from __future__ import annotations

import re
from typing import Any

import httpx

from app.core.config import get_settings

EmbeddingVector = list[float]
_TOKEN_PATTERN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class EmbeddingError(Exception):
    """Base error raised during embedding processing."""


class EmbeddingInputError(EmbeddingError):
    """Raised when the supplied text or batch configuration is invalid."""


class EmbeddingModelLoadError(EmbeddingError):
    """Raised when the configured embedding service cannot be reached."""


class EmbeddingGenerationError(EmbeddingError):
    """Raised when the embedding service cannot generate usable vectors."""


class EmbeddingDimensionError(EmbeddingError):
    """Raised when an embedding has the wrong number of dimensions."""


class EmbeddingTokenizerError(EmbeddingError):
    """Raised when text cannot be divided into safe embedding chunks."""


def normalize_embedding_text(text: str) -> str:
    """Normalize whitespace before embedding or approximate token counting."""

    return " ".join(text.split()).strip()


def _tokenize(text: str) -> list[str]:
    return _TOKEN_PATTERN.findall(normalize_embedding_text(text))


def count_embedding_tokens(text: str) -> int:
    """
    Return a conservative lightweight token estimate.

    Supabase gte-small accepts up to 512 model tokens. The application keeps
    chunks far below that limit (220 configured tokens), so a word/punctuation
    estimate is sufficient here and avoids shipping a multi-gigabyte local
    transformer runtime with the API service.
    """

    return len(_tokenize(text))


def split_text_by_embedding_tokens(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Split text into overlapping lightweight token windows."""

    if max_tokens <= 0:
        raise EmbeddingTokenizerError("max_tokens must be greater than zero.")
    if overlap_tokens < 0:
        raise EmbeddingTokenizerError("overlap_tokens cannot be negative.")
    if overlap_tokens >= max_tokens:
        raise EmbeddingTokenizerError("overlap_tokens must be smaller than max_tokens.")

    tokens = _tokenize(text)
    if not tokens:
        return []
    if len(tokens) <= max_tokens:
        return [normalize_embedding_text(text)]

    step_size = max_tokens - overlap_tokens
    pieces: list[str] = []
    for start in range(0, len(tokens), step_size):
        window = tokens[start : start + max_tokens]
        if not window:
            break
        pieces.append(" ".join(window))
        if start + max_tokens >= len(tokens):
            break
    return pieces


def _embedding_endpoint() -> tuple[str, str]:
    settings = get_settings()
    supabase_url = (settings.supabase_url or "").strip().rstrip("/")
    if not supabase_url:
        raise EmbeddingModelLoadError("SUPABASE_URL is not configured.")

    key = settings.supabase_service_role_key or settings.supabase_anon_key
    if key is None:
        raise EmbeddingModelLoadError(
            "SUPABASE_SERVICE_ROLE_KEY or SUPABASE_ANON_KEY must be configured."
        )

    api_key = key.get_secret_value().strip()
    if not api_key:
        raise EmbeddingModelLoadError("The configured Supabase API key is empty.")

    return f"{supabase_url}/functions/v1/embed", api_key


def _embedding_headers(api_key: str) -> dict[str, str]:
    return {
        "apikey": api_key,
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }


def _validate_inputs(
    texts: list[str],
    batch_size: int | None,
) -> tuple[list[str], int]:
    if not texts:
        raise EmbeddingInputError("At least one text value is required.")

    settings = get_settings()
    resolved_batch_size = batch_size if batch_size is not None else settings.embedding_batch_size
    if resolved_batch_size <= 0:
        raise EmbeddingInputError("Embedding batch size must be greater than zero.")
    if resolved_batch_size > 32:
        resolved_batch_size = 32

    normalized_texts: list[str] = []
    for text_index, text in enumerate(texts):
        normalized_text = normalize_embedding_text(text)
        if not normalized_text:
            raise EmbeddingInputError(f"Text at index {text_index} is empty.")
        normalized_texts.append(normalized_text)
    return normalized_texts, resolved_batch_size


def _validate_response(
    payload: Any,
    *,
    expected_count: int,
) -> list[EmbeddingVector]:
    settings = get_settings()
    if not isinstance(payload, dict):
        raise EmbeddingGenerationError("Embedding service returned an invalid response.")

    rows = payload.get("embeddings")
    if not isinstance(rows, list) or len(rows) != expected_count:
        raise EmbeddingGenerationError(
            "The number of generated embeddings does not match the supplied texts."
        )

    vectors: list[EmbeddingVector] = []
    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            raise EmbeddingGenerationError(f"Embedding row {row_index} is not a vector.")
        try:
            vector = [float(value) for value in row]
        except (TypeError, ValueError) as exc:
            raise EmbeddingGenerationError(
                f"Embedding row {row_index} contains a non-numeric value."
            ) from exc

        if len(vector) != settings.embedding_dimension:
            raise EmbeddingDimensionError(
                f"Embedding row {row_index} has dimension {len(vector)}, "
                f"but {settings.embedding_dimension} is required."
            )
        vectors.append(vector)
    return vectors


def embed_texts(
    texts: list[str],
    *,
    batch_size: int | None = None,
) -> list[EmbeddingVector]:
    """Generate embeddings through the lightweight Supabase Edge Function."""

    normalized_texts, resolved_batch_size = _validate_inputs(texts, batch_size)
    endpoint, api_key = _embedding_endpoint()
    output: list[EmbeddingVector] = []

    try:
        with httpx.Client(timeout=30.0) as client:
            for start in range(0, len(normalized_texts), resolved_batch_size):
                batch = normalized_texts[start : start + resolved_batch_size]
                response = client.post(
                    endpoint,
                    headers=_embedding_headers(api_key),
                    json={"inputs": batch},
                )
                response.raise_for_status()
                output.extend(
                    _validate_response(
                        response.json(),
                        expected_count=len(batch),
                    )
                )
    except httpx.HTTPStatusError as exc:
        raise EmbeddingGenerationError(
            f"Embedding service returned HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingGenerationError("The embedding service request failed.") from exc

    return output


def embed_query(query: str) -> EmbeddingVector:
    """Generate one query embedding using the same model as stored chunks."""

    return embed_texts([query], batch_size=1)[0]


async def embed_texts_async(
    texts: list[str],
    *,
    batch_size: int | None = None,
) -> list[EmbeddingVector]:
    """Generate embeddings asynchronously through Supabase Edge Functions."""

    normalized_texts, resolved_batch_size = _validate_inputs(texts, batch_size)
    endpoint, api_key = _embedding_endpoint()
    output: list[EmbeddingVector] = []

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            for start in range(0, len(normalized_texts), resolved_batch_size):
                batch = normalized_texts[start : start + resolved_batch_size]
                response = await client.post(
                    endpoint,
                    headers=_embedding_headers(api_key),
                    json={"inputs": batch},
                )
                response.raise_for_status()
                output.extend(
                    _validate_response(
                        response.json(),
                        expected_count=len(batch),
                    )
                )
    except httpx.HTTPStatusError as exc:
        raise EmbeddingGenerationError(
            f"Embedding service returned HTTP {exc.response.status_code}."
        ) from exc
    except (httpx.HTTPError, ValueError) as exc:
        raise EmbeddingGenerationError("The embedding service request failed.") from exc

    return output


async def embed_query_async(query: str) -> EmbeddingVector:
    """Generate one query embedding asynchronously."""

    return (await embed_texts_async([query], batch_size=1))[0]

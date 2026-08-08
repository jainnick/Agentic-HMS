from __future__ import annotations

from functools import lru_cache, partial
from typing import Any, cast

from anyio import to_thread
from sentence_transformers import SentenceTransformer

from app.core.config import get_settings

EmbeddingVector = list[float]


class EmbeddingError(Exception):
    """Base error raised during embedding processing."""


class EmbeddingInputError(EmbeddingError):
    """Raised when the supplied text or batch configuration is invalid."""


class EmbeddingModelLoadError(EmbeddingError):
    """Raised when the configured embedding model cannot be loaded."""


class EmbeddingGenerationError(EmbeddingError):
    """Raised when the model cannot generate usable embeddings."""


class EmbeddingDimensionError(EmbeddingError):
    """Raised when an embedding has the wrong number of dimensions."""


class EmbeddingTokenizerError(EmbeddingError):
    """Raised when the embedding tokenizer cannot process text."""


@lru_cache(maxsize=1)
def get_embedding_model() -> SentenceTransformer:
    """
    Load and cache the configured embedding model.

    The model is loaded on the first call. Later calls in the same Python
    process reuse the same model object instead of loading it repeatedly.
    """

    settings = get_settings()

    try:
        model = cast(
            SentenceTransformer,
            SentenceTransformer(
                settings.embedding_model,
            ),
        )
    except Exception as exc:
        raise EmbeddingModelLoadError(
            "The configured embedding model could not be loaded."
        ) from exc

    try:
        model_dimension = model.get_embedding_dimension()
    except Exception as exc:
        raise EmbeddingDimensionError(
            "The embedding model did not report its output dimension."
        ) from exc

    if model_dimension != settings.embedding_dimension:
        raise EmbeddingDimensionError(
            "The embedding model dimension does not match the database. "
            f"Model dimension: {model_dimension}. "
            f"Required dimension: {settings.embedding_dimension}."
        )

    return model


def normalize_embedding_text(
    text: str,
) -> str:
    """
    Normalize whitespace before passing text to the embedding model.

    This converts tabs, line breaks, and repeated spaces into one space.
    Words and punctuation are otherwise preserved.
    """

    return " ".join(text.split()).strip()


def get_embedding_tokenizer() -> Any:
    """
    Return the tokenizer belonging to the configured embedding model.

    Chunking uses exactly the same tokenizer as embedding generation. This
    prevents us from guessing chunk limits using approximate word counts.
    """

    model = get_embedding_model()

    tokenizer = getattr(
        model,
        "tokenizer",
        None,
    )

    if tokenizer is None:
        raise EmbeddingTokenizerError("The configured embedding model does not expose a tokenizer.")

    return tokenizer


def count_embedding_tokens(
    text: str,
) -> int:
    """
    Count tokens exactly as the embedding model sees them.

    Special tokens are included because they consume model input capacity.
    """

    normalized_text = normalize_embedding_text(
        text,
    )

    if not normalized_text:
        return 0

    tokenizer = get_embedding_tokenizer()

    try:
        token_ids: Any = tokenizer.encode(
            normalized_text,
            add_special_tokens=True,
            truncation=False,
        )

    except Exception as exc:
        raise EmbeddingTokenizerError(
            "The embedding tokenizer could not count text tokens."
        ) from exc

    if not isinstance(
        token_ids,
        list,
    ):
        raise EmbeddingTokenizerError(
            "The embedding tokenizer returned an unsupported token format."
        )

    return len(
        token_ids,
    )


def split_text_by_embedding_tokens(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """
    Last-resort splitter for text that cannot be divided naturally.

    Normal chunking should prefer:
        PDF block boundary
        -> sentence boundary
        -> this token-window fallback

    overlap_tokens is used only here because this is an artificial split.
    """

    if max_tokens <= 0:
        raise EmbeddingTokenizerError("max_tokens must be greater than zero.")

    if overlap_tokens < 0:
        raise EmbeddingTokenizerError("overlap_tokens cannot be negative.")

    normalized_text = normalize_embedding_text(
        text,
    )

    if not normalized_text:
        return []

    tokenizer = get_embedding_tokenizer()

    try:
        special_token_count = int(
            tokenizer.num_special_tokens_to_add(
                pair=False,
            )
        )

    except Exception as exc:
        raise EmbeddingTokenizerError(
            "The embedding tokenizer could not determine its special-token count."
        ) from exc

    available_content_tokens = max_tokens - special_token_count

    if available_content_tokens <= 0:
        raise EmbeddingTokenizerError("max_tokens is too small for the embedding tokenizer.")

    if overlap_tokens >= available_content_tokens:
        raise EmbeddingTokenizerError(
            "overlap_tokens must be smaller than the usable token window."
        )

    # Protect against accidentally configuring a chunk larger than the
    # tokenizer/model supports.
    model_max_length = getattr(
        tokenizer,
        "model_max_length",
        None,
    )

    if (
        isinstance(model_max_length, int)
        and 0 < model_max_length < 1_000_000
        and max_tokens > model_max_length
    ):
        raise EmbeddingTokenizerError(
            "Configured maximum chunk tokens exceed the embedding "
            f"model limit of {model_max_length} tokens."
        )

    try:
        token_ids: Any = tokenizer.encode(
            normalized_text,
            add_special_tokens=False,
            truncation=False,
        )

    except Exception as exc:
        raise EmbeddingTokenizerError("The embedding tokenizer could not split text.") from exc

    if not isinstance(
        token_ids,
        list,
    ):
        raise EmbeddingTokenizerError(
            "The embedding tokenizer returned an unsupported token format."
        )

    if len(token_ids) <= available_content_tokens:
        return [
            normalized_text,
        ]

    step_size = available_content_tokens - overlap_tokens

    pieces: list[str] = []

    window_start = 0

    while window_start < len(token_ids):
        window_end = min(
            window_start + available_content_tokens,
            len(token_ids),
        )

        window_ids = token_ids[window_start:window_end]

        try:
            decoded_text = tokenizer.decode(
                window_ids,
                skip_special_tokens=True,
                clean_up_tokenization_spaces=True,
            )

        except Exception as exc:
            raise EmbeddingTokenizerError(
                "The embedding tokenizer could not decode a token window."
            ) from exc

        decoded_text = decoded_text.strip()

        if decoded_text:
            pieces.append(
                decoded_text,
            )

        if window_end >= len(token_ids):
            break

        window_start += step_size

    return pieces


def convert_model_output(
    raw_embeddings: Any,
    *,
    expected_count: int,
    expected_dimension: int,
) -> list[EmbeddingVector]:
    """
    Convert the model output into normal Python lists.

    Sentence Transformers normally returns a NumPy array. The database layer
    will receive list[float] values, so this function creates that boundary
    and validates the shape.
    """

    try:
        rows: object = raw_embeddings.tolist()
    except AttributeError as exc:
        raise EmbeddingGenerationError(
            "The embedding model returned an unsupported output type."
        ) from exc

    if not isinstance(rows, list):
        raise EmbeddingGenerationError("The embedding model did not return a list of vectors.")

    if len(rows) != expected_count:
        raise EmbeddingGenerationError(
            "The number of generated embeddings does not match the number of supplied texts."
        )

    vectors: list[EmbeddingVector] = []

    for row_index, row in enumerate(rows):
        if not isinstance(row, list):
            raise EmbeddingGenerationError(f"Embedding row {row_index} is not a vector.")

        vector: EmbeddingVector = []

        for value in row:
            try:
                vector.append(float(value))
            except (TypeError, ValueError) as exc:
                raise EmbeddingGenerationError(
                    f"Embedding row {row_index} contains a non-numeric value."
                ) from exc

        if len(vector) != expected_dimension:
            raise EmbeddingDimensionError(
                f"Embedding row {row_index} has dimension "
                f"{len(vector)}, but {expected_dimension} is required."
            )

        vectors.append(vector)

    return vectors


def embed_texts(
    texts: list[str],
    *,
    batch_size: int | None = None,
) -> list[EmbeddingVector]:
    """
    Generate embeddings for multiple texts.

    This function is synchronous because Sentence Transformers performs
    synchronous model inference. Async FastAPI code should normally call
    embed_texts_async() instead.
    """

    if not texts:
        raise EmbeddingInputError("At least one text value is required.")

    settings = get_settings()

    resolved_batch_size = batch_size if batch_size is not None else settings.embedding_batch_size

    if resolved_batch_size <= 0:
        raise EmbeddingInputError("Embedding batch size must be greater than zero.")

    normalized_texts: list[str] = []

    for text_index, text in enumerate(texts):
        normalized_text = normalize_embedding_text(
            text,
        )

        if not normalized_text:
            raise EmbeddingInputError(f"Text at index {text_index} is empty.")

        normalized_texts.append(normalized_text)

    model = get_embedding_model()

    try:
        raw_embeddings: Any = model.encode(
            normalized_texts,
            batch_size=resolved_batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
    except Exception as exc:
        raise EmbeddingGenerationError("The embedding model failed while encoding text.") from exc

    return convert_model_output(
        raw_embeddings,
        expected_count=len(normalized_texts),
        expected_dimension=settings.embedding_dimension,
    )


def embed_query(
    query: str,
) -> EmbeddingVector:
    """
    Generate one embedding for a search query.

    The same model is used for stored document chunks and guest questions,
    which keeps both values inside the same vector space.
    """

    vectors = embed_texts(
        [query],
        batch_size=1,
    )

    return vectors[0]


async def embed_texts_async(
    texts: list[str],
    *,
    batch_size: int | None = None,
) -> list[EmbeddingVector]:
    """
    Run embedding generation in an AnyIO worker thread.

    This prevents synchronous model inference from occupying FastAPI's
    asynchronous event-loop thread.
    """

    embedding_call = partial(
        embed_texts,
        texts,
        batch_size=batch_size,
    )

    return await to_thread.run_sync(
        embedding_call,
    )


async def embed_query_async(
    query: str,
) -> EmbeddingVector:
    """Generate a query embedding in an AnyIO worker thread."""

    return await to_thread.run_sync(
        embed_query,
        query,
    )

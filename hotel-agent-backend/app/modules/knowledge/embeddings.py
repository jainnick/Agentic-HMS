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

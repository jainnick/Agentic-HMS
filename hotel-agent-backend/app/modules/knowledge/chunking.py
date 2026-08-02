from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

from app.modules.knowledge.extraction import ExtractedPage


class ChunkingError(Exception):
    """Base error raised while preparing document chunks."""


class InvalidChunkingConfigurationError(ChunkingError):
    """Raised when chunk size or overlap settings are invalid."""


class EmptyDocumentTextError(ChunkingError):
    """Raised when no usable chunks can be produced."""


@dataclass(frozen=True, slots=True)
class PreparedChunk:
    """
    One chunk ready for embedding and database insertion.

    The embedding is not generated here. Keeping chunking separate from
    embeddings makes this function deterministic and easy to test.
    """

    chunk_index: int
    content: str
    page_number: int | None
    heading: str | None
    content_hash: str


def calculate_content_hash(
    content: str,
) -> str:
    """
    Return a stable SHA-256 hash for normalized chunk content.

    The result is always a 64-character hexadecimal string.
    """

    normalized_content = " ".join(content.split())

    return sha256(normalized_content.encode("utf-8")).hexdigest()


def split_text_into_words(
    text: str,
) -> list[str]:
    """
    Split text using whitespace.

    This intentionally uses a predictable word-based approach rather than
    adding a tokenizer or semantic chunking framework to the first version.
    """

    return text.split()


def prepare_chunks(
    pages: list[ExtractedPage],
    *,
    chunk_size_words: int,
    overlap_words: int,
) -> list[PreparedChunk]:
    """
    Convert extracted PDF pages into overlapping word-window chunks.

    Each chunk belongs to only one page. We do not combine text across page
    boundaries because that would make page citations ambiguous.
    """

    if chunk_size_words <= 0:
        raise InvalidChunkingConfigurationError("chunk_size_words must be greater than zero.")

    if overlap_words < 0:
        raise InvalidChunkingConfigurationError("overlap_words cannot be negative.")

    if overlap_words >= chunk_size_words:
        raise InvalidChunkingConfigurationError(
            "overlap_words must be smaller than chunk_size_words."
        )

    prepared_chunks: list[PreparedChunk] = []
    next_chunk_index = 0

    # Example:
    # chunk_size_words = 500
    # overlap_words = 75
    # step_size = 425
    #
    # Chunk 1: words 0-499
    # Chunk 2: words 425-924
    step_size = chunk_size_words - overlap_words

    for page in pages:
        words = split_text_into_words(
            page.text,
        )

        if not words:
            continue

        window_start = 0

        while window_start < len(words):
            window_end = min(
                window_start + chunk_size_words,
                len(words),
            )

            chunk_words = words[window_start:window_end]

            content = " ".join(chunk_words).strip()

            if content:
                prepared_chunks.append(
                    PreparedChunk(
                        chunk_index=next_chunk_index,
                        content=content,
                        page_number=page.page_number,
                        # Reliable heading extraction requires structured
                        # parsing. We leave it empty rather than guessing.
                        heading=None,
                        content_hash=calculate_content_hash(
                            content,
                        ),
                    )
                )

                next_chunk_index += 1

            # We have reached the end of this page.
            if window_end >= len(words):
                break

            window_start += step_size

    if not prepared_chunks:
        raise EmptyDocumentTextError("No usable chunks could be created from the document.")

    return prepared_chunks

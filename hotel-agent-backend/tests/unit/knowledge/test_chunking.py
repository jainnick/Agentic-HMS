import pytest

from app.modules.knowledge.chunking import (
    InvalidChunkingConfigurationError,
    prepare_chunks,
)
from app.modules.knowledge.extraction import ExtractedPage


def test_prepare_chunks_creates_overlapping_windows() -> None:
    words = [f"word{index}" for index in range(12)]

    pages = [
        ExtractedPage(
            page_number=1,
            text=" ".join(words),
        )
    ]

    chunks = prepare_chunks(
        pages,
        chunk_size_words=5,
        overlap_words=2,
    )

    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2, 3]

    first_chunk_words = chunks[0].content.split()
    second_chunk_words = chunks[1].content.split()

    # The final two words of chunk 0 should become the first two
    # words of chunk 1.
    assert first_chunk_words[-2:] == second_chunk_words[:2]


def test_prepare_chunks_retains_page_number() -> None:
    pages = [
        ExtractedPage(
            page_number=4,
            text="Pet policy content for hotel guests.",
        )
    ]

    chunks = prepare_chunks(
        pages,
        chunk_size_words=100,
        overlap_words=10,
    )

    assert len(chunks) == 1
    assert chunks[0].page_number == 4
    assert chunks[0].heading is None


def test_prepare_chunks_creates_sha256_hash() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Pets are allowed with prior approval.",
        )
    ]

    chunks = prepare_chunks(
        pages,
        chunk_size_words=100,
        overlap_words=10,
    )

    assert len(chunks[0].content_hash) == 64


def test_prepare_chunks_rejects_overlap_equal_to_size() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Some hotel information.",
        )
    ]

    with pytest.raises(
        InvalidChunkingConfigurationError,
        match="smaller than",
    ):
        prepare_chunks(
            pages,
            chunk_size_words=10,
            overlap_words=10,
        )

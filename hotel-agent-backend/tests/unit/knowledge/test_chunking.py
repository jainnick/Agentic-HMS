import pytest

from app.modules.knowledge.chunking import (
    EmptyDocumentTextError,
    InvalidChunkingConfigurationError,
    prepare_chunks,
)
from app.modules.knowledge.extraction import (
    ExtractedPage,
)


def fake_token_counter(
    text: str,
) -> int:
    """
    Treat every whitespace-separated word as one token.

    Unit tests intentionally avoid loading the real ML model.
    """

    return len(
        text.split(),
    )


def fake_token_window_splitter(
    text: str,
    max_tokens: int,
    overlap_tokens: int,
) -> list[str]:
    """Simple test replacement for the real tokenizer window splitter."""

    words = text.split()

    if len(words) <= max_tokens:
        return [
            text,
        ]

    step_size = max_tokens - overlap_tokens

    windows: list[str] = []

    start = 0

    while start < len(words):
        end = min(
            start + max_tokens,
            len(words),
        )

        windows.append(
            " ".join(
                words[start:end],
            )
        )

        if end >= len(words):
            break

        start += step_size

    return windows


def test_short_page_becomes_one_chunk() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Checkout is at 11 AM.",
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=20,
        max_tokens=30,
        fallback_overlap_tokens=3,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) == 1
    assert chunks[0].page_number == 1
    assert chunks[0].content == ("Checkout is at 11 AM.")


def test_natural_blocks_are_kept_together_until_target() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=(
                "Check-in is from three PM.\n\n"
                "Checkout is at eleven AM.\n\n"
                "Breakfast starts at seven AM."
            ),
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=10,
        max_tokens=14,
        fallback_overlap_tokens=2,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) >= 2

    assert "Check-in" in chunks[0].content
    assert "Checkout" in chunks[0].content


def test_oversized_block_is_split_at_sentences() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=("One two three four. Five six seven eight."),
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=4,
        max_tokens=5,
        fallback_overlap_tokens=1,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) == 2

    assert chunks[0].content == ("One two three four.")

    assert chunks[1].content == ("Five six seven eight.")

    assert chunks[0].metadata["chunk_method"] == "sentence_pack"


def test_huge_sentence_uses_token_fallback() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text=("one two three four five six seven eight nine ten eleven twelve"),
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=5,
        max_tokens=5,
        fallback_overlap_tokens=2,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) == 4

    assert chunks[0].content.split() == [
        "one",
        "two",
        "three",
        "four",
        "five",
    ]

    assert chunks[1].content.split() == [
        "four",
        "five",
        "six",
        "seven",
        "eight",
    ]

    assert chunks[0].metadata["chunk_method"] == "token_fallback"

    assert chunks[0].metadata["overlap_type"] == "token_window"


def test_chunks_never_cross_physical_pages() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Checkout is at 11 AM.",
        ),
        ExtractedPage(
            page_number=2,
            text="Dogs are allowed.",
        ),
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=100,
        max_tokens=120,
        fallback_overlap_tokens=10,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) == 2

    assert chunks[0].page_number == 1
    assert chunks[1].page_number == 2


def test_fifty_five_pages_are_processed_with_same_algorithm() -> None:
    pages = [
        ExtractedPage(
            page_number=page_number,
            text=(f"Policy content for page {page_number}."),
        )
        for page_number in range(
            1,
            56,
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=100,
        max_tokens=120,
        fallback_overlap_tokens=10,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert len(chunks) == 55

    assert {chunk.page_number for chunk in chunks} == set(
        range(
            1,
            56,
        )
    )


def test_chunk_metadata_contains_diagnostics() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Parking is available upon request.",
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=20,
        max_tokens=30,
        fallback_overlap_tokens=3,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    metadata = chunks[0].metadata

    assert metadata["token_count"] == 5
    assert metadata["chunk_method"] == "block_pack"
    assert metadata["overlap_type"] == "none"
    assert metadata["target_tokens"] == 20
    assert metadata["max_tokens"] == 30


def test_prepare_chunks_creates_sha256_hash() -> None:
    pages = [
        ExtractedPage(
            page_number=1,
            text="Pets are allowed.",
        )
    ]

    chunks = prepare_chunks(
        pages,
        target_tokens=20,
        max_tokens=30,
        fallback_overlap_tokens=3,
        token_counter=fake_token_counter,
        token_window_splitter=(fake_token_window_splitter),
    )

    assert (
        len(
            chunks[0].content_hash,
        )
        == 64
    )


def test_target_cannot_exceed_maximum() -> None:
    with pytest.raises(
        InvalidChunkingConfigurationError,
        match="cannot be greater",
    ):
        prepare_chunks(
            [
                ExtractedPage(
                    page_number=1,
                    text="Hotel policy.",
                )
            ],
            target_tokens=100,
            max_tokens=50,
            fallback_overlap_tokens=5,
            token_counter=fake_token_counter,
            token_window_splitter=(fake_token_window_splitter),
        )


def test_empty_document_is_rejected() -> None:
    with pytest.raises(
        EmptyDocumentTextError,
    ):
        prepare_chunks(
            [
                ExtractedPage(
                    page_number=1,
                    text="   ",
                )
            ],
            target_tokens=100,
            max_tokens=120,
            fallback_overlap_tokens=10,
            token_counter=fake_token_counter,
            token_window_splitter=(fake_token_window_splitter),
        )

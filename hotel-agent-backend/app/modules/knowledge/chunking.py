from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import (
    dataclass,
    field,
)
from hashlib import sha256

from app.modules.knowledge.extraction import (
    ExtractedPage,
)


class ChunkingError(Exception):
    """Base error raised while preparing document chunks."""


class InvalidChunkingConfigurationError(ChunkingError):
    """Raised when chunk settings are invalid."""


class EmptyDocumentTextError(ChunkingError):
    """Raised when no usable chunks can be produced."""


TokenCounter = Callable[
    [str],
    int,
]

TokenWindowSplitter = Callable[
    [str, int, int],
    list[str],
]


@dataclass(frozen=True, slots=True)
class PreparedChunk:
    """
    One chunk ready for embedding and database insertion.

    metadata contains diagnostics explaining how this chunk was produced.
    """

    chunk_index: int
    content: str
    page_number: int | None
    heading: str | None
    content_hash: str

    metadata: dict[str, object] = field(
        default_factory=dict,
    )


@dataclass(frozen=True, slots=True)
class _ChunkUnit:
    """
    Internal structural unit used while building final chunks.

    method:
        block
        sentence
        token_fallback

    uses_overlap is true only when an artificial token-window split was used.
    """

    content: str
    method: str
    uses_overlap: bool = False


_SENTENCE_BOUNDARY_PATTERN = re.compile(r"(?<=[.!?])\s+")

_BLOCK_BOUNDARY_PATTERN = re.compile(r"\n\s*\n+")


def calculate_content_hash(
    content: str,
) -> str:
    """Return a stable SHA-256 hash for normalized chunk content."""

    normalized_content = " ".join(
        content.split(),
    )

    return sha256(
        normalized_content.encode(
            "utf-8",
        )
    ).hexdigest()


def normalize_structural_unit(
    text: str,
) -> str:
    """
    Normalize one block while preserving its words and punctuation.

    Internal line wrapping from PDFs is collapsed because visual line wraps
    should not become semantic boundaries.
    """

    return " ".join(
        text.split(),
    ).strip()


def split_text_into_structural_units(
    text: str,
) -> list[str]:
    """
    Split page text using the blank-line block boundaries produced by the
    extraction layer.

    These are our preferred chunk boundaries.
    """

    units: list[str] = []

    for raw_unit in _BLOCK_BOUNDARY_PATTERN.split(
        text,
    ):
        normalized_unit = normalize_structural_unit(
            raw_unit,
        )

        if normalized_unit:
            units.append(
                normalized_unit,
            )

    return units


def split_text_into_sentences(
    text: str,
) -> list[str]:
    """
    Split oversized prose at sentence boundaries.

    This is deliberately simple and deterministic. It is not attempting NLP
    sentence understanding.

    Token fallback handles cases where sentence punctuation is missing or a
    single sentence remains too large.
    """

    normalized_text = normalize_structural_unit(
        text,
    )

    if not normalized_text:
        return []

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY_PATTERN.split(
            normalized_text,
        )
        if sentence.strip()
    ]

    return sentences or [
        normalized_text,
    ]


def expand_structural_unit(
    text: str,
    *,
    max_tokens: int,
    fallback_overlap_tokens: int,
    token_counter: TokenCounter,
    token_window_splitter: TokenWindowSplitter,
) -> list[_ChunkUnit]:
    """
    Ensure one structural PDF block can fit inside the configured maximum.

    Preferred order:

        complete PDF block
                ↓
        complete sentences
                ↓
        overlapping tokenizer windows

    Token windows are therefore the final fallback, not the normal strategy.
    """

    normalized_text = normalize_structural_unit(
        text,
    )

    if not normalized_text:
        return []

    if (
        token_counter(
            normalized_text,
        )
        <= max_tokens
    ):
        return [
            _ChunkUnit(
                content=normalized_text,
                method="block",
            )
        ]

    sentences = split_text_into_sentences(
        normalized_text,
    )

    expanded_units: list[_ChunkUnit] = []

    # When the oversized block contains useful sentence boundaries, preserve
    # those sentences as atomic units.
    if len(sentences) > 1:
        for sentence in sentences:
            if (
                token_counter(
                    sentence,
                )
                <= max_tokens
            ):
                expanded_units.append(
                    _ChunkUnit(
                        content=sentence,
                        method="sentence",
                    )
                )

                continue

            # One individual sentence is still too large. This is where the
            # tokenizer-window fallback becomes necessary.
            token_windows = token_window_splitter(
                sentence,
                max_tokens,
                fallback_overlap_tokens,
            )

            for token_window in token_windows:
                expanded_units.append(
                    _ChunkUnit(
                        content=token_window,
                        method="token_fallback",
                        uses_overlap=True,
                    )
                )

        return expanded_units

    # The block had no useful sentence boundary. Split it directly using the
    # tokenizer.
    token_windows = token_window_splitter(
        normalized_text,
        max_tokens,
        fallback_overlap_tokens,
    )

    for token_window in token_windows:
        expanded_units.append(
            _ChunkUnit(
                content=token_window,
                method="token_fallback",
                uses_overlap=True,
            )
        )

    return expanded_units


def join_chunk_units(
    units: list[_ChunkUnit],
) -> str:
    """
    Join structural units into readable chunk text.

    Blank lines are retained between PDF blocks/sentences for readability.
    The embedding service later normalizes whitespace before embedding.
    """

    return "\n\n".join(unit.content for unit in units).strip()


def resolve_chunk_method(
    units: list[_ChunkUnit],
) -> str:
    """Describe the strongest splitting method used by a final chunk."""

    methods = {unit.method for unit in units}

    if "token_fallback" in methods:
        return "token_fallback"

    if "sentence" in methods:
        return "sentence_pack"

    return "block_pack"


def build_prepared_chunk(
    *,
    chunk_index: int,
    page_number: int,
    units: list[_ChunkUnit],
    target_tokens: int,
    max_tokens: int,
    token_counter: TokenCounter,
) -> PreparedChunk:
    """Convert accumulated structural units into one final chunk."""

    content = join_chunk_units(
        units,
    )

    token_count = token_counter(
        content,
    )

    uses_overlap = any(unit.uses_overlap for unit in units)

    return PreparedChunk(
        chunk_index=chunk_index,
        content=content,
        page_number=page_number,
        # Heading detection is deliberately not guessed in this version.
        heading=None,
        content_hash=calculate_content_hash(
            content,
        ),
        metadata={
            "token_count": token_count,
            "chunk_method": resolve_chunk_method(
                units,
            ),
            "overlap_type": ("token_window" if uses_overlap else "none"),
            "source_unit_count": len(
                units,
            ),
            "target_tokens": target_tokens,
            "max_tokens": max_tokens,
        },
    )


def prepare_chunks(
    pages: list[ExtractedPage],
    *,
    target_tokens: int,
    max_tokens: int,
    fallback_overlap_tokens: int,
    token_counter: TokenCounter,
    token_window_splitter: TokenWindowSplitter,
) -> list[PreparedChunk]:
    """
    Convert PDF pages into adaptive tokenizer-aware chunks.

    Rules:

    1. Pages remain separate so citations stay unambiguous.
    2. PDF text blocks are preferred as boundaries.
    3. Oversized blocks are split using complete sentences.
    4. Oversized sentences use tokenizer windows as the final fallback.
    5. Chunks target target_tokens but may grow up to max_tokens to keep a
       natural structural unit intact.
    6. Artificial overlap exists only for tokenizer-window fallback.
    """

    if target_tokens <= 0:
        raise InvalidChunkingConfigurationError("target_tokens must be greater than zero.")

    if max_tokens <= 0:
        raise InvalidChunkingConfigurationError("max_tokens must be greater than zero.")

    if target_tokens > max_tokens:
        raise InvalidChunkingConfigurationError("target_tokens cannot be greater than max_tokens.")

    if fallback_overlap_tokens < 0:
        raise InvalidChunkingConfigurationError("fallback_overlap_tokens cannot be negative.")

    if fallback_overlap_tokens >= max_tokens:
        raise InvalidChunkingConfigurationError(
            "fallback_overlap_tokens must be smaller than max_tokens."
        )

    prepared_chunks: list[PreparedChunk] = []

    next_chunk_index = 0

    for page in pages:
        structural_units = split_text_into_structural_units(
            page.text,
        )

        page_units: list[_ChunkUnit] = []

        for structural_unit in structural_units:
            page_units.extend(
                expand_structural_unit(
                    structural_unit,
                    max_tokens=max_tokens,
                    fallback_overlap_tokens=(fallback_overlap_tokens),
                    token_counter=token_counter,
                    token_window_splitter=(token_window_splitter),
                )
            )

        current_units: list[_ChunkUnit] = []

        for unit in page_units:
            unit_token_count = token_counter(
                unit.content,
            )

            # expand_structural_unit() should guarantee this. Keep the check
            # because silently embedding an oversized chunk would be worse
            # than failing ingestion with a clear error.
            if unit_token_count > max_tokens:
                raise ChunkingError(
                    f"A prepared text unit exceeds the configured maximum of {max_tokens} tokens."
                )

            if not current_units:
                current_units.append(
                    unit,
                )

                continue

            current_content = join_chunk_units(
                current_units,
            )

            current_token_count = token_counter(
                current_content,
            )

            candidate_units = [
                *current_units,
                unit,
            ]

            candidate_content = join_chunk_units(
                candidate_units,
            )

            candidate_token_count = token_counter(
                candidate_content,
            )

            # Once the target is reached, prefer the natural boundary rather
            # than continuing to fill the chunk toward the hard maximum.
            target_reached = current_token_count >= target_tokens

            would_exceed_maximum = candidate_token_count > max_tokens

            if target_reached or would_exceed_maximum:
                prepared_chunks.append(
                    build_prepared_chunk(
                        chunk_index=next_chunk_index,
                        page_number=page.page_number,
                        units=current_units,
                        target_tokens=target_tokens,
                        max_tokens=max_tokens,
                        token_counter=token_counter,
                    )
                )

                next_chunk_index += 1

                current_units = [
                    unit,
                ]

                continue

            current_units.append(
                unit,
            )

        if current_units:
            prepared_chunks.append(
                build_prepared_chunk(
                    chunk_index=next_chunk_index,
                    page_number=page.page_number,
                    units=current_units,
                    target_tokens=target_tokens,
                    max_tokens=max_tokens,
                    token_counter=token_counter,
                )
            )

            next_chunk_index += 1

    if not prepared_chunks:
        raise EmptyDocumentTextError("No usable chunks could be created from the document.")

    return prepared_chunks

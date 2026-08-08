from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pymupdf


class PdfExtractionError(Exception):
    """Base error raised while reading a PDF."""


class InvalidPdfError(PdfExtractionError):
    """Raised when the uploaded bytes are not a readable PDF."""


class PdfTextNotFoundError(PdfExtractionError):
    """Raised when a PDF contains no extractable text."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """
    Text extracted from one physical PDF page.

    Page numbers are one-based so they match the page numbers shown to users.

    Text blocks inside a page are separated by a blank line. This allows the
    chunker to prefer PDF structure before falling back to sentences/tokens.
    """

    page_number: int
    text: str


def normalize_extracted_text(
    text: str,
) -> str:
    """
    Normalize one extracted PDF text block.

    We collapse repeated whitespace inside individual lines while keeping
    lines readable. Block boundaries themselves are added by
    extract_pdf_pages().
    """

    normalized_line_endings = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    cleaned_lines: list[str] = []

    for raw_line in normalized_line_endings.split("\n"):
        cleaned_line = " ".join(
            raw_line.split(),
        ).strip()

        if cleaned_line:
            cleaned_lines.append(
                cleaned_line,
            )

    return "\n".join(
        cleaned_lines,
    ).strip()


def extract_pdf_pages(
    pdf_bytes: bytes,
) -> list[ExtractedPage]:
    """
    Extract readable text blocks while preserving physical page numbers.

    Why blocks instead of one flat text string?

    PDF pages frequently contain separate visual regions such as:
    - headings;
    - paragraphs;
    - policy descriptions;
    - list sections;
    - table-like areas.

    PyMuPDF's "blocks" extraction gives us a useful free structural signal.

    This function still does not:
    - perform OCR;
    - create chunks;
    - generate embeddings;
    - write to the database.
    """

    if not pdf_bytes:
        raise InvalidPdfError("The uploaded PDF is empty.")

    try:
        with pymupdf.open(  # type: ignore[no-untyped-call]
            stream=pdf_bytes,
            filetype="pdf",
        ) as document:
            if document.page_count == 0:
                raise PdfTextNotFoundError("The PDF does not contain any pages.")

            extracted_pages: list[ExtractedPage] = []

            for page_index in range(
                document.page_count,
            ):
                page = document.load_page(
                    page_index,
                )

                raw_blocks: Any = page.get_text(
                    "blocks",
                    sort=True,
                )

                cleaned_blocks: list[str] = []

                for block in raw_blocks:
                    # PyMuPDF block tuples contain coordinates followed by
                    # the actual block text at index 4.
                    if not isinstance(
                        block,
                        (tuple, list),
                    ):
                        continue

                    if len(block) < 5:
                        continue

                    raw_block_text = block[4]

                    if not isinstance(
                        raw_block_text,
                        str,
                    ):
                        continue

                    cleaned_block = normalize_extracted_text(
                        raw_block_text,
                    )

                    if cleaned_block:
                        cleaned_blocks.append(
                            cleaned_block,
                        )

                if not cleaned_blocks:
                    # Image-only/scanned pages may have no text. We skip the
                    # individual page and continue checking the document.
                    continue

                # A double newline becomes our explicit structural boundary.
                page_text = "\n\n".join(
                    cleaned_blocks,
                ).strip()

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_index + 1,
                        text=page_text,
                    )
                )

    except PdfTextNotFoundError:
        raise

    except (RuntimeError, ValueError) as exc:
        raise InvalidPdfError("The uploaded file is not a readable PDF.") from exc

    if not extracted_pages:
        raise PdfTextNotFoundError("The PDF contains no extractable text and may require OCR.")

    return extracted_pages

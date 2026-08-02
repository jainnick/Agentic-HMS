from __future__ import annotations

from dataclasses import dataclass

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
    """

    page_number: int
    text: str


def normalize_extracted_text(text: str) -> str:
    """
    Normalize text produced by PyMuPDF.

    PDF text often contains:
    - Windows and Unix line endings;
    - spaces at the start or end of lines;
    - many empty lines.

    We remove that noise while keeping meaningful line separation.
    """

    normalized_line_endings = text.replace(
        "\r\n",
        "\n",
    ).replace(
        "\r",
        "\n",
    )

    cleaned_lines = [line.strip() for line in normalized_line_endings.split("\n") if line.strip()]

    return "\n".join(cleaned_lines).strip()


def extract_pdf_pages(
    pdf_bytes: bytes,
) -> list[ExtractedPage]:
    """
    Extract readable text from a PDF while preserving page numbers.

    This function does not:
    - perform OCR;
    - create chunks;
    - create embeddings;
    - write anything to the database.
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

            for page_index in range(document.page_count):
                page = document.load_page(page_index)

                raw_text = page.get_text(
                    "text",
                    sort=True,
                )

                cleaned_text = normalize_extracted_text(
                    raw_text,
                )

                # Image-only pages may contain no extractable text.
                # We skip those pages but continue checking the rest.
                if not cleaned_text:
                    continue

                extracted_pages.append(
                    ExtractedPage(
                        page_number=page_index + 1,
                        text=cleaned_text,
                    )
                )

    except PdfTextNotFoundError:
        raise

    except (RuntimeError, ValueError) as exc:
        raise InvalidPdfError("The uploaded file is not a readable PDF.") from exc

    if not extracted_pages:
        raise PdfTextNotFoundError("The PDF contains no extractable text and may require OCR.")

    return extracted_pages

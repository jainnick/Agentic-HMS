from __future__ import annotations

import re
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError


class PdfExtractionError(Exception):
    """Base error raised while reading a PDF."""


class InvalidPdfError(PdfExtractionError):
    """Raised when the uploaded bytes are not a readable PDF."""


class PdfTextNotFoundError(PdfExtractionError):
    """Raised when a PDF contains no extractable text."""


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    """Text extracted from one physical PDF page."""

    page_number: int
    text: str


def normalize_extracted_text(text: str) -> str:
    """Normalize one extracted PDF text block while keeping readable lines."""

    normalized_line_endings = text.replace("\r\n", "\n").replace("\r", "\n")
    cleaned_lines: list[str] = []

    for raw_line in normalized_line_endings.split("\n"):
        cleaned_line = " ".join(raw_line.split()).strip()
        if cleaned_line:
            cleaned_lines.append(cleaned_line)

    return "\n".join(cleaned_lines).strip()


def extract_pdf_pages(pdf_bytes: bytes) -> list[ExtractedPage]:
    """
    Extract readable text while preserving physical page numbers.

    pypdf is intentionally used instead of PyMuPDF here because the production
    FastAPI app runs inside a size-constrained Vercel Python function. Paragraph
    boundaries exposed by the PDF text layer are preserved as double newlines so
    the existing chunker can still prefer natural structure before falling back
    to sentence/token splitting.
    """

    if not pdf_bytes:
        raise InvalidPdfError("The uploaded PDF is empty.")

    try:
        reader = PdfReader(BytesIO(pdf_bytes), strict=False)
    except (PdfReadError, ValueError, TypeError, OSError) as exc:
        raise InvalidPdfError("The uploaded file is not a readable PDF.") from exc

    if not reader.pages:
        raise PdfTextNotFoundError("The PDF does not contain any pages.")

    extracted_pages: list[ExtractedPage] = []

    for page_index, page in enumerate(reader.pages):
        try:
            raw_text = page.extract_text() or ""
        except (PdfReadError, ValueError, TypeError, KeyError) as exc:
            raise InvalidPdfError("The uploaded file is not a readable PDF.") from exc

        if not raw_text.strip():
            # Image-only/scanned pages may have no text. Continue checking the
            # rest of the document before deciding that OCR is required.
            continue

        normalized = raw_text.replace("\r\n", "\n").replace("\r", "\n")
        raw_blocks = re.split(r"\n\s*\n+", normalized)
        cleaned_blocks = [
            cleaned for block in raw_blocks if (cleaned := normalize_extracted_text(block))
        ]

        if not cleaned_blocks:
            continue

        extracted_pages.append(
            ExtractedPage(
                page_number=page_index + 1,
                text="\n\n".join(cleaned_blocks).strip(),
            )
        )

    if not extracted_pages:
        raise PdfTextNotFoundError("The PDF contains no extractable text and may require OCR.")

    return extracted_pages

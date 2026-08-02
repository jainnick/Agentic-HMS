import pymupdf
import pytest

from app.modules.knowledge.extraction import (
    InvalidPdfError,
    PdfTextNotFoundError,
    extract_pdf_pages,
)


def build_test_pdf(
    *page_texts: str,
) -> bytes:
    """Create a small in-memory PDF for unit testing."""

    document = pymupdf.open()

    try:
        for page_text in page_texts:
            page = document.new_page()

            if page_text:
                page.insert_text(
                    (72, 72),
                    page_text,
                )

        return document.tobytes()

    finally:
        document.close()


def test_extract_pdf_pages_preserves_page_numbers() -> None:
    pdf_bytes = build_test_pdf(
        "Hotel introduction",
        "Pets under 10 kg are allowed.",
    )

    pages = extract_pdf_pages(
        pdf_bytes,
    )

    assert len(pages) == 2

    assert pages[0].page_number == 1
    assert "Hotel introduction" in pages[0].text

    assert pages[1].page_number == 2
    assert "Pets under 10 kg are allowed." in pages[1].text


def test_extract_pdf_pages_rejects_invalid_bytes() -> None:
    with pytest.raises(
        InvalidPdfError,
        match="not a readable PDF",
    ):
        extract_pdf_pages(
            b"This is not a PDF.",
        )


def test_extract_pdf_pages_rejects_pdf_without_text() -> None:
    pdf_bytes = build_test_pdf(
        "",
    )

    with pytest.raises(
        PdfTextNotFoundError,
        match="may require OCR",
    ):
        extract_pdf_pages(
            pdf_bytes,
        )

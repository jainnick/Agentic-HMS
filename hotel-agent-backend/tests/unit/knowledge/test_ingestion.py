from __future__ import annotations

import pytest

from app.modules.knowledge.ingestion import (
    InvalidPdfUploadError,
    InvalidSourceKeyError,
    calculate_file_checksum,
    normalize_source_key,
    validate_pdf_upload,
)


def build_pdf_like_bytes(
    content: bytes = b"Hotel knowledge test content",
) -> bytes:
    """
    Create bytes that pass preliminary PDF-header validation.

    These bytes are not intended for PyMuPDF extraction tests. The extraction
    module already has separate tests using structurally valid PDFs.
    """

    return b"%PDF-1.7\n" + content


def test_calculate_file_checksum_returns_sha256_hex() -> None:
    checksum = calculate_file_checksum(b"hotel policy")

    assert len(checksum) == 64
    assert all(character in "0123456789abcdef" for character in checksum)


def test_same_file_bytes_produce_same_checksum() -> None:
    first_checksum = calculate_file_checksum(b"same file")

    second_checksum = calculate_file_checksum(b"same file")

    assert first_checksum == second_checksum


def test_different_file_bytes_produce_different_checksums() -> None:
    first_checksum = calculate_file_checksum(b"version one")

    second_checksum = calculate_file_checksum(b"version two")

    assert first_checksum != second_checksum


@pytest.mark.parametrize(
    ("source_key", "expected"),
    [
        (
            "Guest Policies",
            "guest-policies",
        ),
        (
            "  Guest__Policies 2026  ",
            "guest-policies-2026",
        ),
        (
            "Pet & Smoking / Rules",
            "pet-smoking-rules",
        ),
        (
            "ROOM---INFORMATION",
            "room-information",
        ),
        (
            "Café Policy",
            "café-policy",
        ),
    ],
)
def test_normalize_source_key(
    source_key: str,
    expected: str,
) -> None:
    assert normalize_source_key(source_key) == expected


@pytest.mark.parametrize(
    "source_key",
    [
        "",
        "   ",
        "---",
        "_ / &",
    ],
)
def test_normalize_source_key_rejects_blank_result(
    source_key: str,
) -> None:
    with pytest.raises(
        InvalidSourceKeyError,
        match="at least one letter or number",
    ):
        normalize_source_key(source_key)


def test_normalize_source_key_rejects_oversized_key() -> None:
    oversized_source_key = "a" * 121

    with pytest.raises(
        InvalidSourceKeyError,
        match="cannot exceed 120",
    ):
        normalize_source_key(oversized_source_key)


def test_validate_pdf_upload_returns_validated_metadata() -> None:
    pdf_bytes = build_pdf_like_bytes()

    result = validate_pdf_upload(
        filename="guest-policies.pdf",
        content_type="application/pdf",
        file_bytes=pdf_bytes,
        max_upload_mb=10,
    )

    assert result.original_filename == "guest-policies.pdf"
    assert result.size_bytes == len(pdf_bytes)
    assert result.checksum == calculate_file_checksum(pdf_bytes)


def test_validate_pdf_upload_removes_browser_fake_path() -> None:
    result = validate_pdf_upload(
        filename=r"C:\fakepath\guest-policies.pdf",
        content_type="application/pdf",
        file_bytes=build_pdf_like_bytes(),
        max_upload_mb=10,
    )

    assert result.original_filename == "guest-policies.pdf"


def test_validate_pdf_upload_accepts_content_type_parameters() -> None:
    result = validate_pdf_upload(
        filename="guest-policies.pdf",
        content_type="application/pdf; charset=binary",
        file_bytes=build_pdf_like_bytes(),
        max_upload_mb=10,
    )

    assert result.original_filename == "guest-policies.pdf"


def test_validate_pdf_upload_rejects_missing_filename() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="filename is required",
    ):
        validate_pdf_upload(
            filename=None,
            content_type="application/pdf",
            file_bytes=build_pdf_like_bytes(),
            max_upload_mb=10,
        )


def test_validate_pdf_upload_rejects_wrong_extension() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match=r"\.pdf extension",
    ):
        validate_pdf_upload(
            filename="guest-policies.txt",
            content_type="application/pdf",
            file_bytes=build_pdf_like_bytes(),
            max_upload_mb=10,
        )


def test_validate_pdf_upload_rejects_wrong_content_type() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="application/pdf",
    ):
        validate_pdf_upload(
            filename="guest-policies.pdf",
            content_type="text/plain",
            file_bytes=build_pdf_like_bytes(),
            max_upload_mb=10,
        )


def test_validate_pdf_upload_rejects_empty_file() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="empty",
    ):
        validate_pdf_upload(
            filename="guest-policies.pdf",
            content_type="application/pdf",
            file_bytes=b"",
            max_upload_mb=10,
        )


def test_validate_pdf_upload_rejects_file_without_pdf_header() -> None:
    with pytest.raises(
        InvalidPdfUploadError,
        match="PDF header",
    ):
        validate_pdf_upload(
            filename="guest-policies.pdf",
            content_type="application/pdf",
            file_bytes=b"This is not actually a PDF.",
            max_upload_mb=10,
        )


def test_validate_pdf_upload_rejects_oversized_file() -> None:
    oversized_file = b"%PDF-1.7\n" + (b"x" * (1024 * 1024))

    with pytest.raises(
        InvalidPdfUploadError,
        match="exceeds the 1 MB",
    ):
        validate_pdf_upload(
            filename="guest-policies.pdf",
            content_type="application/pdf",
            file_bytes=oversized_file,
            max_upload_mb=1,
        )


def test_validate_pdf_upload_rejects_invalid_size_configuration() -> None:
    with pytest.raises(
        ValueError,
        match="max_upload_mb",
    ):
        validate_pdf_upload(
            filename="guest-policies.pdf",
            content_type="application/pdf",
            file_bytes=build_pdf_like_bytes(),
            max_upload_mb=0,
        )

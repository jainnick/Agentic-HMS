from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256

MAX_SOURCE_KEY_LENGTH = 120
MAX_ORIGINAL_FILENAME_LENGTH = 255
MAX_DOCUMENT_TITLE_LENGTH = 255

PDF_CONTENT_TYPE = "application/pdf"
PDF_HEADER = b"%PDF-"
PDF_HEADER_SEARCH_LIMIT = 1024


class KnowledgeIngestionValidationError(Exception):
    """Base error raised when knowledge-ingestion input is invalid."""


class InvalidSourceKeyError(KnowledgeIngestionValidationError):
    """Raised when a source key cannot be normalized safely."""


class InvalidDocumentTitleError(KnowledgeIngestionValidationError):
    """Raised when a knowledge-document title is invalid."""


class InvalidPdfUploadError(KnowledgeIngestionValidationError):
    """Raised when an uploaded file fails basic PDF validation."""


@dataclass(frozen=True, slots=True)
class ValidatedPdfUpload:
    """
    Validated metadata derived from one uploaded PDF.

    The actual PDF bytes are intentionally not duplicated inside this object.
    The service already has the bytes and can continue passing them separately.
    """

    original_filename: str
    size_bytes: int
    checksum: str


def calculate_file_checksum(
    file_bytes: bytes,
) -> str:
    """
    Calculate a SHA-256 checksum for the complete uploaded file.

    This checksum represents the original PDF bytes, not the extracted text.
    Byte-for-byte identical files produce the same checksum.
    """

    return sha256(file_bytes).hexdigest()


def normalize_document_title(
    title: str,
) -> str:
    """
    Normalize and validate a knowledge-document display title.

    Unlike source_key, a title remains human-readable. We only normalize
    repeated whitespace and enforce database constraints.
    """

    normalized_title = " ".join(title.split())

    if not normalized_title:
        raise InvalidDocumentTitleError("Document title cannot be blank.")

    if len(normalized_title) > MAX_DOCUMENT_TITLE_LENGTH:
        raise InvalidDocumentTitleError(
            f"Document title cannot exceed {MAX_DOCUMENT_TITLE_LENGTH} characters."
        )

    return normalized_title


def normalize_source_key(
    source_key: str,
) -> str:
    """
    Normalize a logical source identifier.

    Examples:
    - "Guest Policies" becomes "guest-policies"
    - "Guest_Policies 2026" becomes "guest-policies-2026"
    - "Cafe & Spa Policy" becomes "cafe-spa-policy"

    Unicode letters and digits are preserved. Punctuation and repeated
    separators are converted into one hyphen.
    """

    normalized_input = source_key.strip().casefold()

    normalized_characters: list[str] = []
    separator_pending = False

    for character in normalized_input:
        if character.isalnum():
            if separator_pending and normalized_characters:
                normalized_characters.append("-")

            normalized_characters.append(character)

            separator_pending = False

        else:
            # Whitespace, underscores, punctuation and other separators all
            # become one pending hyphen. The hyphen is only added when another
            # alphanumeric character appears.
            separator_pending = True

    normalized_source_key = "".join(normalized_characters).strip("-")

    if not normalized_source_key:
        raise InvalidSourceKeyError("Source key must contain at least one letter or number.")

    if len(normalized_source_key) > MAX_SOURCE_KEY_LENGTH:
        raise InvalidSourceKeyError(f"Source key cannot exceed {MAX_SOURCE_KEY_LENGTH} characters.")

    return normalized_source_key


def extract_safe_filename(
    filename: str | None,
) -> str:
    """
    Extract only the final filename component.

    Some browsers submit paths such as:
    C:\\fakepath\\guest-policies.pdf

    We keep only:
    guest-policies.pdf
    """

    if filename is None:
        raise InvalidPdfUploadError("A PDF filename is required.")

    normalized_path = filename.replace(
        "\\",
        "/",
    )

    safe_filename = normalized_path.rsplit(
        "/",
        maxsplit=1,
    )[-1].strip()

    if not safe_filename:
        raise InvalidPdfUploadError("A PDF filename is required.")

    if len(safe_filename) > MAX_ORIGINAL_FILENAME_LENGTH:
        raise InvalidPdfUploadError(
            f"PDF filename cannot exceed {MAX_ORIGINAL_FILENAME_LENGTH} characters."
        )

    return safe_filename


def normalize_content_type(
    content_type: str | None,
) -> str:
    """
    Normalize an HTTP content type.

    A client could send:
    application/pdf; charset=binary

    For comparison we retain only:
    application/pdf
    """

    if content_type is None:
        return ""

    return (
        content_type.split(
            ";",
            maxsplit=1,
        )[0]
        .strip()
        .lower()
    )


def validate_pdf_upload(
    *,
    filename: str | None,
    content_type: str | None,
    file_bytes: bytes,
    max_upload_mb: int,
) -> ValidatedPdfUpload:
    """
    Perform inexpensive validation before PDF extraction begins.

    Validation includes:
    - safe filename extraction;
    - .pdf filename extension;
    - application/pdf MIME type;
    - non-empty file;
    - configured size limit;
    - PDF header presence near the beginning of the file.

    This is preliminary validation. PyMuPDF will later perform the actual
    structural parsing of the PDF.
    """

    if max_upload_mb <= 0:
        raise ValueError("max_upload_mb must be greater than zero.")

    safe_filename = extract_safe_filename(filename)

    if not safe_filename.lower().endswith(".pdf"):
        raise InvalidPdfUploadError("Uploaded file must use the .pdf extension.")

    normalized_content_type = normalize_content_type(content_type)

    if normalized_content_type != PDF_CONTENT_TYPE:
        raise InvalidPdfUploadError("Uploaded file must have the application/pdf content type.")

    if not file_bytes:
        raise InvalidPdfUploadError("Uploaded PDF is empty.")

    max_upload_bytes = max_upload_mb * 1024 * 1024

    if len(file_bytes) > max_upload_bytes:
        raise InvalidPdfUploadError(f"Uploaded PDF exceeds the {max_upload_mb} MB size limit.")

    header_area = file_bytes[:PDF_HEADER_SEARCH_LIMIT]

    if PDF_HEADER not in header_area:
        raise InvalidPdfUploadError("Uploaded file does not contain a valid PDF header.")

    return ValidatedPdfUpload(
        original_filename=safe_filename,
        size_bytes=len(file_bytes),
        checksum=calculate_file_checksum(file_bytes),
    )

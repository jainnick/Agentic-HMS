from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from uuid import UUID

import structlog
from anyio import to_thread
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.knowledge.chunking import (
    ChunkingError,
    PreparedChunk,
    prepare_chunks,
)
from app.modules.knowledge.embeddings import (
    EmbeddingError,
    embed_texts_async,
)
from app.modules.knowledge.enums import (
    KnowledgeSourceType,
)
from app.modules.knowledge.extraction import (
    PdfExtractionError,
    extract_pdf_pages,
)
from app.modules.knowledge.ingestion import (
    normalize_document_title,
    normalize_source_key,
    validate_pdf_upload,
)
from app.db.models import (
    KnowledgeDocument,
)

from app.modules.knowledge.repository import (
    KnowledgeRepositoryError,
    create_processing_document,
    deactivate_previous_versions,
    find_duplicate_document,
    get_next_version_number,
    insert_document_chunks,
    mark_document_failed,
    mark_document_ready,
)

logger = structlog.get_logger(__name__)


class KnowledgeServiceError(Exception):
    """Base error raised by the knowledge service."""


class DuplicateKnowledgeDocumentError(KnowledgeServiceError):
    """Raised when the same source file has already been uploaded."""

    def __init__(
        self,
        *,
        existing_document_id: UUID,
        existing_version_number: int,
    ) -> None:
        super().__init__("This PDF has already been uploaded for the same knowledge source.")

        self.existing_document_id = existing_document_id
        self.existing_version_number = existing_version_number


class KnowledgeDocumentCreationConflictError(KnowledgeServiceError):
    """
    Raised when concurrent writes conflict while creating a new version.
    """


@dataclass(frozen=True, slots=True)
class PdfKnowledgeIngestionResult:
    """Result returned after a PDF is fully ingested."""

    document: KnowledgeDocument
    chunk_count: int


def prepare_pdf_chunks(
    pdf_bytes: bytes,
    *,
    chunk_size_words: int,
    overlap_words: int,
) -> list[PreparedChunk]:
    """
    Extract pages and convert them into prepared chunks.

    This synchronous helper is run through prepare_pdf_chunks_async() so
    PyMuPDF and chunking do not occupy FastAPI's event-loop thread.
    """

    pages = extract_pdf_pages(pdf_bytes)

    return prepare_chunks(
        pages,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
    )


async def prepare_pdf_chunks_async(
    pdf_bytes: bytes,
    *,
    chunk_size_words: int,
    overlap_words: int,
) -> list[PreparedChunk]:
    """
    Run PDF extraction and chunking in an AnyIO worker thread.
    """

    preparation_call = partial(
        prepare_pdf_chunks,
        pdf_bytes,
        chunk_size_words=chunk_size_words,
        overlap_words=overlap_words,
    )

    return await to_thread.run_sync(preparation_call)


def build_safe_processing_error_message(
    error: Exception,
) -> str:
    """
    Convert an internal exception into a safe database error message.

    Detailed exceptions and tracebacks belong in application logs. The
    database stores only messages suitable for an administrator to see.
    """

    if isinstance(
        error,
        PdfExtractionError,
    ):
        return str(error)

    if isinstance(
        error,
        ChunkingError,
    ):
        return str(error)

    if isinstance(
        error,
        EmbeddingError,
    ):
        return "The embedding model could not process this document."

    if isinstance(
        error,
        KnowledgeRepositoryError,
    ):
        return "The document chunks could not be stored."

    return "Document processing failed."


async def ingest_pdf_document(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    created_by: UUID,
    title: str,
    source_key: str,
    filename: str | None,
    content_type: str | None,
    pdf_bytes: bytes,
) -> PdfKnowledgeIngestionResult:
    """
    Validate, process, and persist one PDF knowledge document.

    Transaction 1 permanently creates the PROCESSING document.

    Transaction 2 stores chunks and marks the document READY.

    When processing fails after Transaction 1, unfinished work is rolled
    back and a separate transaction marks the document FAILED.
    """

    settings = get_settings()

    normalized_title = normalize_document_title(title)

    normalized_source_key = normalize_source_key(source_key)

    validated_upload = validate_pdf_upload(
        filename=filename,
        content_type=content_type,
        file_bytes=pdf_bytes,
        max_upload_mb=settings.knowledge_max_upload_mb,
    )

    duplicate_document = await find_duplicate_document(
        session,
        organization_id=organization_id,
        property_id=property_id,
        source_key=normalized_source_key,
        checksum=validated_upload.checksum,
    )

    if duplicate_document is not None:
        raise DuplicateKnowledgeDocumentError(
            existing_document_id=duplicate_document.id,
            existing_version_number=(duplicate_document.version_number),
        )

    version_number = await get_next_version_number(
        session,
        organization_id=organization_id,
        property_id=property_id,
        source_key=normalized_source_key,
    )

    try:
        document = await create_processing_document(
            session,
            organization_id=organization_id,
            property_id=property_id,
            created_by=created_by,
            title=normalized_title,
            source_key=normalized_source_key,
            version_number=version_number,
            checksum=validated_upload.checksum,
            source_type=KnowledgeSourceType.PDF,
            original_filename=(validated_upload.original_filename),
        )

        # This commit makes the PROCESSING record durable.
        await session.commit()

    except IntegrityError as error:
        await session.rollback()

        raise KnowledgeDocumentCreationConflictError(
            "A conflicting knowledge-document version was created "
            "at the same time. Retry the upload."
        ) from error

    try:
        prepared_chunks = await prepare_pdf_chunks_async(
            pdf_bytes,
            chunk_size_words=(settings.knowledge_chunk_size),
            overlap_words=(settings.knowledge_chunk_overlap),
        )

        chunk_texts = [chunk.content for chunk in prepared_chunks]

        embeddings = await embed_texts_async(chunk_texts)

        chunk_rows = await insert_document_chunks(
            session,
            document=document,
            prepared_chunks=prepared_chunks,
            embeddings=embeddings,
        )

        await deactivate_previous_versions(
            session,
            organization_id=organization_id,
            property_id=property_id,
            source_key=normalized_source_key,
            current_document_id=document.id,
        )

        await mark_document_ready(
            session,
            document=document,
        )

        # Chunks, old-version deactivation and READY status become
        # permanent together.
        await session.commit()

        logger.info(
            "knowledge_pdf_ingestion_succeeded",
            organization_id=str(organization_id),
            property_id=str(property_id),
            document_id=str(document.id),
            source_key=normalized_source_key,
            version_number=version_number,
            chunk_count=len(chunk_rows),
        )

        return PdfKnowledgeIngestionResult(
            document=document,
            chunk_count=len(chunk_rows),
        )

    except Exception as error:
        # Remove any unfinished chunk rows or status updates from the
        # unsuccessful processing transaction.
        await session.rollback()

        safe_error_message = build_safe_processing_error_message(error)

        logger.exception(
            "knowledge_pdf_ingestion_failed",
            organization_id=str(organization_id),
            property_id=str(property_id),
            document_id=str(document.id),
            source_key=normalized_source_key,
            version_number=version_number,
        )

        try:
            await mark_document_failed(
                session,
                organization_id=organization_id,
                property_id=property_id,
                document_id=document.id,
                error_message=safe_error_message,
            )

            await session.commit()

        except Exception:
            await session.rollback()

            logger.exception(
                "knowledge_document_failure_status_update_failed",
                organization_id=str(organization_id),
                property_id=str(property_id),
                document_id=str(document.id),
            )

        # Preserve the original exception type for the future API route.
        raise

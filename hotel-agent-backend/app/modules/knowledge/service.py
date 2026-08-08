from __future__ import annotations

from dataclasses import dataclass
from functools import partial
from uuid import UUID

import structlog
from anyio import to_thread
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import (
    KnowledgeDocument,
)
from app.modules.knowledge.chunking import (
    ChunkingError,
    PreparedChunk,
    prepare_chunks,
)
from app.modules.knowledge.embeddings import (
    EmbeddingError,
    count_embedding_tokens,
    embed_query_async,
    embed_texts_async,
    split_text_by_embedding_tokens,
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
from app.modules.knowledge.repository import (
    KnowledgeRepositoryError,
    create_processing_document,
    deactivate_previous_versions,
    find_duplicate_document,
    get_next_version_number,
    insert_document_chunks,
    mark_document_failed,
    mark_document_ready,
    search_knowledge_chunks,
)

logger = structlog.get_logger(__name__)

MAX_KNOWLEDGE_QUERY_LENGTH = 2_000
MAX_KNOWLEDGE_MATCH_COUNT = 20


class KnowledgeServiceError(Exception):
    """Base error raised by the knowledge service."""


class KnowledgeSearchValidationError(KnowledgeServiceError):
    """Raised when a knowledge-search request contains invalid values."""


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


@dataclass(frozen=True, slots=True)
class KnowledgeSearchMatch:
    """
    One relevant knowledge chunk returned by the retrieval service.

    This object is independent of FastAPI and can be consumed by an API route,
    an agent tool, or another internal service.
    """

    chunk_id: UUID
    document_id: UUID

    document_title: str
    source_key: str
    version_number: int

    chunk_index: int
    content: str
    heading: str | None
    page_number: int | None

    similarity: float


def normalize_knowledge_search_query(
    query: str,
) -> str:
    """
    Normalize and validate a hotel-knowledge search query.

    Tabs, new lines, and repeated spaces are collapsed into single spaces.
    The actual words and punctuation are preserved.
    """

    normalized_query = " ".join(query.split()).strip()

    if not normalized_query:
        raise KnowledgeSearchValidationError("Knowledge search query cannot be blank.")

    if len(normalized_query) > MAX_KNOWLEDGE_QUERY_LENGTH:
        raise KnowledgeSearchValidationError(
            f"Knowledge search query cannot exceed {MAX_KNOWLEDGE_QUERY_LENGTH} characters."
        )

    return normalized_query


def resolve_knowledge_match_count(
    match_count: int | None,
    *,
    default_match_count: int,
) -> int:
    """
    Resolve the number of chunks retrieval may return.

    When the caller does not provide a value, the configured application
    default is used.
    """

    resolved_match_count = default_match_count if match_count is None else match_count

    if not 1 <= resolved_match_count <= MAX_KNOWLEDGE_MATCH_COUNT:
        raise KnowledgeSearchValidationError(
            f"Knowledge match count must be between 1 and {MAX_KNOWLEDGE_MATCH_COUNT}."
        )

    return resolved_match_count


def resolve_knowledge_min_similarity(
    min_similarity: float | None,
    *,
    default_min_similarity: float,
) -> float:
    """
    Resolve and validate the minimum cosine-similarity threshold.

    When the caller does not provide a value, the configured default is used.
    Valid similarity values are between 0 and 1.
    """

    resolved_min_similarity = default_min_similarity if min_similarity is None else min_similarity

    if not 0.0 <= resolved_min_similarity <= 1.0:
        raise KnowledgeSearchValidationError("Minimum similarity must be between 0 and 1.")

    return float(resolved_min_similarity)


async def search_property_knowledge(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    query: str,
    match_count: int | None = None,
    min_similarity: float | None = None,
) -> list[KnowledgeSearchMatch]:
    """
    Search active hotel knowledge for one organization and property.

    This service:
    1. validates and normalizes the query;
    2. resolves retrieval settings;
    3. generates the query embedding;
    4. executes tenant-filtered vector retrieval;
    5. maps repository rows into service-level results.

    Tenant identifiers must come from a verified TenantContext. They must not
    be accepted from an LLM-generated tool payload.
    """

    settings = get_settings()

    normalized_query = normalize_knowledge_search_query(query)

    resolved_match_count = resolve_knowledge_match_count(
        match_count,
        default_match_count=settings.rag_match_count,
    )

    resolved_min_similarity = resolve_knowledge_min_similarity(
        min_similarity,
        default_min_similarity=settings.rag_min_similarity,
    )

    query_embedding = await embed_query_async(normalized_query)

    repository_rows = await search_knowledge_chunks(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query_embedding=query_embedding,
        match_count=resolved_match_count,
        min_similarity=resolved_min_similarity,
    )

    matches: list[KnowledgeSearchMatch] = []

    for row in repository_rows:
        matches.append(
            KnowledgeSearchMatch(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                document_title=row.document_title,
                source_key=row.source_key,
                version_number=row.version_number,
                chunk_index=row.chunk_index,
                content=row.content,
                heading=row.heading,
                page_number=row.page_number,
                similarity=row.similarity,
            )
        )

    return matches


def prepare_pdf_chunks(
    pdf_bytes: bytes,
    *,
    target_tokens: int,
    max_tokens: int,
    fallback_overlap_tokens: int,
) -> list[PreparedChunk]:
    """
    Extract PDF pages and create adaptive tokenizer-aware chunks.

    The same tokenizer used by the embedding model controls chunk size.
    """

    pages = extract_pdf_pages(
        pdf_bytes,
    )

    return prepare_chunks(
        pages,
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        fallback_overlap_tokens=(fallback_overlap_tokens),
        token_counter=count_embedding_tokens,
        token_window_splitter=(split_text_by_embedding_tokens),
    )


async def prepare_pdf_chunks_async(
    pdf_bytes: bytes,
    *,
    target_tokens: int,
    max_tokens: int,
    fallback_overlap_tokens: int,
) -> list[PreparedChunk]:
    """Run PDF extraction and adaptive chunking in a worker thread."""

    preparation_call = partial(
        prepare_pdf_chunks,
        pdf_bytes,
        target_tokens=target_tokens,
        max_tokens=max_tokens,
        fallback_overlap_tokens=(fallback_overlap_tokens),
    )

    return await to_thread.run_sync(
        preparation_call,
    )


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
            target_tokens=(settings.knowledge_chunk_target_tokens),
            max_tokens=(settings.knowledge_chunk_max_tokens),
            fallback_overlap_tokens=(settings.knowledge_chunk_fallback_overlap_tokens),
        )

        token_counts: list[int] = []

        for chunk in prepared_chunks:
            token_count = chunk.metadata.get(
                "token_count",
            )

            if isinstance(
                token_count,
                int,
            ):
                token_counts.append(
                    token_count,
                )

        logger.info(
            "knowledge_pdf_chunks_prepared",
            organization_id=str(
                organization_id,
            ),
            property_id=str(
                property_id,
            ),
            document_id=str(
                document.id,
            ),
            page_count=len(
                {chunk.page_number for chunk in prepared_chunks if chunk.page_number is not None}
            ),
            chunk_count=len(
                prepared_chunks,
            ),
            minimum_chunk_tokens=(min(token_counts) if token_counts else None),
            maximum_chunk_tokens=(max(token_counts) if token_counts else None),
            average_chunk_tokens=(
                round(
                    sum(token_counts) / len(token_counts),
                    2,
                )
                if token_counts
                else None
            ),
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

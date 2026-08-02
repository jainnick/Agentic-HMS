from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import (
    Float,
    and_,
    func,
    select,
    update,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KnowledgeChunk,
    KnowledgeDocument,
)
from app.modules.knowledge.chunking import PreparedChunk
from app.modules.knowledge.embeddings import EmbeddingVector
from app.modules.knowledge.enums import (
    KnowledgeDocumentStatus,
    KnowledgeSourceType,
)


class KnowledgeRepositoryError(Exception):
    """Base error raised by knowledge repository operations."""


class KnowledgeChunkCountMismatchError(KnowledgeRepositoryError):
    """
    Raised when chunks and embeddings do not have a one-to-one relationship.
    """


@dataclass(frozen=True, slots=True)
class KnowledgeSearchRow:
    """
    One knowledge chunk returned by vector retrieval.

    This is a repository result, not an HTTP response. The service and API
    layers will later decide which fields should be exposed externally.
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


async def find_duplicate_document(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    source_key: str,
    checksum: str,
) -> KnowledgeDocument | None:
    """
    Find an existing active or in-progress copy of the same source file.

    A document is considered a duplicate when all of these match:
    - organization;
    - property;
    - logical source key;
    - complete-file checksum.

    Failed documents are intentionally excluded so the same file can be
    uploaded again after a temporary processing failure.
    """

    statement = (
        select(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.property_id == property_id,
            KnowledgeDocument.source_key == source_key,
            KnowledgeDocument.checksum == checksum,
            KnowledgeDocument.status.in_(
                [
                    KnowledgeDocumentStatus.PROCESSING,
                    KnowledgeDocumentStatus.READY,
                ]
            ),
        )
        .order_by(KnowledgeDocument.version_number.desc())
        .limit(1)
    )

    result: KnowledgeDocument | None = await session.scalar(statement)

    return result


async def get_next_version_number(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    source_key: str,
) -> int:
    """
    Return the next version number for one logical knowledge source.

    Examples:
    - no existing versions -> 1;
    - latest version is 1 -> 2;
    - latest version is 5 -> 6.

    Failed versions are included because version numbers must remain unique
    and should never be reused.
    """

    statement = select(func.max(KnowledgeDocument.version_number)).where(
        KnowledgeDocument.organization_id == organization_id,
        KnowledgeDocument.property_id == property_id,
        KnowledgeDocument.source_key == source_key,
    )

    latest_version = await session.scalar(statement)

    if latest_version is None:
        return 1

    return int(latest_version) + 1


async def create_processing_document(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    created_by: UUID,
    title: str,
    source_key: str,
    version_number: int,
    checksum: str,
    source_type: KnowledgeSourceType,
    original_filename: str | None,
) -> KnowledgeDocument:
    """
    Add a new processing document to the current database transaction.

    This function calls flush(), not commit(). The service layer decides
    when the transaction becomes permanent.
    """

    document = KnowledgeDocument(
        organization_id=organization_id,
        property_id=property_id,
        created_by=created_by,
        title=title,
        source_key=source_key,
        version_number=version_number,
        checksum=checksum,
        source_type=source_type,
        original_filename=original_filename,
        status=KnowledgeDocumentStatus.PROCESSING,
        is_active=False,
        error_message=None,
    )

    session.add(document)

    await session.flush()

    return document


async def insert_document_chunks(
    session: AsyncSession,
    *,
    document: KnowledgeDocument,
    prepared_chunks: list[PreparedChunk],
    embeddings: list[EmbeddingVector],
) -> list[KnowledgeChunk]:
    """
    Convert prepared chunks and embeddings into database rows.

    The order must remain aligned:

    prepared_chunks[0] <-> embeddings[0]
    prepared_chunks[1] <-> embeddings[1]
    """

    if len(prepared_chunks) != len(embeddings):
        raise KnowledgeChunkCountMismatchError(
            "The number of prepared chunks does not match the number of embeddings."
        )

    chunk_rows: list[KnowledgeChunk] = []

    for prepared_chunk, embedding in zip(
        prepared_chunks,
        embeddings,
        strict=True,
    ):
        chunk_row = KnowledgeChunk(
            organization_id=document.organization_id,
            property_id=document.property_id,
            document_id=document.id,
            chunk_index=prepared_chunk.chunk_index,
            heading=prepared_chunk.heading,
            content=prepared_chunk.content,
            page_number=prepared_chunk.page_number,
            content_hash=prepared_chunk.content_hash,
            embedding=embedding,
            metadata_={},
        )

        chunk_rows.append(chunk_row)

    session.add_all(chunk_rows)

    await session.flush()

    return chunk_rows


async def deactivate_previous_versions(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    source_key: str,
    current_document_id: UUID,
) -> None:
    """
    Deactivate earlier active versions of the same logical source.

    The current document is explicitly excluded.
    """

    statement = (
        update(KnowledgeDocument)
        .where(
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.property_id == property_id,
            KnowledgeDocument.source_key == source_key,
            KnowledgeDocument.id != current_document_id,
            KnowledgeDocument.is_active.is_(True),
        )
        .values(
            is_active=False,
            updated_at=func.now(),
        )
    )

    await session.execute(statement)

    await session.flush()


async def mark_document_ready(
    session: AsyncSession,
    *,
    document: KnowledgeDocument,
) -> None:
    """
    Mark a successfully processed document as ready and active.

    Earlier versions should be deactivated before this function is called.
    """

    document.status = KnowledgeDocumentStatus.READY
    document.is_active = True
    document.error_message = None

    await session.flush()


async def mark_document_failed(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    document_id: UUID,
    error_message: str,
) -> None:
    """
    Mark a previously committed processing document as failed.

    This uses an UPDATE statement rather than relying on the original ORM
    object. After rollback, an ORM object's state may no longer be reliable.
    """

    safe_error_message = error_message.strip() or "Document processing failed."

    statement = (
        update(KnowledgeDocument)
        .where(
            KnowledgeDocument.id == document_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.property_id == property_id,
        )
        .values(
            status=KnowledgeDocumentStatus.FAILED,
            is_active=False,
            error_message=safe_error_message,
            updated_at=func.now(),
        )
    )

    await session.execute(statement)

    await session.flush()


async def get_document_by_id(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    document_id: UUID,
) -> KnowledgeDocument | None:
    """
    Retrieve one document while enforcing tenant filters.

    The tenant filters remain present even though document IDs are UUIDs.
    A UUID is an identifier, not an authorization mechanism.
    """

    statement = select(KnowledgeDocument).where(
        KnowledgeDocument.id == document_id,
        KnowledgeDocument.organization_id == organization_id,
        KnowledgeDocument.property_id == property_id,
    )

    result: KnowledgeDocument | None = await session.scalar(statement)

    return result


async def search_knowledge_chunks(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    query_embedding: EmbeddingVector,
    match_count: int,
    min_similarity: float,
) -> list[KnowledgeSearchRow]:
    """
    Find the most relevant active knowledge chunks for one hotel property.

    The caller is responsible for validating:
    - query_embedding;
    - match_count;
    - min_similarity.

    This repository function focuses only on constructing and executing the
    tenant-filtered PostgreSQL vector query.
    """

    cosine_distance = KnowledgeChunk.embedding.op(
        "<=>",
        return_type=Float,
    )(query_embedding)

    similarity = (1.0 - cosine_distance).label("similarity")

    maximum_distance = 1.0 - min_similarity

    statement = (
        select(
            KnowledgeChunk.id,
            KnowledgeChunk.document_id,
            KnowledgeDocument.title,
            KnowledgeDocument.source_key,
            KnowledgeDocument.version_number,
            KnowledgeChunk.chunk_index,
            KnowledgeChunk.content,
            KnowledgeChunk.heading,
            KnowledgeChunk.page_number,
            similarity,
        )
        .join(
            KnowledgeDocument,
            and_(
                KnowledgeDocument.id == KnowledgeChunk.document_id,
                KnowledgeDocument.organization_id == KnowledgeChunk.organization_id,
                KnowledgeDocument.property_id == KnowledgeChunk.property_id,
            ),
        )
        .where(
            KnowledgeChunk.organization_id == organization_id,
            KnowledgeChunk.property_id == property_id,
            KnowledgeDocument.organization_id == organization_id,
            KnowledgeDocument.property_id == property_id,
            KnowledgeDocument.status == KnowledgeDocumentStatus.READY,
            KnowledgeDocument.is_active.is_(True),
            cosine_distance <= maximum_distance,
        )
        .order_by(cosine_distance.asc())
        .limit(match_count)
    )

    result = await session.execute(statement)

    search_rows: list[KnowledgeSearchRow] = []

    for row in result.all():
        search_rows.append(
            KnowledgeSearchRow(
                chunk_id=row[0],
                document_id=row[1],
                document_title=row[2],
                source_key=row[3],
                version_number=row[4],
                chunk_index=row[5],
                content=row[6],
                heading=row[7],
                page_number=row[8],
                similarity=float(row[9]),
            )
        )

    return search_rows

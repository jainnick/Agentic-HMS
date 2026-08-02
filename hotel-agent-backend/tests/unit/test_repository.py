from __future__ import annotations

from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.chunking import (
    PreparedChunk,
)
from app.modules.knowledge.enums import (
    KnowledgeDocumentStatus,
    KnowledgeSourceType,
)
from app.modules.knowledge.models import (
    KnowledgeDocument,
)
from app.modules.knowledge.repository import (
    KnowledgeChunkCountMismatchError,
    create_processing_document,
    get_next_version_number,
    insert_document_chunks,
    mark_document_ready,
)


def build_mock_session() -> MagicMock:
    """
    Build an AsyncSession-shaped mock.

    add() and add_all() are synchronous SQLAlchemy methods.
    flush() and scalar() are asynchronous methods.
    """

    session = MagicMock(spec=AsyncSession)

    session.flush = AsyncMock()
    session.scalar = AsyncMock()

    return session


@pytest.mark.asyncio
async def test_create_processing_document_sets_initial_state() -> None:
    session = build_mock_session()

    organization_id = uuid4()
    property_id = uuid4()
    created_by = uuid4()

    document = await create_processing_document(
        session,
        organization_id=organization_id,
        property_id=property_id,
        created_by=created_by,
        title="Guest Policies",
        source_key="guest-policies",
        version_number=1,
        checksum="a" * 64,
        source_type=KnowledgeSourceType.PDF,
        original_filename="guest-policies.pdf",
    )

    assert document.organization_id == organization_id
    assert document.property_id == property_id
    assert document.created_by == created_by
    assert document.status == KnowledgeDocumentStatus.PROCESSING
    assert document.is_active is False
    assert document.error_message is None

    session.add.assert_called_once_with(document)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_next_version_number_returns_one_when_none_exist() -> None:
    session = build_mock_session()
    session.scalar.return_value = None

    version_number = await get_next_version_number(
        session,
        organization_id=uuid4(),
        property_id=uuid4(),
        source_key="guest-policies",
    )

    assert version_number == 1


@pytest.mark.asyncio
async def test_get_next_version_number_increments_latest() -> None:
    session = build_mock_session()
    session.scalar.return_value = 4

    version_number = await get_next_version_number(
        session,
        organization_id=uuid4(),
        property_id=uuid4(),
        source_key="guest-policies",
    )

    assert version_number == 5


@pytest.mark.asyncio
async def test_insert_document_chunks_maps_chunks_and_embeddings() -> None:
    session = build_mock_session()

    document = KnowledgeDocument(
        id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        created_by=uuid4(),
        title="Guest Policies",
        source_key="guest-policies",
        version_number=1,
        checksum="a" * 64,
        source_type=KnowledgeSourceType.PDF,
        original_filename="guest-policies.pdf",
        status=KnowledgeDocumentStatus.PROCESSING,
        is_active=False,
    )

    prepared_chunks = [
        PreparedChunk(
            chunk_index=0,
            content="Pets are allowed with prior approval.",
            page_number=2,
            heading=None,
            content_hash="b" * 64,
        ),
        PreparedChunk(
            chunk_index=1,
            content="Checkout is at 11 AM.",
            page_number=3,
            heading="Checkout",
            content_hash="c" * 64,
        ),
    ]

    embeddings = [
        [0.0] * 384,
        [1.0] * 384,
    ]

    rows = await insert_document_chunks(
        session,
        document=document,
        prepared_chunks=prepared_chunks,
        embeddings=embeddings,
    )

    assert len(rows) == 2

    assert rows[0].document_id == document.id
    assert rows[0].organization_id == document.organization_id
    assert rows[0].property_id == document.property_id
    assert rows[0].chunk_index == 0
    assert rows[0].content == prepared_chunks[0].content
    assert rows[0].embedding == embeddings[0]

    assert rows[1].chunk_index == 1
    assert rows[1].heading == "Checkout"
    assert rows[1].page_number == 3
    assert rows[1].embedding == embeddings[1]

    session.add_all.assert_called_once_with(rows)
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_insert_document_chunks_rejects_count_mismatch() -> None:
    session = build_mock_session()

    document = KnowledgeDocument(
        id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        created_by=uuid4(),
        title="Guest Policies",
        source_key="guest-policies",
        version_number=1,
        checksum="a" * 64,
        source_type=KnowledgeSourceType.PDF,
        original_filename="guest-policies.pdf",
        status=KnowledgeDocumentStatus.PROCESSING,
        is_active=False,
    )

    prepared_chunks = [
        PreparedChunk(
            chunk_index=0,
            content="Pet policy.",
            page_number=1,
            heading=None,
            content_hash="b" * 64,
        )
    ]

    embeddings = [
        [0.0] * 384,
        [1.0] * 384,
    ]

    with pytest.raises(
        KnowledgeChunkCountMismatchError,
        match="does not match",
    ):
        await insert_document_chunks(
            session,
            document=document,
            prepared_chunks=prepared_chunks,
            embeddings=embeddings,
        )

    session.add_all.assert_not_called()
    session.flush.assert_not_awaited()


@pytest.mark.asyncio
async def test_mark_document_ready_updates_state() -> None:
    session = build_mock_session()

    document = KnowledgeDocument(
        id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        created_by=uuid4(),
        title="Guest Policies",
        source_key="guest-policies",
        version_number=1,
        checksum="a" * 64,
        source_type=KnowledgeSourceType.PDF,
        original_filename="guest-policies.pdf",
        status=KnowledgeDocumentStatus.PROCESSING,
        is_active=False,
        error_message="Old error",
    )

    await mark_document_ready(
        session,
        document=document,
    )

    assert document.status == KnowledgeDocumentStatus.READY
    assert document.is_active is True
    assert document.error_message is None

    session.flush.assert_awaited_once()

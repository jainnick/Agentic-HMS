from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    KnowledgeDocument,
)
from app.modules.knowledge import (
    service as knowledge_service,
)
from app.modules.knowledge.chunking import (
    PreparedChunk,
)
from app.modules.knowledge.enums import (
    KnowledgeDocumentStatus,
    KnowledgeSourceType,
)
from app.modules.knowledge.extraction import (
    PdfTextNotFoundError,
)
from app.modules.knowledge.repository import (
    KnowledgeSearchRow,
)
from app.modules.knowledge.service import (
    DuplicateKnowledgeDocumentError,
    KnowledgeDocumentCreationConflictError,
    KnowledgeSearchValidationError,
    ingest_pdf_document,
    search_property_knowledge,
)


def build_mock_session() -> MagicMock:
    session = MagicMock(spec=AsyncSession)

    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()

    return session


def build_document(
    *,
    version_number: int = 1,
) -> KnowledgeDocument:
    return KnowledgeDocument(
        id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        created_by=uuid4(),
        title="Guest Policies",
        source_key="guest-policies",
        version_number=version_number,
        checksum="a" * 64,
        source_type=KnowledgeSourceType.PDF,
        original_filename="guest-policies.pdf",
        status=KnowledgeDocumentStatus.PROCESSING,
        is_active=False,
    )


def patch_test_settings(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = SimpleNamespace(
        knowledge_max_upload_mb=10,
        knowledge_chunk_size=500,
        knowledge_chunk_overlap=75,
        rag_match_count=6,
        rag_min_similarity=0.45,
    )

    monkeypatch.setattr(
        knowledge_service,
        "get_settings",
        lambda: settings,
    )


@pytest.mark.asyncio
async def test_ingest_pdf_document_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()
    document = build_document()

    prepared_chunks = [
        PreparedChunk(
            chunk_index=0,
            content="Checkout is at 11 AM.",
            page_number=1,
            heading=None,
            content_hash="b" * 64,
        )
    ]

    find_duplicate_mock = AsyncMock(return_value=None)
    get_version_mock = AsyncMock(return_value=1)
    create_document_mock = AsyncMock(return_value=document)
    prepare_chunks_mock = AsyncMock(return_value=prepared_chunks)
    embed_mock = AsyncMock(
        return_value=[
            [0.0] * 384,
        ]
    )
    insert_chunks_mock = AsyncMock(
        return_value=[
            MagicMock(),
        ]
    )
    deactivate_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "find_duplicate_document",
        find_duplicate_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "get_next_version_number",
        get_version_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "create_processing_document",
        create_document_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "prepare_pdf_chunks_async",
        prepare_chunks_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "embed_texts_async",
        embed_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "insert_document_chunks",
        insert_chunks_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "deactivate_previous_versions",
        deactivate_mock,
    )

    result = await ingest_pdf_document(
        session,
        organization_id=document.organization_id,
        property_id=document.property_id,
        created_by=document.created_by,
        title="  Guest   Policies  ",
        source_key="Guest Policies",
        filename="guest-policies.pdf",
        content_type="application/pdf",
        pdf_bytes=b"%PDF-1.7\nfake test content",
    )

    assert result.document is document
    assert result.chunk_count == 1
    assert document.status == KnowledgeDocumentStatus.READY
    assert document.is_active is True

    assert session.commit.await_count == 2
    session.rollback.assert_not_awaited()

    embed_mock.assert_awaited_once_with(
        [
            "Checkout is at 11 AM.",
        ]
    )

    insert_chunks_mock.assert_awaited_once()


@pytest.mark.asyncio
async def test_ingest_pdf_document_rejects_duplicate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    duplicate_document = build_document(version_number=3)

    find_duplicate_mock = AsyncMock(return_value=duplicate_document)
    get_version_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "find_duplicate_document",
        find_duplicate_mock,
    )
    monkeypatch.setattr(
        knowledge_service,
        "get_next_version_number",
        get_version_mock,
    )

    with pytest.raises(
        DuplicateKnowledgeDocumentError,
    ) as error_info:
        await ingest_pdf_document(
            session,
            organization_id=(duplicate_document.organization_id),
            property_id=(duplicate_document.property_id),
            created_by=uuid4(),
            title="Guest Policies",
            source_key="guest-policies",
            filename="guest-policies.pdf",
            content_type="application/pdf",
            pdf_bytes=b"%PDF-1.7\nsame content",
        )

    assert error_info.value.existing_document_id == duplicate_document.id
    assert error_info.value.existing_version_number == 3

    get_version_mock.assert_not_awaited()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_processing_failure_marks_document_failed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()
    document = build_document()

    monkeypatch.setattr(
        knowledge_service,
        "find_duplicate_document",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        knowledge_service,
        "get_next_version_number",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        knowledge_service,
        "create_processing_document",
        AsyncMock(return_value=document),
    )
    monkeypatch.setattr(
        knowledge_service,
        "prepare_pdf_chunks_async",
        AsyncMock(side_effect=PdfTextNotFoundError("The PDF contains no extractable text.")),
    )

    mark_failed_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "mark_document_failed",
        mark_failed_mock,
    )

    with pytest.raises(
        PdfTextNotFoundError,
    ):
        await ingest_pdf_document(
            session,
            organization_id=document.organization_id,
            property_id=document.property_id,
            created_by=document.created_by,
            title="Guest Policies",
            source_key="guest-policies",
            filename="guest-policies.pdf",
            content_type="application/pdf",
            pdf_bytes=b"%PDF-1.7\nfake content",
        )

    assert session.commit.await_count == 2
    session.rollback.assert_awaited_once()

    mark_failed_mock.assert_awaited_once_with(
        session,
        organization_id=document.organization_id,
        property_id=document.property_id,
        document_id=document.id,
        error_message=("The PDF contains no extractable text."),
    )


@pytest.mark.asyncio
async def test_processing_document_commit_conflict(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()
    document = build_document()

    session.commit.side_effect = IntegrityError(
        "INSERT INTO knowledge_documents",
        {},
        Exception("unique constraint violation"),
    )

    monkeypatch.setattr(
        knowledge_service,
        "find_duplicate_document",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        knowledge_service,
        "get_next_version_number",
        AsyncMock(return_value=1),
    )
    monkeypatch.setattr(
        knowledge_service,
        "create_processing_document",
        AsyncMock(return_value=document),
    )

    with pytest.raises(
        KnowledgeDocumentCreationConflictError,
        match="conflicting",
    ):
        await ingest_pdf_document(
            session,
            organization_id=document.organization_id,
            property_id=document.property_id,
            created_by=document.created_by,
            title="Guest Policies",
            source_key="guest-policies",
            filename="guest-policies.pdf",
            content_type="application/pdf",
            pdf_bytes=b"%PDF-1.7\nfake content",
        )

    session.rollback.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_property_knowledge_uses_defaults_and_maps_results(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    organization_id = uuid4()
    property_id = uuid4()
    chunk_id = uuid4()
    document_id = uuid4()

    query_embedding = [0.01] * 384

    repository_rows = [
        KnowledgeSearchRow(
            chunk_id=chunk_id,
            document_id=document_id,
            document_title="Guest Policies",
            source_key="guest-policies",
            version_number=2,
            chunk_index=3,
            content="Checkout time is 11:00 AM.",
            heading="Check-in and checkout",
            page_number=4,
            similarity=0.82,
        )
    ]

    embed_query_mock = AsyncMock(return_value=query_embedding)

    search_repository_mock = AsyncMock(return_value=repository_rows)

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        embed_query_mock,
    )

    monkeypatch.setattr(
        knowledge_service,
        "search_knowledge_chunks",
        search_repository_mock,
    )

    matches = await search_property_knowledge(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query="  What   time is\ncheckout?  ",
    )

    embed_query_mock.assert_awaited_once_with("What time is checkout?")

    search_repository_mock.assert_awaited_once_with(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query_embedding=query_embedding,
        match_count=6,
        min_similarity=0.45,
    )

    assert len(matches) == 1

    match = matches[0]

    assert match.chunk_id == chunk_id
    assert match.document_id == document_id
    assert match.document_title == "Guest Policies"
    assert match.source_key == "guest-policies"
    assert match.version_number == 2
    assert match.chunk_index == 3
    assert match.content == "Checkout time is 11:00 AM."
    assert match.heading == "Check-in and checkout"
    assert match.page_number == 4
    assert match.similarity == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_search_property_knowledge_uses_custom_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    organization_id = uuid4()
    property_id = uuid4()

    query_embedding = [0.02] * 384

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        AsyncMock(return_value=query_embedding),
    )

    search_repository_mock = AsyncMock(return_value=[])

    monkeypatch.setattr(
        knowledge_service,
        "search_knowledge_chunks",
        search_repository_mock,
    )

    matches = await search_property_knowledge(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query="Are pets allowed?",
        match_count=4,
        min_similarity=0.60,
    )

    assert matches == []

    search_repository_mock.assert_awaited_once_with(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query_embedding=query_embedding,
        match_count=4,
        min_similarity=0.60,
    )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "",
        "   ",
        "\n\t",
    ],
)
async def test_search_property_knowledge_rejects_blank_query(
    monkeypatch: pytest.MonkeyPatch,
    query: str,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    embed_query_mock = AsyncMock()
    search_repository_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        embed_query_mock,
    )

    monkeypatch.setattr(
        knowledge_service,
        "search_knowledge_chunks",
        search_repository_mock,
    )

    with pytest.raises(
        KnowledgeSearchValidationError,
        match="cannot be blank",
    ):
        await search_property_knowledge(
            session,
            organization_id=uuid4(),
            property_id=uuid4(),
            query=query,
        )

    embed_query_mock.assert_not_awaited()
    search_repository_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_search_property_knowledge_rejects_long_query(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    embed_query_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        embed_query_mock,
    )

    with pytest.raises(
        KnowledgeSearchValidationError,
        match="cannot exceed",
    ):
        await search_property_knowledge(
            session,
            organization_id=uuid4(),
            property_id=uuid4(),
            query="a" * 2_001,
        )

    embed_query_mock.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "match_count",
    [
        0,
        -1,
        21,
    ],
)
async def test_search_property_knowledge_rejects_invalid_match_count(
    monkeypatch: pytest.MonkeyPatch,
    match_count: int,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    embed_query_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        embed_query_mock,
    )

    with pytest.raises(
        KnowledgeSearchValidationError,
        match="match count",
    ):
        await search_property_knowledge(
            session,
            organization_id=uuid4(),
            property_id=uuid4(),
            query="What time is checkout?",
            match_count=match_count,
        )

    embed_query_mock.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "min_similarity",
    [
        -0.01,
        1.01,
    ],
)
async def test_search_property_knowledge_rejects_invalid_similarity(
    monkeypatch: pytest.MonkeyPatch,
    min_similarity: float,
) -> None:
    patch_test_settings(monkeypatch)

    session = build_mock_session()

    embed_query_mock = AsyncMock()

    monkeypatch.setattr(
        knowledge_service,
        "embed_query_async",
        embed_query_mock,
    )

    with pytest.raises(
        KnowledgeSearchValidationError,
        match="between 0 and 1",
    ):
        await search_property_knowledge(
            session,
            organization_id=uuid4(),
            property_id=uuid4(),
            query="What time is checkout?",
            min_similarity=min_similarity,
        )

    embed_query_mock.assert_not_awaited()

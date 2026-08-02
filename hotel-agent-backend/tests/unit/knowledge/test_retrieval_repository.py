from __future__ import annotations

from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.repository import (
    search_knowledge_chunks,
)


def build_mock_session() -> MagicMock:
    """Create an AsyncSession-shaped mock for repository tests."""

    session = MagicMock(spec=AsyncSession)

    session.execute = AsyncMock()

    return session


@pytest.mark.asyncio
async def test_search_knowledge_chunks_maps_database_rows() -> None:
    session = build_mock_session()

    organization_id = uuid4()
    property_id = uuid4()
    chunk_id = uuid4()
    document_id = uuid4()

    database_result = MagicMock()

    database_result.all.return_value = [
        (
            chunk_id,
            document_id,
            "Guest Policies",
            "guest-policies",
            2,
            3,
            "Checkout time is 11:00 AM.",
            "Check-in and checkout",
            4,
            0.82,
        )
    ]

    session.execute.return_value = database_result

    matches = await search_knowledge_chunks(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query_embedding=[0.0] * 384,
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

    session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_search_knowledge_chunks_returns_empty_list() -> None:
    session = build_mock_session()

    database_result = MagicMock()
    database_result.all.return_value = []

    session.execute.return_value = database_result

    matches = await search_knowledge_chunks(
        session,
        organization_id=uuid4(),
        property_id=uuid4(),
        query_embedding=[0.0] * 384,
        match_count=6,
        min_similarity=0.45,
    )

    assert matches == []


@pytest.mark.asyncio
async def test_search_query_contains_required_filters() -> None:
    session = build_mock_session()

    database_result = MagicMock()
    database_result.all.return_value = []

    session.execute.return_value = database_result

    organization_id = uuid4()
    property_id = uuid4()

    await search_knowledge_chunks(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query_embedding=[0.0] * 384,
        match_count=5,
        min_similarity=0.45,
    )

    executed_statement = session.execute.await_args.args[0]

    generated_sql = str(executed_statement)

    assert "knowledge_chunks.organization_id" in generated_sql
    assert "knowledge_chunks.property_id" in generated_sql
    assert "knowledge_documents.organization_id" in generated_sql
    assert "knowledge_documents.property_id" in generated_sql
    assert "knowledge_documents.status" in generated_sql
    assert "knowledge_documents.is_active" in generated_sql
    assert "<=>" in generated_sql
    assert "ORDER BY" in generated_sql
    assert "LIMIT" in generated_sql

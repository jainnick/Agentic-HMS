from __future__ import annotations

from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant.context import (
    AssistantToolContext,
    AssistantToolContextError,
)
from app.modules.assistant.tools import knowledge as knowledge_tool
from app.modules.assistant.tools.knowledge import (
    KnowledgeSearchToolInput,
    execute_knowledge_search_tool,
)
from app.modules.knowledge.service import KnowledgeSearchMatch
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import OrganizationRole


def build_mock_session() -> MagicMock:
    """Create an AsyncSession-shaped mock."""

    return MagicMock(
        spec=AsyncSession,
    )


def build_property_tenant_context() -> TenantContext:
    """Create a verified property context for an organization owner."""

    return TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
        property_role=None,
    )


def test_assistant_tool_context_from_tenant_context() -> None:
    session = build_mock_session()
    tenant_context = build_property_tenant_context()

    context = AssistantToolContext.from_tenant_context(
        session=session,
        tenant_context=tenant_context,
    )

    assert context.session is session
    assert context.organization_id == tenant_context.organization_id
    assert context.property_id == tenant_context.property_id


def test_assistant_tool_context_requires_property() -> None:
    session = build_mock_session()

    tenant_context = TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=None,
        organization_role=OrganizationRole.ORGANIZATION_OWNER,
        property_role=None,
    )

    with pytest.raises(
        AssistantToolContextError,
        match="property must be selected",
    ):
        AssistantToolContext.from_tenant_context(
            session=session,
            tenant_context=tenant_context,
        )


def test_knowledge_search_input_rejects_tenant_ids() -> None:
    with pytest.raises(
        ValidationError,
    ):
        KnowledgeSearchToolInput.model_validate(
            {
                "query": "What time is checkout?",
                "organization_id": str(uuid4()),
                "property_id": str(uuid4()),
            }
        )


def test_knowledge_search_input_rejects_excessive_match_count() -> None:
    with pytest.raises(
        ValidationError,
    ):
        KnowledgeSearchToolInput(
            query="What time is checkout?",
            match_count=7,
        )


@pytest.mark.asyncio
async def test_execute_knowledge_search_tool_uses_trusted_context(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = build_mock_session()

    organization_id = uuid4()
    property_id = uuid4()

    context = AssistantToolContext(
        session=session,
        organization_id=organization_id,
        property_id=property_id,
    )

    service_match = KnowledgeSearchMatch(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Guest Policies",
        source_key="guest-policies",
        version_number=2,
        chunk_index=3,
        content="Checkout time is 11:00 AM.",
        heading="Check-in and checkout",
        page_number=4,
        similarity=0.82,
    )

    search_service_mock = AsyncMock(
        return_value=[
            service_match,
        ]
    )

    monkeypatch.setattr(
        knowledge_tool,
        "search_property_knowledge",
        search_service_mock,
    )

    tool_input = KnowledgeSearchToolInput(
        query="What time is checkout?",
        match_count=5,
    )

    result = await execute_knowledge_search_tool(
        tool_input,
        context=context,
    )

    search_service_mock.assert_awaited_once_with(
        session,
        organization_id=organization_id,
        property_id=property_id,
        query="What time is checkout?",
        match_count=5,
    )

    assert result.query == "What time is checkout?"
    assert result.returned_count == 1
    assert len(result.matches) == 1

    match = result.matches[0]

    assert match.document_title == "Guest Policies"
    assert match.source_key == "guest-policies"
    assert match.heading == "Check-in and checkout"
    assert match.page_number == 4
    assert match.content == "Checkout time is 11:00 AM."
    assert match.similarity == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_execute_knowledge_search_tool_returns_empty_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = build_mock_session()

    context = AssistantToolContext(
        session=session,
        organization_id=uuid4(),
        property_id=uuid4(),
    )

    search_service_mock = AsyncMock(return_value=[])

    monkeypatch.setattr(
        knowledge_tool,
        "search_property_knowledge",
        search_service_mock,
    )

    result = await execute_knowledge_search_tool(
        KnowledgeSearchToolInput(
            query="Does the hotel offer helicopter transfers?",
        ),
        context=context,
    )

    assert result.returned_count == 0
    assert result.matches == []

    search_service_mock.assert_awaited_once_with(
        session,
        organization_id=context.organization_id,
        property_id=context.property_id,
        query="Does the hotel offer helicopter transfers?",
        match_count=None,
    )

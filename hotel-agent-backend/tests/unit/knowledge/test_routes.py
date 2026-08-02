from __future__ import annotations

from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import (
    routes as knowledge_routes,
)
from app.modules.knowledge.schemas import (
    KnowledgeSearchRequest,
)
from app.modules.knowledge.service import (
    KnowledgeSearchMatch,
    KnowledgeSearchValidationError,
)
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)


def build_mock_session() -> MagicMock:
    """Create an AsyncSession-shaped mock."""

    return MagicMock(spec=AsyncSession)


def build_owner_tenant_context() -> TenantContext:
    """Create a verified property context for an organization owner."""

    return TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        organization_role=(OrganizationRole.ORGANIZATION_OWNER),
        property_role=None,
    )


@pytest.mark.asyncio
async def test_search_knowledge_test_returns_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = build_mock_session()
    tenant_context = build_owner_tenant_context()

    chunk_id = uuid4()
    document_id = uuid4()

    search_match = KnowledgeSearchMatch(
        chunk_id=chunk_id,
        document_id=document_id,
        document_title="Guest Policies",
        source_key="guest-policies",
        version_number=1,
        chunk_index=0,
        content="Checkout time is 11:00 AM.",
        heading="Check-in and checkout",
        page_number=3,
        similarity=0.82,
    )

    search_service_mock = AsyncMock(
        return_value=[
            search_match,
        ]
    )

    monkeypatch.setattr(
        knowledge_routes,
        "search_property_knowledge",
        search_service_mock,
    )

    request = KnowledgeSearchRequest(
        query="What time is checkout?",
        match_count=6,
        min_similarity=0.45,
    )

    response = await knowledge_routes.search_knowledge_test(
        request=request,
        tenant_context=tenant_context,
        session=session,
    )

    search_service_mock.assert_awaited_once_with(
        session,
        organization_id=(tenant_context.organization_id),
        property_id=tenant_context.property_id,
        query="What time is checkout?",
        match_count=6,
        min_similarity=0.45,
    )

    assert response.query == "What time is checkout?"
    assert response.returned_count == 1
    assert len(response.matches) == 1

    match = response.matches[0]

    assert match.chunk_id == chunk_id
    assert match.document_id == document_id
    assert match.document_title == "Guest Policies"
    assert match.content == "Checkout time is 11:00 AM."
    assert match.page_number == 3
    assert match.similarity == pytest.approx(0.82)


@pytest.mark.asyncio
async def test_search_knowledge_test_returns_empty_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = build_mock_session()
    tenant_context = build_owner_tenant_context()

    monkeypatch.setattr(
        knowledge_routes,
        "search_property_knowledge",
        AsyncMock(return_value=[]),
    )

    response = await knowledge_routes.search_knowledge_test(
        request=KnowledgeSearchRequest(
            query="Does the hotel offer helicopter transfers?",
        ),
        tenant_context=tenant_context,
        session=session,
    )

    assert response.returned_count == 0
    assert response.matches == []


@pytest.mark.asyncio
async def test_search_knowledge_test_requires_property() -> None:
    session = build_mock_session()

    tenant_context = TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=None,
        organization_role=(OrganizationRole.ORGANIZATION_OWNER),
        property_role=None,
    )

    with pytest.raises(
        HTTPException,
    ) as error_info:
        await knowledge_routes.search_knowledge_test(
            request=KnowledgeSearchRequest(
                query="What time is checkout?",
            ),
            tenant_context=tenant_context,
            session=session,
        )

    assert error_info.value.status_code == 400
    assert "X-Property-ID" in str(error_info.value.detail)


@pytest.mark.asyncio
async def test_search_knowledge_test_requires_management_access() -> None:
    session = build_mock_session()

    tenant_context = TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        organization_role=None,
        property_role=PropertyRole.VIEWER,
    )

    with pytest.raises(
        HTTPException,
    ) as error_info:
        await knowledge_routes.search_knowledge_test(
            request=KnowledgeSearchRequest(
                query="What time is checkout?",
            ),
            tenant_context=tenant_context,
            session=session,
        )

    assert error_info.value.status_code == 403


@pytest.mark.asyncio
async def test_search_knowledge_test_maps_service_validation_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = build_mock_session()
    tenant_context = build_owner_tenant_context()

    monkeypatch.setattr(
        knowledge_routes,
        "search_property_knowledge",
        AsyncMock(
            side_effect=KnowledgeSearchValidationError("Knowledge search query cannot be blank.")
        ),
    )

    with pytest.raises(
        HTTPException,
    ) as error_info:
        await knowledge_routes.search_knowledge_test(
            request=KnowledgeSearchRequest(
                query="Valid at the HTTP boundary",
            ),
            tenant_context=tenant_context,
            session=session,
        )

    assert error_info.value.status_code == 400
    assert error_info.value.detail == ("Knowledge search query cannot be blank.")

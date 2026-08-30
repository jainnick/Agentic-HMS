from __future__ import annotations

from collections.abc import (
    AsyncIterator,
    Generator,
)
from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import get_tenant_context
from app.core.database import get_db_session
from app.main import app
from app.modules.assistant import routes as assistant_routes
from app.modules.assistant.llm import (
    AssistantLlmConfigurationError,
    AssistantLlmRateLimitError,
    AssistantLlmRequestError,
    AssistantLlmResponseError,
)
from app.modules.assistant.service import (
    AssistantMessageValidationError,
    AssistantSource,
    AssistantToolTrace,
    HotelAssistantResult,
)
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import (
    OrganizationRole,
    PropertyRole,
)

ASSISTANT_CHAT_URL = "/api/v1/admin/assistant/chat-test"


@pytest.fixture
def selected_property_context() -> TenantContext:
    return TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        organization_role=(OrganizationRole.ORGANIZATION_OWNER),
        property_role=None,
    )


@pytest.fixture
def assistant_client(
    selected_property_context: TenantContext,
) -> Generator[
    tuple[TestClient, MagicMock],
    None,
    None,
]:
    session = MagicMock(
        spec=AsyncSession,
    )

    async def override_tenant_context() -> TenantContext:
        return selected_property_context

    async def override_db_session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_tenant_context] = override_tenant_context
    app.dependency_overrides[get_db_session] = override_db_session

    try:
        with TestClient(app) as client:
            yield client, session

    finally:
        app.dependency_overrides.clear()


def test_assistant_chat_returns_safe_response(
    assistant_client: tuple[TestClient, MagicMock],
    selected_property_context: TenantContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, session = assistant_client

    assistant_session_id = uuid4()

    assistant_mock = AsyncMock(
        return_value=HotelAssistantResult(
            session_id=assistant_session_id,
            answer="Checkout is at 11:00 AM.",
            sources=[
                AssistantSource(
                    document_title="Guest Policies",
                    page_number=4,
                    heading="Check-in and checkout",
                )
            ],
            tool_calls=[
                AssistantToolTrace(
                    call_id="internal-call-1",
                    name="knowledge.search",
                    returned_count=1,
                )
            ],
            model_request_ids=[
                "provider-request-1",
            ],
        )
    )

    monkeypatch.setattr(
        assistant_routes,
        "run_hotel_assistant",
        assistant_mock,
    )

    response = client.post(
        ASSISTANT_CHAT_URL,
        json={
            "message": "What time is checkout?",
        },
    )

    assert response.status_code == 200

    assert response.json() == {
        "session_id": str(
            assistant_session_id
        ),
        "answer": "Checkout is at 11:00 AM.",
        "sources": [
            {
                "document_title": "Guest Policies",
                "page_number": 4,
                "heading": "Check-in and checkout",
            }
        ],
        "tool_calls": [
            {
                "name": "knowledge.search",
                "returned_count": 1,
            }
        ],
    }

    assert (
        "model_request_ids"
        not in response.json()
    )

    assert (
        "call_id"
        not in response.json()["tool_calls"][0]
    )

    assistant_mock.assert_awaited_once()

    call_arguments = (
        assistant_mock
        .await_args
        .kwargs
    )

    assert call_arguments["message"] == (
        "What time is checkout?"
    )

    tool_context = (
        call_arguments["context"]
    )

    assert tool_context.session is session

    assert (
        tool_context.organization_id
        == selected_property_context.organization_id
    )

    assert (
        tool_context.property_id
        == selected_property_context.property_id
    )


def test_assistant_chat_requires_selected_property(
    assistant_client: tuple[TestClient, MagicMock],
) -> None:
    client, _ = assistant_client

    organization_scope_context = TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=None,
        organization_role=(OrganizationRole.ORGANIZATION_OWNER),
        property_role=None,
    )

    async def override_tenant_context() -> TenantContext:
        return organization_scope_context

    app.dependency_overrides[get_tenant_context] = override_tenant_context

    response = client.post(
        ASSISTANT_CHAT_URL,
        json={
            "message": "What time is checkout?",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": ("A property must be selected using the X-Property-ID header."),
    }


def test_assistant_chat_requires_management_access(
    assistant_client: tuple[TestClient, MagicMock],
) -> None:
    client, _ = assistant_client

    viewer_context = TenantContext(
        user_id=uuid4(),
        organization_id=uuid4(),
        property_id=uuid4(),
        organization_role=OrganizationRole.VIEWER,
        property_role=PropertyRole.VIEWER,
    )

    async def override_tenant_context() -> TenantContext:
        return viewer_context

    app.dependency_overrides[get_tenant_context] = override_tenant_context

    response = client.post(
        ASSISTANT_CHAT_URL,
        json={
            "message": "What time is checkout?",
        },
    )

    assert response.status_code == 403
    assert response.json() == {
        "detail": "Property management access is required.",
    }


def test_assistant_chat_maps_message_validation_error(
    assistant_client: tuple[TestClient, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _ = assistant_client

    monkeypatch.setattr(
        assistant_routes,
        "run_hotel_assistant",
        AsyncMock(
            side_effect=AssistantMessageValidationError(
                "Assistant message cannot be blank.",
            ),
        ),
    )

    response = client.post(
        ASSISTANT_CHAT_URL,
        json={
            "message": "   ",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "detail": "Assistant message cannot be blank.",
    }


@pytest.mark.parametrize(
    (
        "assistant_error",
        "expected_status",
        "expected_detail",
    ),
    [
        (
            AssistantLlmRateLimitError(
                "Provider rate limit reached.",
            ),
            429,
            ("The Hotel Assistant is temporarily busy. Please retry shortly."),
        ),
        (
            AssistantLlmConfigurationError(
                "LLM_API_KEY is not configured.",
            ),
            503,
            "The Hotel Assistant is not configured.",
        ),
        (
            AssistantLlmRequestError(
                "Provider connection failed.",
            ),
            502,
            ("The language-model provider could not complete the request."),
        ),
        (
            AssistantLlmResponseError(
                "Provider response was invalid.",
            ),
            502,
            ("The Hotel Assistant returned an unusable response."),
        ),
    ],
)
def test_assistant_chat_maps_llm_errors(
    assistant_client: tuple[TestClient, MagicMock],
    monkeypatch: pytest.MonkeyPatch,
    assistant_error: Exception,
    expected_status: int,
    expected_detail: str,
) -> None:
    client, _ = assistant_client

    monkeypatch.setattr(
        assistant_routes,
        "run_hotel_assistant",
        AsyncMock(
            side_effect=assistant_error,
        ),
    )

    response = client.post(
        ASSISTANT_CHAT_URL,
        json={
            "message": "What time is checkout?",
        },
    )

    assert response.status_code == expected_status
    assert response.json() == {
        "detail": expected_detail,
    }

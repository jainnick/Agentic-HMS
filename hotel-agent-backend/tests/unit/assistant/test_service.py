from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import (
    AsyncMock,
    MagicMock,
)
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.assistant import service as assistant_service
from app.modules.assistant.context import AssistantToolContext
from app.modules.assistant.llm import (
    AssistantFunctionCall,
    AssistantModelTurn,
)
from app.modules.assistant.service import (
    AssistantMessageValidationError,
    AssistantToolArgumentsError,
    AssistantToolRoundLimitError,
    run_hotel_assistant,
)
from app.modules.assistant.tools.knowledge import (
    KnowledgeSearchToolMatch,
    KnowledgeSearchToolResult,
)


def build_mock_session() -> MagicMock:
    return MagicMock(
        spec=AsyncSession,
    )


def build_context() -> AssistantToolContext:
    return AssistantToolContext(
        session=build_mock_session(),
        organization_id=uuid4(),
        property_id=uuid4(),
    )


def patch_settings(
    monkeypatch: pytest.MonkeyPatch,
    *,
    max_tool_rounds: int = 3,
) -> None:
    settings = SimpleNamespace(
        assistant_max_message_length=4_000,
        assistant_max_tool_rounds=max_tool_rounds,
    )

    monkeypatch.setattr(
        assistant_service,
        "get_settings",
        lambda: settings,
    )


@pytest.mark.asyncio
async def test_assistant_returns_direct_model_answer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    model_mock = AsyncMock(
        return_value=AssistantModelTurn(
            text="Hello! How may I help with your stay?",
            tool_calls=[],
            assistant_message={
                "role": "assistant",
                "content": ("Hello! How may I help with your stay?"),
            },
            request_id="request-1",
        )
    )

    monkeypatch.setattr(
        assistant_service,
        "generate_assistant_turn",
        model_mock,
    )

    result = await run_hotel_assistant(
        message="  Hello  ",
        context=build_context(),
    )

    assert result.answer == ("Hello! How may I help with your stay?")
    assert result.sources == []
    assert result.tool_calls == []
    assert result.model_request_ids == [
        "request-1",
    ]

    first_messages = model_mock.await_args.args[0]

    assert first_messages[1] == {
        "role": "user",
        "content": "Hello",
    }


@pytest.mark.asyncio
async def test_assistant_executes_knowledge_tool_then_answers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    first_turn = AssistantModelTurn(
        text=None,
        tool_calls=[
            AssistantFunctionCall(
                call_id="call-1",
                name="knowledge_search",
                arguments=('{"query":"What time is checkout?","match_count":5}'),
            )
        ],
        assistant_message={
            "role": "assistant",
            "tool_calls": [
                {
                    "id": "call-1",
                    "type": "function",
                    "function": {
                        "name": "knowledge_search",
                        "arguments": ('{"query":"What time is checkout?","match_count":5}'),
                    },
                }
            ],
        },
        request_id="request-1",
    )

    second_turn = AssistantModelTurn(
        text=("Checkout is at 11:00 AM, according to Guest Policies, page 4."),
        tool_calls=[],
        assistant_message={
            "role": "assistant",
            "content": ("Checkout is at 11:00 AM, according to Guest Policies, page 4."),
        },
        request_id="request-2",
    )

    model_mock = AsyncMock(
        side_effect=[
            first_turn,
            second_turn,
        ]
    )

    tool_result = KnowledgeSearchToolResult(
        query="What time is checkout?",
        returned_count=1,
        matches=[
            KnowledgeSearchToolMatch(
                document_title="Guest Policies",
                source_key="guest-policies",
                heading="Check-in and checkout",
                page_number=4,
                content="Checkout time is 11:00 AM.",
                similarity=0.82,
            )
        ],
    )

    tool_mock = AsyncMock(return_value=tool_result)

    monkeypatch.setattr(
        assistant_service,
        "generate_assistant_turn",
        model_mock,
    )

    monkeypatch.setattr(
        assistant_service,
        "execute_knowledge_search_tool",
        tool_mock,
    )

    context = build_context()

    result = await run_hotel_assistant(
        message="What time is checkout?",
        context=context,
    )

    assert model_mock.await_count == 2
    assert tool_mock.await_count == 1

    assert result.answer.startswith("Checkout is at 11:00 AM")

    assert len(result.sources) == 1
    assert result.sources[0].document_title == ("Guest Policies")
    assert result.sources[0].page_number == 4

    assert len(result.tool_calls) == 1
    assert result.tool_calls[0].name == ("knowledge.search")
    assert result.tool_calls[0].returned_count == 1

    second_call_messages = model_mock.await_args_list[1].args[0]

    tool_messages = [message for message in second_call_messages if message.get("role") == "tool"]

    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == ("call-1")


@pytest.mark.asyncio
async def test_assistant_rejects_invalid_tool_arguments(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    monkeypatch.setattr(
        assistant_service,
        "generate_assistant_turn",
        AsyncMock(
            return_value=AssistantModelTurn(
                text=None,
                tool_calls=[
                    AssistantFunctionCall(
                        call_id="call-1",
                        name="knowledge_search",
                        arguments='{"match_count":500}',
                    )
                ],
                assistant_message={
                    "role": "assistant",
                },
                request_id=None,
            )
        ),
    )

    with pytest.raises(
        AssistantToolArgumentsError,
    ):
        await run_hotel_assistant(
            message="What time is checkout?",
            context=build_context(),
        )


@pytest.mark.asyncio
async def test_assistant_rejects_blank_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(monkeypatch)

    model_mock = AsyncMock()

    monkeypatch.setattr(
        assistant_service,
        "generate_assistant_turn",
        model_mock,
    )

    with pytest.raises(
        AssistantMessageValidationError,
    ):
        await run_hotel_assistant(
            message="  \n\t ",
            context=build_context(),
        )

    model_mock.assert_not_awaited()


@pytest.mark.asyncio
async def test_assistant_enforces_tool_round_limit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    patch_settings(
        monkeypatch,
        max_tool_rounds=1,
    )

    repeated_tool_turn = AssistantModelTurn(
        text=None,
        tool_calls=[
            AssistantFunctionCall(
                call_id="call-1",
                name="knowledge_search",
                arguments='{"query":"Checkout time?"}',
            )
        ],
        assistant_message={
            "role": "assistant",
        },
        request_id=None,
    )

    monkeypatch.setattr(
        assistant_service,
        "generate_assistant_turn",
        AsyncMock(
            side_effect=[
                repeated_tool_turn,
                repeated_tool_turn,
            ]
        ),
    )

    monkeypatch.setattr(
        assistant_service,
        "execute_knowledge_search_tool",
        AsyncMock(
            return_value=KnowledgeSearchToolResult(
                query="Checkout time?",
                returned_count=0,
                matches=[],
            )
        ),
    )

    with pytest.raises(
        AssistantToolRoundLimitError,
    ):
        await run_hotel_assistant(
            message="What time is checkout?",
            context=build_context(),
        )

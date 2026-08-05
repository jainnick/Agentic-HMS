from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import get_settings
from app.modules.assistant.context import AssistantToolContext
from app.modules.assistant.llm import (
    AssistantFunctionCall,
    AssistantMessage,
    AssistantModelTurn,
    generate_assistant_turn,
)
from app.modules.assistant.prompts import (
    HOTEL_ASSISTANT_INSTRUCTIONS,
)
from app.modules.assistant.tools.knowledge import (
    KNOWLEDGE_SEARCH_TOOL_LABEL,
    KNOWLEDGE_SEARCH_TOOL_NAME,
    KnowledgeSearchToolInput,
    KnowledgeSearchToolResult,
    execute_knowledge_search_tool,
)


class AssistantServiceError(Exception):
    """Base error raised by the Hotel Assistant service."""


class AssistantMessageValidationError(AssistantServiceError):
    """Raised when the supplied guest message is invalid."""


class AssistantUnsupportedToolError(AssistantServiceError):
    """Raised when the model requests a tool that is not available."""


class AssistantToolArgumentsError(AssistantServiceError):
    """Raised when model-generated tool arguments are invalid."""


class AssistantToolRoundLimitError(AssistantServiceError):
    """Raised when the model exceeds the permitted tool-call rounds."""


class AssistantEmptyResponseError(AssistantServiceError):
    """Raised when the model returns neither text nor a tool call."""


@dataclass(frozen=True, slots=True)
class AssistantSource:
    """One hotel document source associated with the assistant answer."""

    document_title: str
    page_number: int | None
    heading: str | None


@dataclass(frozen=True, slots=True)
class AssistantToolTrace:
    """Summary of one successfully executed assistant tool call."""

    call_id: str
    name: str
    returned_count: int


@dataclass(frozen=True, slots=True)
class HotelAssistantResult:
    """Final result returned by the Hotel Assistant orchestration."""

    answer: str
    sources: list[AssistantSource]
    tool_calls: list[AssistantToolTrace]
    model_request_ids: list[str]


def normalize_assistant_message(
    message: str,
    *,
    max_length: int,
) -> str:
    """Normalize and validate one guest message."""

    normalized_message = " ".join(message.split()).strip()

    if not normalized_message:
        raise AssistantMessageValidationError("Assistant message cannot be blank.")

    if len(normalized_message) > max_length:
        raise AssistantMessageValidationError(
            f"Assistant message cannot exceed {max_length} characters."
        )

    return normalized_message


def collect_knowledge_sources(
    result: KnowledgeSearchToolResult,
    *,
    existing_sources: list[AssistantSource],
) -> list[AssistantSource]:
    """
    Add unique document/page sources from a knowledge tool result.

    This records candidate sources supplied to the model. A later citation
    layer can track which exact passages were used in the final sentence.
    """

    source_keys = {
        (
            source.document_title,
            source.page_number,
            source.heading,
        )
        for source in existing_sources
    }

    collected_sources = list(existing_sources)

    for match in result.matches:
        source_key = (
            match.document_title,
            match.page_number,
            match.heading,
        )

        if source_key in source_keys:
            continue

        collected_sources.append(
            AssistantSource(
                document_title=match.document_title,
                page_number=match.page_number,
                heading=match.heading,
            )
        )

        source_keys.add(source_key)

    return collected_sources


async def execute_requested_tool(
    tool_call: AssistantFunctionCall,
    *,
    context: AssistantToolContext,
) -> KnowledgeSearchToolResult:
    """Validate and execute one model-requested assistant tool."""

    if tool_call.name != KNOWLEDGE_SEARCH_TOOL_NAME:
        raise AssistantUnsupportedToolError(f"Unsupported assistant tool: {tool_call.name}.")

    try:
        tool_input = KnowledgeSearchToolInput.model_validate_json(tool_call.arguments)

    except ValidationError as exc:
        raise AssistantToolArgumentsError(
            "The language model generated invalid knowledge-search arguments."
        ) from exc

    return await execute_knowledge_search_tool(
        tool_input,
        context=context,
    )


async def run_hotel_assistant(
    *,
    message: str,
    context: AssistantToolContext,
) -> HotelAssistantResult:
    """
    Run one Hotel Assistant request through a bounded tool-calling loop.

    Each iteration asks the model either to:
    - produce a final text response; or
    - request the knowledge_search tool.

    Tool outputs are appended to the conversation and sent back to the model.
    """

    settings = get_settings()

    normalized_message = normalize_assistant_message(
        message,
        max_length=(settings.assistant_max_message_length),
    )

    messages: list[AssistantMessage] = [
        {
            "role": "system",
            "content": HOTEL_ASSISTANT_INSTRUCTIONS,
        },
        {
            "role": "user",
            "content": normalized_message,
        },
    ]

    sources: list[AssistantSource] = []
    tool_traces: list[AssistantToolTrace] = []
    model_request_ids: list[str] = []

    completed_tool_rounds = 0

    while True:
        model_turn: AssistantModelTurn = await generate_assistant_turn(messages)

        if model_turn.request_id is not None:
            model_request_ids.append(model_turn.request_id)

        messages.append(model_turn.assistant_message)

        if not model_turn.tool_calls:
            if model_turn.text is None:
                raise AssistantEmptyResponseError(
                    "The language model returned neither a final answer nor a tool call."
                )

            return HotelAssistantResult(
                answer=model_turn.text,
                sources=sources,
                tool_calls=tool_traces,
                model_request_ids=model_request_ids,
            )

        if completed_tool_rounds >= settings.assistant_max_tool_rounds:
            raise AssistantToolRoundLimitError(
                "The assistant exceeded the maximum number of tool-call rounds."
            )

        completed_tool_rounds += 1

        for tool_call in model_turn.tool_calls:
            tool_result = await execute_requested_tool(
                tool_call,
                context=context,
            )

            sources = collect_knowledge_sources(
                tool_result,
                existing_sources=sources,
            )

            tool_traces.append(
                AssistantToolTrace(
                    call_id=tool_call.call_id,
                    name=KNOWLEDGE_SEARCH_TOOL_LABEL,
                    returned_count=(tool_result.returned_count),
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.call_id,
                    "content": (tool_result.model_dump_json()),
                }
            )

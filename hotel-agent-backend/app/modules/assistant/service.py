from __future__ import annotations

from dataclasses import dataclass

from pydantic import ValidationError

from app.core.config import get_settings
from app.modules.assistant.context import (
    AssistantToolContext,
)
from app.modules.assistant.llm import (
    AssistantFunctionCall,
    AssistantMessage,
    AssistantModelTurn,
    build_assistant_tool_definitions,
    generate_assistant_turn,
)
from app.modules.assistant.prompts import (
    HOTEL_ASSISTANT_INSTRUCTIONS,
)
from app.modules.assistant.tools.knowledge import (
    KNOWLEDGE_SEARCH_TOOL_LABEL,
    KnowledgeSearchToolInput,
    KnowledgeSearchToolResult,
    execute_knowledge_search_tool,
)
from app.modules.assistant.tools.rooms import (
    ROOM_AVAILABILITY_TOOL_LABEL,
    RoomAvailabilityToolInput,
    RoomAvailabilityToolResult,
    execute_room_availability_tool,
)
from app.modules.property_tools import (
    PropertyToolName,
    list_property_tools,
)
from app.modules.rooms import (
    RoomValidationError,
)


class AssistantServiceError(Exception):
    """Base Hotel Assistant service error."""


class AssistantMessageValidationError(AssistantServiceError):
    """Invalid guest message."""


class AssistantUnsupportedToolError(AssistantServiceError):
    """Model requested an unavailable tool."""


class AssistantToolArgumentsError(AssistantServiceError):
    """Model produced invalid tool arguments."""


class AssistantToolRoundLimitError(AssistantServiceError):
    """Maximum tool rounds exceeded."""


class AssistantEmptyResponseError(AssistantServiceError):
    """Model returned no usable response."""


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantSource:
    """One knowledge source used by assistant."""

    document_title: str
    page_number: int | None
    heading: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantToolTrace:
    """Safe summary of a tool execution."""

    call_id: str
    name: str
    returned_count: int


@dataclass(
    frozen=True,
    slots=True,
)
class HotelAssistantResult:
    """Final assistant result."""

    answer: str

    sources: list[AssistantSource]

    tool_calls: list[AssistantToolTrace]

    model_request_ids: list[str]


def normalize_assistant_message(
    message: str,
    *,
    max_length: int,
) -> str:
    """Normalize and validate guest input."""

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
    Add unique knowledge document/page sources.
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
                document_title=(match.document_title),
                page_number=(match.page_number),
                heading=match.heading,
            )
        )

        source_keys.add(source_key)

    return collected_sources


async def get_enabled_assistant_tools(
    context: AssistantToolContext,
) -> set[PropertyToolName]:
    """
    Resolve effective PR4 capabilities once per
    assistant request.
    """

    property_tools = await list_property_tools(
        context.session,
        property_id=context.property_id,
    )

    return {property_tool.tool_name for property_tool in property_tools if property_tool.enabled}


async def execute_requested_tool(
    tool_call: AssistantFunctionCall,
    *,
    context: AssistantToolContext,
    enabled_tools: set[PropertyToolName],
) -> KnowledgeSearchToolResult | RoomAvailabilityToolResult:
    """
    Validate and execute one requested tool.

    Model-generated arguments are untrusted.
    Tenant context comes from the backend.
    """

    try:
        property_tool = PropertyToolName(tool_call.name)

    except ValueError as exc:
        raise AssistantUnsupportedToolError(
            f"Unsupported assistant tool: {tool_call.name}."
        ) from exc

    if property_tool not in enabled_tools:
        raise AssistantUnsupportedToolError(
            "The requested assistant tool is disabled for this property."
        )

    if property_tool == PropertyToolName.KNOWLEDGE_SEARCH:
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

    if property_tool == PropertyToolName.ROOM_AVAILABILITY:
        try:
            room_input = RoomAvailabilityToolInput.model_validate_json(tool_call.arguments)

        except ValidationError as exc:
            raise AssistantToolArgumentsError(
                "The language model generated invalid room-availability arguments."
            ) from exc

        try:
            return await execute_room_availability_tool(
                room_input,
                context=context,
            )

        except RoomValidationError as exc:
            raise AssistantToolArgumentsError(str(exc)) from exc

    raise AssistantUnsupportedToolError(f"Unsupported assistant tool: {tool_call.name}.")


def get_tool_trace_details(
    result: (KnowledgeSearchToolResult | RoomAvailabilityToolResult),
) -> tuple[str, int]:
    """
    Map different tool results to the existing
    generic trace structure.
    """

    if isinstance(
        result,
        KnowledgeSearchToolResult,
    ):
        return (
            KNOWLEDGE_SEARCH_TOOL_LABEL,
            result.returned_count,
        )

    return (
        ROOM_AVAILABILITY_TOOL_LABEL,
        len(result.options),
    )


async def run_hotel_assistant(
    *,
    message: str,
    context: AssistantToolContext,
) -> HotelAssistantResult:
    """
    Run one property-aware bounded tool loop.

    Flow:

        user
        -> enabled property capabilities
        -> LLM
        -> tool
        -> backend service
        -> tool result
        -> LLM
        -> final answer
    """

    settings = get_settings()

    normalized_message = normalize_assistant_message(
        message,
        max_length=(settings.assistant_max_message_length),
    )

    enabled_tools = await get_enabled_assistant_tools(context)

    tool_definitions = build_assistant_tool_definitions(enabled_tools)

    messages: list[AssistantMessage] = [
        {
            "role": "system",
            "content": (HOTEL_ASSISTANT_INSTRUCTIONS),
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
        model_turn: AssistantModelTurn = await generate_assistant_turn(
            messages,
            tool_definitions=(tool_definitions),
        )

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
                model_request_ids=(model_request_ids),
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
                enabled_tools=(enabled_tools),
            )

            if isinstance(
                tool_result,
                KnowledgeSearchToolResult,
            ):
                sources = collect_knowledge_sources(
                    tool_result,
                    existing_sources=(sources),
                )

            (
                tool_label,
                returned_count,
            ) = get_tool_trace_details(tool_result)

            tool_traces.append(
                AssistantToolTrace(
                    call_id=(tool_call.call_id),
                    name=tool_label,
                    returned_count=(returned_count),
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": (tool_call.call_id),
                    "content": (tool_result.model_dump_json()),
                }
            )

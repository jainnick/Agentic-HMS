from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    ValidationError,
)

from app.core.config import (
    get_settings,
)
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
from app.modules.assistant.sessions import (
    AssistantSession,
    get_conversation_history,
    get_or_create_assistant_session,
    save_conversation_turn,
)
from app.modules.assistant.tools.knowledge import (
    KNOWLEDGE_SEARCH_TOOL_LABEL,
    KnowledgeSearchToolInput,
    KnowledgeSearchToolResult,
    execute_knowledge_search_tool,
)
from app.modules.assistant.tools.rooms import (
    ROOM_AVAILABILITY_TOOL_LABEL,
    ROOM_BOOKING_TOOL_LABEL,
    RoomAvailabilityToolInput,
    RoomAvailabilityToolResult,
    RoomBookingToolInput,
    RoomBookingToolResult,
    execute_room_availability_tool,
    execute_room_booking_tool,
)
from app.modules.property_tools import (
    PropertyToolName,
    list_property_tools,
)
from app.modules.rooms import (
    RoomValidationError,
)


class AssistantServiceError(Exception):
    """Base Hotel Assistant error."""


class AssistantMessageValidationError(
    AssistantServiceError
):
    """Guest message is invalid."""


class AssistantUnsupportedToolError(
    AssistantServiceError
):
    """Model requested unavailable tool."""


class AssistantToolArgumentsError(
    AssistantServiceError
):
    """Model produced invalid arguments."""


class AssistantToolRoundLimitError(
    AssistantServiceError
):
    """Tool loop exceeded configured limit."""


class AssistantEmptyResponseError(
    AssistantServiceError
):
    """Model returned no useful output."""


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantSource:
    document_title: str
    page_number: int | None
    heading: str | None


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantToolTrace:
    call_id: str
    name: str
    returned_count: int


@dataclass(
    frozen=True,
    slots=True,
)
class HotelAssistantResult:
    session_id: UUID

    answer: str

    sources: list[
        AssistantSource
    ]

    tool_calls: list[
        AssistantToolTrace
    ]

    model_request_ids: list[
        str
    ]


class AssistantToolErrorResult(BaseModel):
    """
    Recoverable tool-input issue.

    These are returned to the LLM rather than becoming
    an HTTP 502 response.
    """

    error: str

    missing_fields: list[
        str
    ] = Field(
        default_factory=list,
    )


def normalize_assistant_message(
    message: str,
    *,
    max_length: int,
) -> str:
    normalized_message = " ".join(
        message.split()
    ).strip()

    if not normalized_message:
        raise AssistantMessageValidationError(
            "Assistant message cannot be blank."
        )

    if (
        len(normalized_message)
        > max_length
    ):
        raise AssistantMessageValidationError(
            "Assistant message cannot exceed "
            f"{max_length} characters."
        )

    return normalized_message


def collect_knowledge_sources(
    result: KnowledgeSearchToolResult,
    *,
    existing_sources: list[
        AssistantSource
    ],
) -> list[AssistantSource]:
    source_keys = {
        (
            source.document_title,
            source.page_number,
            source.heading,
        )
        for source
        in existing_sources
    }

    collected_sources = list(
        existing_sources
    )

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
                document_title=(
                    match.document_title
                ),
                page_number=(
                    match.page_number
                ),
                heading=(
                    match.heading
                ),
            )
        )

        source_keys.add(
            source_key
        )

    return collected_sources


async def get_enabled_assistant_tools(
    context: AssistantToolContext,
) -> set[PropertyToolName]:
    """
    Resolve PR4 property capabilities once.
    """

    property_tools = (
        await list_property_tools(
            context.session,
            property_id=(
                context.property_id
            ),
        )
    )

    return {
        property_tool.tool_name
        for property_tool
        in property_tools
        if property_tool.enabled
    }


async def execute_requested_tool(
    tool_call: AssistantFunctionCall,
    *,
    context: AssistantToolContext,
    enabled_tools: set[
        PropertyToolName
    ],
    assistant_session: AssistantSession,
    user_message: str,
) -> (
    KnowledgeSearchToolResult
    | RoomAvailabilityToolResult
    | RoomBookingToolResult
    | AssistantToolErrorResult
):
    """
    Validate and execute one requested tool.

    Model-generated arguments are untrusted.

    organization/property/session state comes from
    trusted backend context.
    """

    try:
        property_tool = (
            PropertyToolName(
                tool_call.name
            )
        )

    except ValueError as exc:
        raise AssistantUnsupportedToolError(
            "Unsupported assistant tool: "
            f"{tool_call.name}."
        ) from exc

    if (
        property_tool
        not in enabled_tools
    ):
        raise AssistantUnsupportedToolError(
            "The requested assistant tool "
            "is disabled for this property."
        )

    # ------------------------------------------------------------
    # Knowledge
    # ------------------------------------------------------------

    if (
        property_tool
        == PropertyToolName.KNOWLEDGE_SEARCH
    ):
        try:
            tool_input = (
                KnowledgeSearchToolInput
                .model_validate_json(
                    tool_call.arguments
                )
            )

        except ValidationError as exc:
            raise AssistantToolArgumentsError(
                "The language model generated "
                "invalid knowledge-search arguments."
            ) from exc

        return (
            await execute_knowledge_search_tool(
                tool_input,
                context=context,
            )
        )

    # ------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------

    if (
        property_tool
        == PropertyToolName.ROOM_AVAILABILITY
    ):
        try:
            room_input = (
                RoomAvailabilityToolInput
                .model_validate_json(
                    tool_call.arguments
                )
            )

        except ValidationError as exc:
            missing_fields = [
                str(
                    error["loc"][-1]
                )
                for error
                in exc.errors()
                if (
                    error["type"]
                    == "missing"
                )
            ]

            return AssistantToolErrorResult(
                error=(
                    "Room availability is missing "
                    "required information. Ask the "
                    "guest for the missing values "
                    "and do not guess them."
                ),
                missing_fields=(
                    missing_fields
                ),
            )

        try:
            return (
                await execute_room_availability_tool(
                    room_input,
                    context=context,
                )
            )

        except RoomValidationError as exc:
            return AssistantToolErrorResult(
                error=str(exc)
            )

    # ------------------------------------------------------------
    # Booking
    # ------------------------------------------------------------

    if (
        property_tool
        == PropertyToolName.ROOM_BOOKING
    ):
        try:
            booking_input = (
                RoomBookingToolInput
                .model_validate_json(
                    tool_call.arguments
                )
            )

        except ValidationError:
            return AssistantToolErrorResult(
                error=(
                    "The booking request contains "
                    "invalid information. Ask the "
                    "guest to provide or correct "
                    "the required details."
                )
            )

        try:
            return (
                await execute_room_booking_tool(
                    booking_input,
                    context=context,
                    assistant_session=(
                        assistant_session
                    ),
                    user_message=(
                        user_message
                    ),
                )
            )

        except RoomValidationError as exc:
            return AssistantToolErrorResult(
                error=str(exc)
            )

    raise AssistantUnsupportedToolError(
        "Unsupported assistant tool: "
        f"{tool_call.name}."
    )


def get_tool_trace_details(
    result: (
        KnowledgeSearchToolResult
        | RoomAvailabilityToolResult
        | RoomBookingToolResult
        | AssistantToolErrorResult
    ),
) -> tuple[str, int]:
    """
    Convert different tool responses into the existing
    generic debug trace.
    """

    if isinstance(
        result,
        KnowledgeSearchToolResult,
    ):
        return (
            KNOWLEDGE_SEARCH_TOOL_LABEL,
            result.returned_count,
        )

    if isinstance(
        result,
        RoomAvailabilityToolResult,
    ):
        return (
            ROOM_AVAILABILITY_TOOL_LABEL,
            len(result.options),
        )

    if isinstance(
        result,
        RoomBookingToolResult,
    ):
        return (
            ROOM_BOOKING_TOOL_LABEL,
            (
                1
                if result.status
                == "confirmed"
                else 0
            ),
        )

    return (
        "tool.validation",
        0,
    )


async def run_hotel_assistant(
    *,
    message: str,
    context: AssistantToolContext,
    session_id: UUID | None = None,
) -> HotelAssistantResult:
    """
    Run one stateful property-specific assistant turn.

    Flow:

    incoming session ID
        -> load conversation
        -> append current user message
        -> LLM
        -> tool(s)
        -> LLM
        -> save final user/assistant turn
    """

    settings = get_settings()

    normalized_message = (
        normalize_assistant_message(
            message,
            max_length=(
                settings
                .assistant_max_message_length
            ),
        )
    )

    assistant_session = (
        await get_or_create_assistant_session(
            context.session,
            organization_id=(
                context.organization_id
            ),
            property_id=(
                context.property_id
            ),
            session_id=session_id,
        )
    )

    enabled_tools = (
        await get_enabled_assistant_tools(
            context
        )
    )

    tool_definitions = (
        build_assistant_tool_definitions(
            enabled_tools
        )
    )

    history = (
        get_conversation_history(
            assistant_session
        )
    )

    messages: list[
        AssistantMessage
    ] = [
        {
            "role": "system",
            "content": (
                HOTEL_ASSISTANT_INSTRUCTIONS
            ),
        },
        *history,
        {
            "role": "user",
            "content": (
                normalized_message
            ),
        },
    ]

    sources: list[
        AssistantSource
    ] = []

    tool_traces: list[
        AssistantToolTrace
    ] = []

    model_request_ids: list[
        str
    ] = []

    completed_tool_rounds = 0

    while True:
        model_turn: AssistantModelTurn = (
            await generate_assistant_turn(
                messages,
                tool_definitions=(
                    tool_definitions
                ),
            )
        )

        if (
            model_turn.request_id
            is not None
        ):
            model_request_ids.append(
                model_turn.request_id
            )

        messages.append(
            model_turn.assistant_message
        )

        # --------------------------------------------------------
        # Final natural-language answer
        # --------------------------------------------------------

        if not model_turn.tool_calls:
            if model_turn.text is None:
                raise AssistantEmptyResponseError(
                    "The language model returned "
                    "neither a final answer nor "
                    "a tool call."
                )

            await save_conversation_turn(
                context.session,
                assistant_session=(
                    assistant_session
                ),
                user_message=(
                    normalized_message
                ),
                assistant_message=(
                    model_turn.text
                ),
            )

            return HotelAssistantResult(
                session_id=(
                    assistant_session.id
                ),
                answer=(
                    model_turn.text
                ),
                sources=sources,
                tool_calls=(
                    tool_traces
                ),
                model_request_ids=(
                    model_request_ids
                ),
            )

        # --------------------------------------------------------
        # Bounded tool loop
        # --------------------------------------------------------

        if (
            completed_tool_rounds
            >= settings
            .assistant_max_tool_rounds
        ):
            raise AssistantToolRoundLimitError(
                "The assistant exceeded the "
                "maximum number of tool-call "
                "rounds."
            )

        completed_tool_rounds += 1

        for tool_call in (
            model_turn.tool_calls
        ):
            tool_result = (
                await execute_requested_tool(
                    tool_call,
                    context=context,
                    enabled_tools=(
                        enabled_tools
                    ),
                    assistant_session=(
                        assistant_session
                    ),
                    user_message=(
                        normalized_message
                    ),
                )
            )

            if isinstance(
                tool_result,
                KnowledgeSearchToolResult,
            ):
                sources = (
                    collect_knowledge_sources(
                        tool_result,
                        existing_sources=(
                            sources
                        ),
                    )
                )

            (
                tool_label,
                returned_count,
            ) = get_tool_trace_details(
                tool_result
            )

            tool_traces.append(
                AssistantToolTrace(
                    call_id=(
                        tool_call.call_id
                    ),
                    name=tool_label,
                    returned_count=(
                        returned_count
                    ),
                )
            )

            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": (
                        tool_call.call_id
                    ),
                    "content": (
                        tool_result
                        .model_dump_json()
                    ),
                }
            )
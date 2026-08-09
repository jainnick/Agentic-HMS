from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from typing import Any, cast

import openai
import structlog
from openai import AsyncOpenAI
from openai.types.chat import (
    ChatCompletionMessageFunctionToolCall,
)
from pydantic import BaseModel

from app.core.config import get_settings
from app.modules.assistant.tools.knowledge import (
    KNOWLEDGE_SEARCH_TOOL_NAME,
    KnowledgeSearchToolInput,
)
from app.modules.assistant.tools.rooms import (
    ROOM_AVAILABILITY_TOOL_NAME,
    ROOM_BOOKING_TOOL_NAME,
    RoomAvailabilityToolInput,
    RoomBookingToolInput,
)
from app.modules.property_tools import (
    PropertyToolName,
)


logger = structlog.get_logger(
    __name__
)


AssistantMessage = dict[
    str,
    Any,
]


class AssistantLlmError(Exception):
    """Base assistant LLM error."""


class AssistantLlmConfigurationError(
    AssistantLlmError
):
    """LLM is not configured."""


class AssistantLlmRequestError(
    AssistantLlmError
):
    """LLM request failed."""


class AssistantLlmRateLimitError(
    AssistantLlmRequestError
):
    """LLM provider rate limit."""


class AssistantLlmResponseError(
    AssistantLlmError
):
    """LLM returned an unusable response."""


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantFunctionCall:
    """
    One function call requested by the LLM.
    """

    call_id: str
    name: str
    arguments: str


@dataclass(
    frozen=True,
    slots=True,
)
class AssistantModelTurn:
    """
    Provider-neutral result of one LLM call.
    """

    text: str | None

    tool_calls: list[
        AssistantFunctionCall
    ]

    assistant_message: (
        AssistantMessage
    )

    request_id: str | None


def build_function_tool_definition(
    *,
    name: str,
    description: str,
    input_model: type[BaseModel],
) -> dict[str, Any]:
    """
    Generic OpenAI-compatible function definition.

    Pydantic remains the schema source of truth.
    """

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": (
                input_model
                .model_json_schema()
            ),
            "strict": False,
        },
    }


def build_knowledge_search_tool_definition(
) -> dict[str, Any]:
    return build_function_tool_definition(
        name=(
            KNOWLEDGE_SEARCH_TOOL_NAME
        ),
        description=(
            "Search this hotel's active knowledge "
            "documents for property-specific "
            "policies, facilities, services, "
            "dining, events, check-in, checkout, "
            "cancellations, pets, parking, and "
            "other guest information. Use only "
            "information relevant to the guest's "
            "actual question."
        ),
        input_model=(
            KnowledgeSearchToolInput
        ),
    )


def build_room_availability_tool_definition(
) -> dict[str, Any]:
    return build_function_tool_definition(
        name=(
            ROOM_AVAILABILITY_TOOL_NAME
        ),
        description=(
            "Check live room availability and "
            "current rates for specified check-in "
            "and check-out dates. Both dates are "
            "required. If either date is missing, "
            "ask the guest instead of guessing. "
            "Use this for available-room questions, "
            "specific or partial room names, guest "
            "capacity, inventory and current rates."
        ),
        input_model=(
            RoomAvailabilityToolInput
        ),
    )


def build_room_booking_tool_definition(
) -> dict[str, Any]:
    return build_function_tool_definition(
        name=ROOM_BOOKING_TOOL_NAME,
        description=(
            "Prepare or confirm a room booking. "
            "Use confirm=false after all required "
            "booking details are known; this "
            "prepares a quote but does not create "
            "the reservation. After the guest "
            "explicitly confirms that quote in a "
            "later message, call with confirm=true. "
            "When confirm=true, do not regenerate "
            "or repeat booking details because the "
            "backend already stores the pending "
            "booking."
        ),
        input_model=(
            RoomBookingToolInput
        ),
    )


def build_assistant_tool_definitions(
    enabled_tools: set[
        PropertyToolName
    ],
) -> list[dict[str, Any]]:
    """
    Expose only capabilities enabled for this property.
    """

    definitions: list[
        dict[str, Any]
    ] = []

    if (
        PropertyToolName.KNOWLEDGE_SEARCH
        in enabled_tools
    ):
        definitions.append(
            build_knowledge_search_tool_definition()
        )

    if (
        PropertyToolName.ROOM_AVAILABILITY
        in enabled_tools
    ):
        definitions.append(
            build_room_availability_tool_definition()
        )

    if (
        PropertyToolName.ROOM_BOOKING
        in enabled_tools
    ):
        definitions.append(
            build_room_booking_tool_definition()
        )

    return definitions


@lru_cache(maxsize=1)
def get_llm_client() -> AsyncOpenAI:
    """
    Create and cache the OpenAI-compatible client.
    """

    settings = get_settings()

    if settings.llm_api_key is None:
        raise AssistantLlmConfigurationError(
            "LLM_API_KEY is not configured."
        )

    if (
        settings.llm_model is None
        or not settings.llm_model.strip()
    ):
        raise AssistantLlmConfigurationError(
            "LLM_MODEL is not configured."
        )

    client_options: dict[
        str,
        Any,
    ] = {
        "api_key": (
            settings.llm_api_key
            .get_secret_value()
        ),
        "timeout": (
            settings
            .llm_timeout_seconds
        ),
    }

    if (
        settings.llm_base_url
        is not None
        and settings.llm_base_url.strip()
    ):
        client_options["base_url"] = (
            settings
            .llm_base_url
            .strip()
        )

    return AsyncOpenAI(
        **client_options
    )


def build_assistant_message(
    *,
    content: str | None,
    tool_calls: list[
        AssistantFunctionCall
    ],
) -> AssistantMessage:
    """
    Rebuild provider-compatible assistant message.
    """

    assistant_message: (
        AssistantMessage
    ) = {
        "role": "assistant",
    }

    if content is not None:
        assistant_message[
            "content"
        ] = content

    if tool_calls:
        assistant_message[
            "tool_calls"
        ] = [
            {
                "id": (
                    tool_call.call_id
                ),
                "type": "function",
                "function": {
                    "name": (
                        tool_call.name
                    ),
                    "arguments": (
                        tool_call.arguments
                    ),
                },
            }
            for tool_call
            in tool_calls
        ]

    return assistant_message


async def generate_assistant_turn(
    messages: list[
        AssistantMessage
    ],
    *,
    tool_definitions: list[
        dict[str, Any]
    ],
) -> AssistantModelTurn:
    """
    Send one turn to the configured LLM.

    Groq validates generated function calls before
    returning them to us. Occasionally a model may
    generate malformed tool-call syntax even though
    the intended tool arguments are correct.

    For Groq's specific `tool_use_failed` 400 error,
    retry the model generation once.

    We do NOT retry arbitrary 400 responses.
    """

    settings = get_settings()

    if (
        settings.llm_model is None
        or not settings.llm_model.strip()
    ):
        raise AssistantLlmConfigurationError(
            "LLM_MODEL is not configured."
        )

    client = get_llm_client()

    request_options: dict[
        str,
        Any,
    ] = {
        "model": (
            settings
            .llm_model
            .strip()
        ),
        "messages": cast(
            Any,
            messages,
        ),
        "max_completion_tokens": (
            settings
            .llm_max_output_tokens
        ),

        # Hotel operations benefit from deterministic
        # structured tool generation rather than
        # creative sampling.
        "temperature": 0,
    }

    if tool_definitions:
        request_options[
            "tools"
        ] = cast(
            Any,
            tool_definitions,
        )

        request_options[
            "tool_choice"
        ] = "auto"

    completion = None

    # One normal attempt + one targeted retry.
    for attempt in range(2):
        try:
            completion = (
                await client
                .chat
                .completions
                .create(
                    **request_options
                )
            )

            break

        except openai.APITimeoutError as exc:
            logger.warning(
                "assistant_llm_timeout",
                model=settings.llm_model,
            )

            raise AssistantLlmRequestError(
                "The language-model request "
                "timed out."
            ) from exc

        except openai.APIConnectionError as exc:
            logger.warning(
                "assistant_llm_connection_error",
                model=settings.llm_model,
                error_type=(
                    type(exc).__name__
                ),
            )

            raise AssistantLlmRequestError(
                "The language-model provider "
                "could not be reached."
            ) from exc

        except openai.RateLimitError as exc:
            raise AssistantLlmRateLimitError(
                "The Hotel Assistant is "
                "temporarily busy. "
                "Please retry shortly."
            ) from exc

        except openai.BadRequestError as exc:
            error_body = (
                exc.body
                if isinstance(
                    exc.body,
                    dict,
                )
                else {}
            )

            error_details = (
                error_body.get(
                    "error",
                    {}
                )
                if isinstance(
                    error_body,
                    dict,
                )
                else {}
            )

            error_code = (
                error_details.get(
                    "code"
                )
                if isinstance(
                    error_details,
                    dict,
                )
                else None
            )

            # Groq validates generated tool calls.
            #
            # A tool_use_failed response means the
            # model intended to call a tool but did
            # not produce provider-valid tool syntax.
            #
            # Retry exactly once because another
            # deterministic generation commonly
            # resolves this model-formatting failure.
            if (
                error_code
                == "tool_use_failed"
                and attempt == 0
            ):
                logger.warning(
                    "assistant_llm_tool_use_retry",
                    model=(
                        settings.llm_model
                    ),
                    request_id=getattr(
                        exc,
                        "request_id",
                        None,
                    ),
                )

                continue

            logger.warning(
                "assistant_llm_bad_request",
                status_code=(
                    exc.status_code
                ),
                request_id=getattr(
                    exc,
                    "request_id",
                    None,
                ),
                error_code=error_code,
                model=(
                    settings.llm_model
                ),
            )

            raise AssistantLlmRequestError(
                "The language-model provider "
                "rejected the request."
            ) from exc

        except openai.APIStatusError as exc:
            logger.warning(
                "assistant_llm_status_error",
                status_code=(
                    exc.status_code
                ),
                request_id=getattr(
                    exc,
                    "request_id",
                    None,
                ),
                model=(
                    settings.llm_model
                ),
            )

            raise AssistantLlmRequestError(
                "The language-model provider "
                "rejected the request."
            ) from exc

        except openai.OpenAIError as exc:
            raise AssistantLlmRequestError(
                "The language-model request "
                "failed."
            ) from exc

    if completion is None:
        raise AssistantLlmRequestError(
            "The language-model provider "
            "could not generate a valid tool call."
        )

    if not completion.choices:
        raise AssistantLlmResponseError(
            "The language model returned "
            "no completion choices."
        )

    message = (
        completion
        .choices[0]
        .message
    )

    text: str | None = None

    if message.content is not None:
        normalized_text = (
            message
            .content
            .strip()
        )

        if normalized_text:
            text = normalized_text

    normalized_tool_calls: list[
        AssistantFunctionCall
    ] = []

    for tool_call in (
        message.tool_calls or []
    ):
        if not isinstance(
            tool_call,
            ChatCompletionMessageFunctionToolCall,
        ):
            raise AssistantLlmResponseError(
                "The language model returned "
                "an unsupported custom tool call."
            )

        normalized_tool_calls.append(
            AssistantFunctionCall(
                call_id=(
                    tool_call.id
                ),
                name=(
                    tool_call
                    .function
                    .name
                ),
                arguments=(
                    tool_call
                    .function
                    .arguments
                ),
            )
        )

    assistant_message = (
        build_assistant_message(
            content=message.content,
            tool_calls=(
                normalized_tool_calls
            ),
        )
    )

    request_id_value = getattr(
        completion,
        "_request_id",
        None,
    )

    request_id = (
        request_id_value
        if isinstance(
            request_id_value,
            str,
        )
        else None
    )

    return AssistantModelTurn(
        text=text,
        tool_calls=(
            normalized_tool_calls
        ),
        assistant_message=(
            assistant_message
        ),
        request_id=request_id,
    )
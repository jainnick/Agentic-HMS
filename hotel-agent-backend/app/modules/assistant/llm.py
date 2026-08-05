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

from app.core.config import get_settings
from app.modules.assistant.tools.knowledge import (
    KNOWLEDGE_SEARCH_TOOL_NAME,
    KnowledgeSearchToolInput,
)

logger = structlog.get_logger(__name__)

# The assistant service works with simple dictionaries instead of OpenAI SDK
# message classes. This keeps provider-specific types inside this file.
AssistantMessage = dict[str, Any]


class AssistantLlmError(Exception):
    """Base error raised by the assistant LLM boundary."""


class AssistantLlmConfigurationError(AssistantLlmError):
    """Raised when the LLM provider is not configured correctly."""


class AssistantLlmRequestError(AssistantLlmError):
    """Raised when the configured LLM-provider request fails."""


class AssistantLlmRateLimitError(AssistantLlmRequestError):
    """Raised when the LLM provider's rate limit has been reached."""


class AssistantLlmResponseError(AssistantLlmError):
    """Raised when the LLM provider returns an unusable response."""


@dataclass(frozen=True, slots=True)
class AssistantFunctionCall:
    """
    One function call requested by the language model.

    arguments contains the raw JSON string produced by the model. The
    assistant service validates that JSON against the tool's Pydantic model
    before executing the tool.
    """

    call_id: str
    name: str
    arguments: str


@dataclass(frozen=True, slots=True)
class AssistantModelTurn:
    """
    Normalized result from one language-model request.

    The rest of the application consumes this object instead of depending on
    OpenAI SDK response classes.
    """

    text: str | None
    tool_calls: list[AssistantFunctionCall]
    assistant_message: AssistantMessage
    request_id: str | None


def build_knowledge_search_tool_definition() -> dict[str, Any]:
    """
    Build the provider-facing definition for the knowledge_search tool.

    KnowledgeSearchToolInput remains the source of truth for the accepted
    arguments. Because organization_id and property_id are not present in
    that model, the LLM cannot supply tenant identifiers through the tool.
    """

    parameters = KnowledgeSearchToolInput.model_json_schema()

    return {
        "type": "function",
        "function": {
            "name": KNOWLEDGE_SEARCH_TOOL_NAME,
            "description": (
                "Search the selected hotel's active knowledge documents for "
                "property-specific policies, facilities, services, rooms, "
                "dining, events, check-in, checkout, cancellations, pets, "
                "parking, and other guest information."
            ),
            "parameters": parameters,
            # The backend performs the authoritative Pydantic validation.
            # False is more compatible with OpenAI-compatible providers such
            # as Groq than relying on provider-side strict-schema support.
            "strict": False,
        },
    }


@lru_cache(maxsize=1)
def get_llm_client() -> AsyncOpenAI:
    """
    Create and cache the asynchronous OpenAI-compatible client.

    For Groq, configure:

    LLM_BASE_URL=https://api.groq.com/openai/v1
    LLM_API_KEY=gsk_...
    LLM_MODEL=llama-3.3-70b-versatile

    The client is reused within the current Python process instead of being
    recreated for every assistant request.
    """

    settings = get_settings()

    if settings.llm_api_key is None:
        raise AssistantLlmConfigurationError(
            "LLM_API_KEY is not configured."
        )

    if settings.llm_model is None or not settings.llm_model.strip():
        raise AssistantLlmConfigurationError(
            "LLM_MODEL is not configured."
        )

    client_options: dict[str, Any] = {
        "api_key": settings.llm_api_key.get_secret_value(),
        "timeout": settings.llm_timeout_seconds,
    }

    if (
        settings.llm_base_url is not None
        and settings.llm_base_url.strip()
    ):
        client_options["base_url"] = (
            settings.llm_base_url.strip()
        )

    return AsyncOpenAI(
        **client_options,
    )


def build_assistant_message(
    *,
    content: str | None,
    tool_calls: list[AssistantFunctionCall],
) -> AssistantMessage:
    """
    Build the assistant message that will be sent back on the next LLM call.

    The provider requires the original assistant tool request to appear before
    the corresponding role='tool' result. We rebuild only the fields needed
    for that conversation instead of forwarding every provider-specific field
    returned by the SDK.
    """

    assistant_message: AssistantMessage = {
        "role": "assistant",
    }

    if content is not None:
        assistant_message["content"] = content

    if tool_calls:
        assistant_message["tool_calls"] = [
            {
                "id": tool_call.call_id,
                "type": "function",
                "function": {
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                },
            }
            for tool_call in tool_calls
        ]

    return assistant_message


async def generate_assistant_turn(
    messages: list[AssistantMessage],
) -> AssistantModelTurn:
    """
    Send one assistant turn to the configured language model.

    The function:

    1. sends the current conversation and available tool definition;
    2. receives either response text or function-tool calls;
    3. rejects unsupported custom tool-call variants;
    4. converts SDK objects into application-owned dataclasses.

    This is the only module that should depend directly on OpenAI-compatible
    SDK response types.
    """

    settings = get_settings()

    if settings.llm_model is None or not settings.llm_model.strip():
        raise AssistantLlmConfigurationError(
            "LLM_MODEL is not configured."
        )

    client = get_llm_client()

    try:
        completion = await client.chat.completions.create(
            model=settings.llm_model.strip(),
            messages=cast(
                Any,
                messages,
            ),
            tools=cast(
                Any,
                [
                    build_knowledge_search_tool_definition(),
                ],
            ),
            tool_choice="auto",
            max_completion_tokens=(
                settings.llm_max_output_tokens
            ),
        )

    except openai.APITimeoutError as exc:
        raise AssistantLlmRequestError(
            "The language-model request timed out."
        ) from exc

    except openai.APIConnectionError as exc:
        raise AssistantLlmRequestError(
            "The language-model provider could not be reached."
        ) from exc

    # RateLimitError is a subtype of APIStatusError, so it must be handled
    # before the broader APIStatusError block.
    except openai.RateLimitError as exc:
        raise AssistantLlmRateLimitError(
            "The Hotel Assistant is temporarily busy. "
            "Please retry shortly."
        ) from exc

    except openai.APIStatusError as exc:
        logger.exception(
            "assistant_llm_status_error",
            status_code=exc.status_code,
            request_id=getattr(
                exc,
                "request_id",
                None,
            ),
        )

        raise AssistantLlmRequestError(
            "The language-model provider rejected the request."
        ) from exc

    except openai.OpenAIError as exc:
        raise AssistantLlmRequestError(
            "The language-model request failed."
        ) from exc

    if not completion.choices:
        raise AssistantLlmResponseError(
            "The language model returned no completion choices."
        )

    message = completion.choices[0].message

    text: str | None = None

    if message.content is not None:
        normalized_text = message.content.strip()

        if normalized_text:
            text = normalized_text

    normalized_tool_calls: list[
        AssistantFunctionCall
    ] = []

    for tool_call in message.tool_calls or []:
        # New OpenAI SDK versions type message.tool_calls as a union of:
        #
        # - ChatCompletionMessageFunctionToolCall
        # - ChatCompletionMessageCustomToolCall
        #
        # Only function tool calls contain .function.name and
        # .function.arguments. This isinstance check narrows the union for
        # mypy and rejects tool-call formats our application does not support.
        if not isinstance(
            tool_call,
            ChatCompletionMessageFunctionToolCall,
        ):
            raise AssistantLlmResponseError(
                "The language model returned an unsupported "
                "custom tool call."
            )

        normalized_tool_calls.append(
            AssistantFunctionCall(
                call_id=tool_call.id,
                name=tool_call.function.name,
                arguments=tool_call.function.arguments,
            )
        )

    # Keep the provider's original content for conversation continuity. The
    # separately returned `text` field remains normalized for final answers.
    assistant_message = build_assistant_message(
        content=message.content,
        tool_calls=normalized_tool_calls,
    )

    request_id_value = getattr(
        completion,
        "_request_id",
        None,
    )

    request_id = (
        request_id_value
        if isinstance(request_id_value, str)
        else None
    )

    return AssistantModelTurn(
        text=text,
        tool_calls=normalized_tool_calls,
        assistant_message=assistant_message,
        request_id=request_id,
    )
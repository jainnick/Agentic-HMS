from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import (
    DatabaseSessionDependency,
    TenantContextDependency,
)
from app.modules.assistant.context import (
    AssistantToolContext,
    AssistantToolContextError,
)
from app.modules.assistant.llm import (
    AssistantLlmConfigurationError,
    AssistantLlmRateLimitError,
    AssistantLlmRequestError,
    AssistantLlmResponseError,
)
from app.modules.assistant.schemas import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantSourceResponse,
    AssistantToolCallResponse,
)
from app.modules.assistant.service import (
    AssistantEmptyResponseError,
    AssistantMessageValidationError,
    AssistantToolArgumentsError,
    AssistantToolRoundLimitError,
    AssistantUnsupportedToolError,
    run_hotel_assistant,
)
from app.modules.knowledge.embeddings import EmbeddingError
from app.modules.knowledge.repository import KnowledgeRepositoryError
from app.modules.knowledge.service import KnowledgeSearchValidationError
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.service import (
    TenantAccessDeniedError,
    require_property_management_access,
)

logger = structlog.get_logger(__name__)

router = APIRouter(
    prefix="/admin/assistant",
    tags=["Assistant Admin"],
)


def require_selected_management_property(
    tenant_context: TenantContext,
) -> UUID:
    """
    Require a selected property and verified property-management permission.

    TenantContext has already verified that the property belongs to the
    organization and that the authenticated user has tenant access.
    """

    property_id = tenant_context.property_id

    if property_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=("A property must be selected using the X-Property-ID header."),
        )

    try:
        require_property_management_access(
            tenant_context,
        )

    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Property management access is required.",
        ) from exc

    return property_id


@router.post(
    "/chat-test",
    response_model=AssistantChatResponse,
    status_code=status.HTTP_200_OK,
)
async def chat_with_hotel_assistant_test(
    request: AssistantChatRequest,
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> AssistantChatResponse:
    """
    Test the Hotel Assistant for one authenticated hotel property.

    This administrative endpoint verifies the complete flow:

    authenticated user
        -> verified tenant context
        -> trusted assistant context
        -> LLM tool selection
        -> property-filtered knowledge search
        -> grounded answer
    """

    property_id = require_selected_management_property(
        tenant_context,
    )

    try:
        tool_context = AssistantToolContext.from_tenant_context(
            session=session,
            tenant_context=tenant_context,
        )

        result = await run_hotel_assistant(
            message=request.message,
            context=tool_context,
        )

    except (
        AssistantMessageValidationError,
        AssistantToolContextError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    except AssistantLlmRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=("The Hotel Assistant is temporarily busy. Please retry shortly."),
        ) from exc

    except AssistantLlmConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The Hotel Assistant is not configured.",
        ) from exc

    except EmbeddingError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=("The knowledge-search service is temporarily unavailable."),
        ) from exc

    except KnowledgeRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Knowledge retrieval could not be completed.",
        ) from exc

    except AssistantLlmRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("The language-model provider could not complete the request."),
        ) from exc

    except (
        AssistantLlmResponseError,
        AssistantUnsupportedToolError,
        AssistantToolArgumentsError,
        AssistantToolRoundLimitError,
        AssistantEmptyResponseError,
        KnowledgeSearchValidationError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=("The Hotel Assistant returned an unusable response."),
        ) from exc

    logger.info(
        "hotel_assistant_request_completed",
        organization_id=str(
            tenant_context.organization_id,
        ),
        property_id=str(property_id),
        source_count=len(result.sources),
        tool_call_count=len(result.tool_calls),
        tool_names=[tool_call.name for tool_call in result.tool_calls],
        model_request_ids=result.model_request_ids,
    )

    return AssistantChatResponse(
        answer=result.answer,
        sources=[
            AssistantSourceResponse(
                document_title=source.document_title,
                page_number=source.page_number,
                heading=source.heading,
            )
            for source in result.sources
        ],
        tool_calls=[
            AssistantToolCallResponse(
                name=tool_call.name,
                returned_count=tool_call.returned_count,
            )
            for tool_call in result.tool_calls
        ],
    )

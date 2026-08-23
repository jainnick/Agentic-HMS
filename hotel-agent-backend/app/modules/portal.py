from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import func, select

from app.api.dependencies import DatabaseSessionDependency, TenantContextDependency
from app.modules.assistant.context import AssistantToolContext
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
from app.modules.assistant.sessions import AssistantSession, AssistantSessionNotFoundError
from app.modules.knowledge.embeddings import EmbeddingError
from app.modules.knowledge.models import KnowledgeChunk, KnowledgeDocument
from app.modules.knowledge.repository import KnowledgeRepositoryError
from app.modules.knowledge.service import KnowledgeSearchValidationError
from app.modules.property_tools import PropertyToolResponse, list_property_tools
from app.modules.rooms import RoomBooking, RoomBookingStatus, RoomType
from app.modules.tenancy.context import TenantContext
from app.modules.tenancy.enums import LifecycleStatus
from app.modules.tenancy.models import Organization, Property
from app.modules.tenancy.service import TenantAccessDeniedError, require_property_management_access

router = APIRouter(tags=["Portal"])


class PublicRoomType(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    max_adults: int
    max_children: int
    nightly_rate: Decimal
    currency: str


class WidgetBootstrapResponse(BaseModel):
    organization_name: str
    organization_slug: str
    property_id: UUID
    property_name: str
    property_code: str
    timezone: str
    currency: str
    rooms: list[PublicRoomType]
    tools: list[PropertyToolResponse]


class DashboardProperty(BaseModel):
    organization_name: str
    organization_slug: str
    property_id: UUID
    property_name: str
    property_code: str
    timezone: str
    currency: str


class DashboardRoom(BaseModel):
    id: UUID
    code: str
    name: str
    description: str | None
    total_rooms: int
    max_adults: int
    max_children: int
    nightly_rate: Decimal
    currency: str
    is_active: bool


class DashboardBooking(BaseModel):
    confirmation_code: str
    guest_name: str
    room_type_name: str
    check_in: str
    check_out: str
    rooms: int
    adults: int
    children: int
    total_amount: Decimal
    currency: str
    status: str
    created_at: datetime


class DashboardKnowledgeDocument(BaseModel):
    id: UUID
    title: str
    original_filename: str | None
    status: str
    is_active: bool
    version_number: int
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DashboardMetrics(BaseModel):
    guest_sessions_today: int
    bookings_this_week: int
    questions_answered: int


class DashboardResponse(BaseModel):
    property: DashboardProperty
    metrics: DashboardMetrics
    rooms: list[DashboardRoom]
    bookings: list[DashboardBooking]
    knowledge_documents: list[DashboardKnowledgeDocument]
    tools: list[PropertyToolResponse]


def require_dashboard_property(tenant_context: TenantContext) -> UUID:
    property_id = tenant_context.property_id
    if property_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A property must be selected using the X-Property-ID header.",
        )
    try:
        require_property_management_access(tenant_context)
    except TenantAccessDeniedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Property management access is required.",
        ) from exc
    return property_id


async def resolve_public_property(
    session: DatabaseSessionDependency,
    property_code: str,
) -> tuple[Property, Organization]:
    row = (
        await session.execute(
            select(Property, Organization)
            .join(Organization, Organization.id == Property.organization_id)
            .where(
                func.upper(Property.code) == property_code.strip().upper(),
                Property.status == LifecycleStatus.ACTIVE,
                Organization.status == LifecycleStatus.ACTIVE,
            )
            .limit(1)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Hotel property not found.",
        )
    return row[0], row[1]


@router.get(
    "/widget/{property_code}/bootstrap",
    response_model=WidgetBootstrapResponse,
)
async def widget_bootstrap(
    property_code: str,
    session: DatabaseSessionDependency,
) -> WidgetBootstrapResponse:
    property_, organization = await resolve_public_property(session, property_code)
    room_types = (
        await session.scalars(
            select(RoomType)
            .where(
                RoomType.organization_id == property_.organization_id,
                RoomType.property_id == property_.id,
                RoomType.is_active.is_(True),
            )
            .order_by(RoomType.nightly_rate, RoomType.name)
        )
    ).all()
    tools = await list_property_tools(session, property_id=property_.id)
    return WidgetBootstrapResponse(
        organization_name=organization.name,
        organization_slug=organization.slug,
        property_id=property_.id,
        property_name=property_.name,
        property_code=property_.code,
        timezone=property_.timezone,
        currency=property_.currency,
        rooms=[
            PublicRoomType(
                id=room.id,
                code=room.code,
                name=room.name,
                description=room.description,
                max_adults=room.max_adults,
                max_children=room.max_children,
                nightly_rate=room.nightly_rate,
                currency=room.currency,
            )
            for room in room_types
        ],
        tools=tools,
    )


@router.post(
    "/widget/{property_code}/chat",
    response_model=AssistantChatResponse,
)
async def widget_chat(
    property_code: str,
    request: AssistantChatRequest,
    session: DatabaseSessionDependency,
) -> AssistantChatResponse:
    property_, _ = await resolve_public_property(session, property_code)
    context = AssistantToolContext(
        session=session,
        organization_id=property_.organization_id,
        property_id=property_.id,
    )
    try:
        result = await run_hotel_assistant(
            message=request.message,
            context=context,
            session_id=request.session_id,
        )
    except (
        AssistantMessageValidationError,
        AssistantSessionNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except AssistantLlmRateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="The hotel assistant is temporarily busy.",
        ) from exc
    except (
        AssistantLlmConfigurationError,
        EmbeddingError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The hotel assistant is temporarily unavailable.",
        ) from exc
    except KnowledgeRepositoryError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Hotel knowledge could not be retrieved.",
        ) from exc
    except AssistantLlmRequestError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The language-model provider could not complete the request.",
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
            detail="The hotel assistant returned an unusable response.",
        ) from exc

    return AssistantChatResponse(
        session_id=result.session_id,
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


@router.get(
    "/admin/dashboard",
    response_model=DashboardResponse,
)
async def admin_dashboard(
    tenant_context: TenantContextDependency,
    session: DatabaseSessionDependency,
) -> DashboardResponse:
    property_id = require_dashboard_property(tenant_context)
    property_row = (
        await session.execute(
            select(Property, Organization)
            .join(Organization, Organization.id == Property.organization_id)
            .where(
                Property.id == property_id,
                Property.organization_id == tenant_context.organization_id,
            )
        )
    ).one_or_none()
    if property_row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Property not found.",
        )
    property_, organization = property_row

    rooms = (
        await session.scalars(
            select(RoomType)
            .where(
                RoomType.organization_id == tenant_context.organization_id,
                RoomType.property_id == property_id,
            )
            .order_by(RoomType.nightly_rate, RoomType.name)
        )
    ).all()

    booking_rows = (
        await session.execute(
            select(RoomBooking, RoomType.name)
            .join(
                RoomType,
                (RoomType.id == RoomBooking.room_type_id)
                & (RoomType.property_id == RoomBooking.property_id)
                & (RoomType.organization_id == RoomBooking.organization_id),
            )
            .where(
                RoomBooking.organization_id == tenant_context.organization_id,
                RoomBooking.property_id == property_id,
            )
            .order_by(RoomBooking.created_at.desc())
            .limit(50)
        )
    ).all()

    document_rows = (
        await session.execute(
            select(
                KnowledgeDocument,
                func.count(KnowledgeChunk.id).label("chunk_count"),
            )
            .outerjoin(
                KnowledgeChunk,
                (KnowledgeChunk.document_id == KnowledgeDocument.id)
                & (KnowledgeChunk.property_id == KnowledgeDocument.property_id)
                & (KnowledgeChunk.organization_id == KnowledgeDocument.organization_id),
            )
            .where(
                KnowledgeDocument.organization_id == tenant_context.organization_id,
                KnowledgeDocument.property_id == property_id,
            )
            .group_by(KnowledgeDocument.id)
            .order_by(KnowledgeDocument.created_at.desc())
        )
    ).all()

    tools = await list_property_tools(session, property_id=property_id)

    now = datetime.now(timezone.utc)
    start_of_day = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_of_week = start_of_day - timedelta(days=start_of_day.weekday())

    session_rows = (
        await session.scalars(
            select(AssistantSession).where(
                AssistantSession.organization_id == tenant_context.organization_id,
                AssistantSession.property_id == property_id,
            )
        )
    ).all()
    guest_sessions_today = sum(1 for row in session_rows if row.created_at >= start_of_day)
    questions_answered = 0
    for row in session_rows:
        messages = row.messages if isinstance(row.messages, list) else []
        questions_answered += sum(
            1
            for message in messages
            if isinstance(message, dict) and message.get("role") == "assistant"
        )

    bookings_this_week = int(
        await session.scalar(
            select(func.count(RoomBooking.id)).where(
                RoomBooking.organization_id == tenant_context.organization_id,
                RoomBooking.property_id == property_id,
                RoomBooking.status == RoomBookingStatus.CONFIRMED,
                RoomBooking.created_at >= start_of_week,
            )
        )
        or 0
    )

    return DashboardResponse(
        property=DashboardProperty(
            organization_name=organization.name,
            organization_slug=organization.slug,
            property_id=property_.id,
            property_name=property_.name,
            property_code=property_.code,
            timezone=property_.timezone,
            currency=property_.currency,
        ),
        metrics=DashboardMetrics(
            guest_sessions_today=guest_sessions_today,
            bookings_this_week=bookings_this_week,
            questions_answered=questions_answered,
        ),
        rooms=[
            DashboardRoom(
                id=room.id,
                code=room.code,
                name=room.name,
                description=room.description,
                total_rooms=room.total_rooms,
                max_adults=room.max_adults,
                max_children=room.max_children,
                nightly_rate=room.nightly_rate,
                currency=room.currency,
                is_active=room.is_active,
            )
            for room in rooms
        ],
        bookings=[
            DashboardBooking(
                confirmation_code=booking.confirmation_code,
                guest_name=booking.guest_name,
                room_type_name=room_type_name,
                check_in=booking.check_in.isoformat(),
                check_out=booking.check_out.isoformat(),
                rooms=booking.rooms,
                adults=booking.adults,
                children=booking.children,
                total_amount=booking.total_amount,
                currency=booking.currency,
                status=booking.status.value,
                created_at=booking.created_at,
            )
            for booking, room_type_name in booking_rows
        ],
        knowledge_documents=[
            DashboardKnowledgeDocument(
                id=document.id,
                title=document.title,
                original_filename=document.original_filename,
                status=getattr(document.status, "value", str(document.status)),
                is_active=document.is_active,
                version_number=document.version_number,
                chunk_count=int(chunk_count),
                created_at=document.created_at,
                updated_at=document.updated_at,
            )
            for document, chunk_count in document_rows
        ],
        tools=tools,
    )

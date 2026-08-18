from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, ConfigDict
from sqlalchemy import (
    DateTime,
    ForeignKeyConstraint,
    Index,
    func,
    select,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

MAX_ASSISTANT_HISTORY_MESSAGES = 20


class AssistantSession(Base):
    """
    One property-scoped assistant conversation.

    messages:
        Recent guest-visible user/assistant conversation history.

    pending_booking:
        Server-owned booking quote waiting for explicit guest confirmation.

    We deliberately do not persist raw LLM tool messages here.
    """

    __tablename__ = "assistant_sessions"

    __table_args__ = (
        ForeignKeyConstraint(
            [
                "organization_id",
                "property_id",
            ],
            [
                "properties.organization_id",
                "properties.id",
            ],
            name="fk_assistant_sessions_property_organization",
            ondelete="CASCADE",
        ),
        Index(
            "ix_assistant_sessions_property",
            "organization_id",
            "property_id",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        server_default=text("gen_random_uuid()"),
    )

    organization_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    property_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    messages: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
    )

    pending_booking: Mapped[dict[str, object] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class AssistantConversationMessage(BaseModel):
    """
    One message persisted in conversation history.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    role: Literal[
        "user",
        "assistant",
    ]

    content: str


class PendingRoomBooking(BaseModel):
    """
    Trusted server-side booking details waiting for confirmation.

    After the guest says "yes", these values are used to create
    the reservation instead of asking the LLM to regenerate them.
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    idempotency_key: UUID

    room_type_id: UUID
    room_type_name: str

    check_in: date
    check_out: date

    adults: int
    children: int
    rooms: int

    guest_name: str

    guest_email: str | None = None
    guest_phone: str | None = None

    nightly_rate: Decimal
    total_amount: Decimal
    currency: str


class AssistantSessionNotFoundError(Exception):
    """Requested assistant session does not exist for this property."""


async def get_or_create_assistant_session(
    session: AsyncSession,
    *,
    organization_id: UUID,
    property_id: UUID,
    session_id: UUID | None,
) -> AssistantSession:
    """
    Continue a property-scoped conversation or start a new one.

    organization_id + property_id are part of the lookup so a session
    from one hotel cannot accidentally be reused for another hotel.
    """

    if session_id is not None:
        assistant_session = await session.scalar(
            select(AssistantSession).where(
                AssistantSession.id == session_id,
                AssistantSession.organization_id == organization_id,
                AssistantSession.property_id == property_id,
            )
        )

        if assistant_session is None:
            raise AssistantSessionNotFoundError("Assistant session was not found.")

        return assistant_session

    assistant_session = AssistantSession(
        organization_id=organization_id,
        property_id=property_id,
        messages=[],
    )

    session.add(assistant_session)

    await session.commit()

    await session.refresh(assistant_session)

    return assistant_session


def get_conversation_history(
    assistant_session: AssistantSession,
) -> list[dict[str, str]]:
    """
    Validate JSONB history before passing it back to the LLM.

    Database JSON is still treated as external input rather than
    blindly trusted.
    """

    messages = [
        AssistantConversationMessage.model_validate(message)
        for message in assistant_session.messages
    ]

    return [message.model_dump() for message in messages]


async def save_conversation_turn(
    session: AsyncSession,
    *,
    assistant_session: AssistantSession,
    user_message: str,
    assistant_message: str,
) -> None:
    """
    Persist one completed conversational turn.

    Only the latest 20 messages are retained for the MVP so token
    usage does not grow forever.
    """

    history = list(assistant_session.messages)

    history.extend(
        [
            AssistantConversationMessage(
                role="user",
                content=user_message,
            ).model_dump(),
            AssistantConversationMessage(
                role="assistant",
                content=assistant_message,
            ).model_dump(),
        ]
    )

    assistant_session.messages = history[-MAX_ASSISTANT_HISTORY_MESSAGES:]

    await session.commit()


def get_pending_booking(
    assistant_session: AssistantSession,
) -> PendingRoomBooking | None:
    """
    Return validated server-owned booking state.
    """

    if assistant_session.pending_booking is None:
        return None

    return PendingRoomBooking.model_validate(assistant_session.pending_booking)


async def set_pending_booking(
    session: AsyncSession,
    *,
    assistant_session: AssistantSession,
    pending_booking: PendingRoomBooking,
) -> None:
    """
    Save a quoted booking waiting for confirmation.
    """

    assistant_session.pending_booking = pending_booking.model_dump(mode="json")

    await session.commit()


async def clear_pending_booking(
    session: AsyncSession,
    *,
    assistant_session: AssistantSession,
) -> None:
    """
    Clear booking state after confirmation or invalidation.
    """

    assistant_session.pending_booking = None

    await session.commit()

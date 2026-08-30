from __future__ import annotations

from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


class AssistantChatRequest(BaseModel):
    """
    One guest message.

    session_id:
    - null/omitted -> start a new conversation
    - supplied -> continue that conversation
    """

    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = Field(
        description=("Question or request submitted to the Hotel Assistant."),
        examples=[
            "Book a Deluxe room.",
        ],
    )

    session_id: UUID | None = Field(
        default=None,
        description=("Existing assistant conversation ID. Omit it for the first message."),
    )


class AssistantSourceResponse(BaseModel):
    """Safe knowledge-source metadata."""

    document_title: str

    page_number: int | None = None

    heading: str | None = None


class AssistantToolCallResponse(BaseModel):
    """Safe summary of one assistant tool call."""

    name: str

    returned_count: int = Field(
        ge=0,
    )


class AssistantPendingBookingResponse(BaseModel):
    """
    Safe guest-facing booking quote.

    Internal IDs and idempotency data deliberately remain server-side.
    """

    room_type_name: str
    total_amount: Decimal
    currency: str


class AssistantChatResponse(BaseModel):
    """
    Guest-facing response.

    session_id must be sent back on later messages.

    next_action="confirm_booking" is returned only when the backend has a
    prepared pending booking waiting for the guest's final confirmation.
    """

    session_id: UUID

    answer: str

    sources: list[AssistantSourceResponse] = Field(
        default_factory=list,
    )

    tool_calls: list[AssistantToolCallResponse] = Field(
        default_factory=list,
    )

    next_action: Literal["confirm_booking"] | None = None

    pending_booking: AssistantPendingBookingResponse | None = None

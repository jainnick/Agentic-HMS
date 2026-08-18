from __future__ import annotations

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


class AssistantChatResponse(BaseModel):
    """
    Guest-facing response.

    session_id must be sent back on later messages.
    """

    session_id: UUID

    answer: str

    sources: list[AssistantSourceResponse] = Field(
        default_factory=list,
    )

    tool_calls: list[AssistantToolCallResponse] = Field(
        default_factory=list,
    )

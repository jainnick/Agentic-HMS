from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class AssistantChatRequest(BaseModel):
    """Guest message submitted to the authenticated Hotel Assistant."""

    model_config = ConfigDict(
        extra="forbid",
    )

    message: str = Field(
        description="Question or request submitted to the Hotel Assistant.",
        examples=[
            "What time is checkout?",
        ],
    )


class AssistantSourceResponse(BaseModel):
    """Safe knowledge-source metadata returned with an assistant answer."""

    document_title: str
    page_number: int | None = None
    heading: str | None = None


class AssistantToolCallResponse(BaseModel):
    """Safe summary of one assistant tool execution."""

    name: str
    returned_count: int = Field(
        ge=0,
    )


class AssistantChatResponse(BaseModel):
    """Guest-facing response from the Hotel Assistant."""

    answer: str
    sources: list[AssistantSourceResponse] = Field(
        default_factory=list,
    )
    tool_calls: list[AssistantToolCallResponse] = Field(
        default_factory=list,
    )

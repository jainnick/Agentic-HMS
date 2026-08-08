from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.modules.assistant.context import AssistantToolContext
from app.modules.knowledge.service import search_property_knowledge

KNOWLEDGE_SEARCH_TOOL_NAME = "knowledge_search"
KNOWLEDGE_SEARCH_TOOL_LABEL = "knowledge.search"
MAX_KNOWLEDGE_TOOL_MATCH_COUNT = 6


class KnowledgeSearchToolInput(BaseModel):
    """
    Arguments the LLM is allowed to supply to knowledge.search.

    Tenant identifiers are intentionally absent because the backend supplies
    them through AssistantToolContext.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=2_000,
        description=(
            "A focused question about this hotel's policies, facilities, "
            "services, rooms, dining, events, or guest information."
        ),
        examples=[
            "What time is checkout?",
        ],
    )

    match_count: int | None = Field(
        default=None,
        ge=1,
        le=MAX_KNOWLEDGE_TOOL_MATCH_COUNT,
        description=(
            "Maximum number of relevant knowledge chunks to return. "
            "Usually 3 to 6 results are sufficient."
        ),
        examples=[
            5,
        ],
    )


class KnowledgeSearchToolMatch(BaseModel):
    """
    One safe source passage returned to the assistant.

    Internal database identifiers, source keys, similarity scores, and
    embeddings are intentionally excluded.
    """

    document_title: str
    heading: str | None
    page_number: int | None
    content: str


class KnowledgeSearchToolResult(BaseModel):
    """Structured result returned by knowledge.search."""

    query: str
    returned_count: int
    matches: list[KnowledgeSearchToolMatch]


async def execute_knowledge_search_tool(
    tool_input: KnowledgeSearchToolInput,
    *,
    context: AssistantToolContext,
) -> KnowledgeSearchToolResult:
    """
    Search the selected property's active hotel knowledge.

    This is a thin adapter between the assistant and the existing retrieval
    service. It does not generate a guest-facing response.
    """

    matches = await search_property_knowledge(
        context.session,
        organization_id=context.organization_id,
        property_id=context.property_id,
        query=tool_input.query,
        match_count=tool_input.match_count,
    )

    tool_matches = [
        KnowledgeSearchToolMatch(
            document_title=match.document_title,
            heading=match.heading,
            page_number=match.page_number,
            content=match.content,
        )
        for match in matches
    ]

    return KnowledgeSearchToolResult(
        query=tool_input.query,
        returned_count=len(tool_matches),
        matches=tool_matches,
    )

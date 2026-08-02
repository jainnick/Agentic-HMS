from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.modules.knowledge.enums import (
    KnowledgeDocumentStatus,
    KnowledgeSourceType,
)


class KnowledgePdfUploadResponse(BaseModel):
    """
    Response returned after a PDF has been completely processed.

    The first implementation processes PDFs synchronously, so a successful
    response means chunks and embeddings have already been stored.
    """

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: UUID
    organization_id: UUID
    property_id: UUID

    title: str
    source_type: KnowledgeSourceType
    original_filename: str | None
    source_key: str
    version_number: int

    status: KnowledgeDocumentStatus
    is_active: bool
    chunk_count: int

    created_at: datetime
    updated_at: datetime


class KnowledgeSearchRequest(BaseModel):
    """
    Request body for the temporary administrative retrieval endpoint.

    Tenant identifiers are deliberately excluded. The backend obtains them
    from the verified TenantContext dependency.
    """

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    query: str = Field(
        min_length=1,
        max_length=2_000,
        description="Question to search for in the selected property's knowledge.",
        examples=[
            "What time is checkout?",
        ],
    )

    match_count: int | None = Field(
        default=None,
        ge=1,
        le=20,
        description=(
            "Maximum number of matching chunks to return. "
            "The configured default is used when omitted."
        ),
        examples=[
            6,
        ],
    )

    min_similarity: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum cosine similarity accepted by retrieval. "
            "The configured default is used when omitted."
        ),
        examples=[
            0.45,
        ],
    )


class KnowledgeSearchMatchResponse(BaseModel):
    """One matching document chunk returned by vector retrieval."""

    chunk_id: UUID
    document_id: UUID

    document_title: str
    source_key: str
    version_number: int

    chunk_index: int
    content: str
    heading: str | None
    page_number: int | None

    similarity: float = Field(
        ge=0.0,
        le=1.0,
    )


class KnowledgeSearchResponse(BaseModel):
    """Response returned by the temporary retrieval endpoint."""

    query: str
    returned_count: int = Field(
        ge=0,
    )
    matches: list[KnowledgeSearchMatchResponse]

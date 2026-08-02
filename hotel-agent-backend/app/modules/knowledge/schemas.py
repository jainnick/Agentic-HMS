from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

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

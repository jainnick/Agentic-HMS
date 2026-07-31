from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import (
    JSONB,
)
from sqlalchemy.dialects.postgresql import (
    UUID as PostgreSQLUUID,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.base import Base
from app.modules.knowledge.enums import (
    KnowledgeDocumentStatus,
    KnowledgeSourceType,
)


class KnowledgeDocument(Base):
    """
    One version of a hotel knowledge source.

    Examples:
    - guest-policy.pdf version 1
    - guest-policy.pdf version 2
    - manually entered FAQ content
    """

    __tablename__ = "knowledge_documents"
    __table_args__ = (
        # Ensures the property belongs to the supplied organization.
        ForeignKeyConstraint(
            [
                "organization_id",
                "property_id",
            ],
            [
                "properties.organization_id",
                "properties.id",
            ],
            name="fk_knowledge_documents_property_organization",
            ondelete="CASCADE",
        ),
        # A logical source can have multiple versions, but not duplicate
        # version numbers inside the same hotel property.
        UniqueConstraint(
            "property_id",
            "source_key",
            "version_number",
            name="uq_knowledge_documents_property_source_version",
        ),
        # Required for the composite foreign key from knowledge_chunks.
        UniqueConstraint(
            "organization_id",
            "property_id",
            "id",
            name="uq_knowledge_documents_organization_property_id",
        ),
        CheckConstraint(
            "version_number > 0",
            name="ck_knowledge_documents_version_positive",
        ),
        CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_knowledge_documents_title_not_blank",
        ),
        CheckConstraint(
            "char_length(btrim(source_key)) > 0",
            name="ck_knowledge_documents_source_key_not_blank",
        ),
        CheckConstraint(
            "char_length(checksum) = 64",
            name="ck_knowledge_documents_checksum_sha256",
        ),
        Index(
            "ix_knowledge_documents_tenant_status",
            "organization_id",
            "property_id",
            "status",
            "is_active",
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

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    source_type: Mapped[KnowledgeSourceType] = mapped_column(
        Enum(
            KnowledgeSourceType,
            name="knowledge_document_source_type",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
    )

    original_filename: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    source_key: Mapped[str] = mapped_column(
        String(120),
        nullable=False,
    )

    version_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default=text("1"),
    )

    checksum: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    status: Mapped[KnowledgeDocumentStatus] = mapped_column(
        Enum(
            KnowledgeDocumentStatus,
            name="knowledge_document_status",
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum_type: [member.value for member in enum_type],
        ),
        nullable=False,
        default=KnowledgeDocumentStatus.PROCESSING,
        server_default=KnowledgeDocumentStatus.PROCESSING.value,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Supabase Auth user UUID.
    created_by: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
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

    chunks: Mapped[list[KnowledgeChunk]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class KnowledgeChunk(Base):
    """
    One searchable piece of a knowledge document.

    Tenant identifiers are repeated intentionally so vector retrieval can
    filter by organization and property before similarity ranking.
    """

    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        # Prevents document_id from being combined with the wrong
        # organization_id or property_id.
        ForeignKeyConstraint(
            [
                "organization_id",
                "property_id",
                "document_id",
            ],
            [
                "knowledge_documents.organization_id",
                "knowledge_documents.property_id",
                "knowledge_documents.id",
            ],
            name="fk_knowledge_chunks_document_tenant",
            ondelete="CASCADE",
        ),
        UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_knowledge_chunks_document_chunk_index",
        ),
        CheckConstraint(
            "chunk_index >= 0",
            name="ck_knowledge_chunks_index_non_negative",
        ),
        CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_knowledge_chunks_page_positive",
        ),
        CheckConstraint(
            "char_length(btrim(content)) > 0",
            name="ck_knowledge_chunks_content_not_blank",
        ),
        CheckConstraint(
            "char_length(content_hash) = 64",
            name="ck_knowledge_chunks_content_hash_sha256",
        ),
        Index(
            "ix_knowledge_chunks_tenant",
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

    document_id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True),
        nullable=False,
    )

    chunk_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    heading: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    page_number: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    content_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )

    embedding: Mapped[list[float]] = mapped_column(
        VECTOR(384),
        nullable=False,
    )

    # `metadata` is reserved by SQLAlchemy's declarative base.
    # The Python attribute is metadata_, while the database column is metadata.
    metadata_: Mapped[dict[str, object]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    document: Mapped[KnowledgeDocument] = relationship(
        back_populates="chunks",
    )

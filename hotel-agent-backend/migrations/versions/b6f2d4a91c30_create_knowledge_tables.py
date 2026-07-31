"""create knowledge tables

Revision ID: b6f2d4a91c30
Revises: a81c4f6b2d90
Create Date: 2026-07-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

revision: str = "b6f2d4a91c30"
down_revision: str | Sequence[str] | None = "a81c4f6b2d90"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create tenant-scoped knowledge document and chunk tables."""

    # Supabase normally keeps extensions in this schema.
    op.execute(
        """
        CREATE SCHEMA IF NOT EXISTS extensions
        """
    )

    op.execute(
        """
        CREATE EXTENSION IF NOT EXISTS vector
        WITH SCHEMA extensions
        """
    )

    # pgvector's SQLAlchemy type emits VECTOR(...).
    # Adding extensions to the migration search path lets PostgreSQL resolve it.
    op.execute(
        """
        SET LOCAL search_path = public, extensions
        """
    )

    op.create_table(
        "knowledge_documents",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "title",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "source_type",
            sa.Enum(
                "pdf",
                "manual",
                name="knowledge_document_source_type",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column(
            "original_filename",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "source_key",
            sa.String(length=120),
            nullable=False,
        ),
        sa.Column(
            "version_number",
            sa.Integer(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "checksum",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "status",
            sa.Enum(
                "processing",
                "ready",
                "failed",
                name="knowledge_document_status",
                native_enum=False,
                create_constraint=True,
            ),
            server_default="processing",
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column(
            "error_message",
            sa.Text(),
            nullable=True,
        ),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "version_number > 0",
            name="ck_knowledge_documents_version_positive",
        ),
        sa.CheckConstraint(
            "char_length(btrim(title)) > 0",
            name="ck_knowledge_documents_title_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(btrim(source_key)) > 0",
            name="ck_knowledge_documents_source_key_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(checksum) = 64",
            name="ck_knowledge_documents_checksum_sha256",
        ),
        sa.ForeignKeyConstraint(
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
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "property_id",
            "source_key",
            "version_number",
            name="uq_knowledge_documents_property_source_version",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "property_id",
            "id",
            name="uq_knowledge_documents_organization_property_id",
        ),
    )

    op.create_index(
        "ix_knowledge_documents_tenant_status",
        "knowledge_documents",
        [
            "organization_id",
            "property_id",
            "status",
            "is_active",
        ],
        unique=False,
    )

    op.create_table(
        "knowledge_chunks",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "chunk_index",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "heading",
            sa.String(length=500),
            nullable=True,
        ),
        sa.Column(
            "content",
            sa.Text(),
            nullable=False,
        ),
        sa.Column(
            "page_number",
            sa.Integer(),
            nullable=True,
        ),
        sa.Column(
            "content_hash",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "embedding",
            VECTOR(384),
            nullable=False,
        ),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chunk_index >= 0",
            name="ck_knowledge_chunks_index_non_negative",
        ),
        sa.CheckConstraint(
            "page_number IS NULL OR page_number > 0",
            name="ck_knowledge_chunks_page_positive",
        ),
        sa.CheckConstraint(
            "char_length(btrim(content)) > 0",
            name="ck_knowledge_chunks_content_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(content_hash) = 64",
            name="ck_knowledge_chunks_content_hash_sha256",
        ),
        sa.ForeignKeyConstraint(
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
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "document_id",
            "chunk_index",
            name="uq_knowledge_chunks_document_chunk_index",
        ),
    )

    op.create_index(
        "ix_knowledge_chunks_tenant",
        "knowledge_chunks",
        [
            "organization_id",
            "property_id",
        ],
        unique=False,
    )

    # Keep the same security model as the existing tenancy tables:
    # authenticated users can read tenant-accessible data, while writes
    # continue through FastAPI.
    op.execute(
        """
        GRANT SELECT ON
            public.knowledge_documents,
            public.knowledge_chunks
        TO authenticated
        """
    )

    op.execute(
        """
        ALTER TABLE public.knowledge_documents
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        ALTER TABLE public.knowledge_chunks
        ENABLE ROW LEVEL SECURITY
        """
    )

    op.execute(
        """
        CREATE POLICY knowledge_documents_select_for_property_members
        ON public.knowledge_documents
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_property(
                organization_id,
                property_id
            )
        )
        """
    )

    op.execute(
        """
        CREATE POLICY knowledge_chunks_select_for_property_members
        ON public.knowledge_chunks
        FOR SELECT
        TO authenticated
        USING (
            private.can_access_property(
                organization_id,
                property_id
            )
        )
        """
    )


def downgrade() -> None:
    """Remove knowledge tables without removing the shared vector extension."""

    op.execute(
        """
        DROP POLICY IF EXISTS
            knowledge_chunks_select_for_property_members
        ON public.knowledge_chunks
        """
    )

    op.execute(
        """
        DROP POLICY IF EXISTS
            knowledge_documents_select_for_property_members
        ON public.knowledge_documents
        """
    )

    op.execute(
        """
        REVOKE SELECT ON
            public.knowledge_documents,
            public.knowledge_chunks
        FROM authenticated
        """
    )

    op.drop_index(
        "ix_knowledge_chunks_tenant",
        table_name="knowledge_chunks",
    )

    op.drop_table(
        "knowledge_chunks",
    )

    op.drop_index(
        "ix_knowledge_documents_tenant_status",
        table_name="knowledge_documents",
    )

    op.drop_table(
        "knowledge_documents",
    )

    # Do not drop the vector extension because other current or future tables
    # may also use it.

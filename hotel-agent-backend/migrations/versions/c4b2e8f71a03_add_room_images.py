"""add room images

Revision ID: c4b2e8f71a03
Revises: 6a9f3c1d8e42
Create Date: 2026-08-30

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c4b2e8f71a03"
down_revision: str | Sequence[str] | None = "6a9f3c1d8e42"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Add lightweight room-photo metadata and its public Storage bucket."""

    op.add_column(
        "room_types",
        sa.Column(
            "room_images",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
    )

    op.execute(
        """
        INSERT INTO storage.buckets (
            id,
            name,
            public,
            file_size_limit,
            allowed_mime_types
        )
        VALUES (
            'room-images',
            'room-images',
            true,
            5242880,
            ARRAY['image/jpeg', 'image/png', 'image/webp']::text[]
        )
        ON CONFLICT (id) DO UPDATE SET
            public = EXCLUDED.public,
            file_size_limit = EXCLUDED.file_size_limit,
            allowed_mime_types = EXCLUDED.allowed_mime_types
        """
    )


def downgrade() -> None:
    """Remove room image metadata; uploaded objects are deliberately retained."""

    op.drop_column("room_types", "room_images")

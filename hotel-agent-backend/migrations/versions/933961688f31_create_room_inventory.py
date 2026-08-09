"""create room inventory

Revision ID: 933961688f31
Revises: 250d0d8058ef
Create Date: 2026-08-09 14:41:44.672419
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "933961688f31"
down_revision: str | Sequence[str] | None = "250d0d8058ef"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""

    op.create_table(
        "room_types",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            nullable=False,
        ),
        sa.Column(
            "organization_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "property_id",
            sa.UUID(),
            nullable=False,
        ),
        sa.Column(
            "code",
            sa.String(length=64),
            nullable=False,
        ),
        sa.Column(
            "name",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "description",
            sa.String(length=1000),
            nullable=True,
        ),
        sa.Column(
            "total_rooms",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "max_adults",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "max_children",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column(
            "nightly_rate",
            sa.Numeric(
                precision=12,
                scale=2,
            ),
            nullable=False,
        ),
        sa.Column(
            "currency",
            sa.String(length=3),
            nullable=False,
        ),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("true"),
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
            "char_length(btrim(code)) > 0",
            name="ck_room_types_code_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(btrim(name)) > 0",
            name="ck_room_types_name_not_blank",
        ),
        sa.CheckConstraint(
            "char_length(currency) = 3 AND currency = upper(currency)",
            name="ck_room_types_currency_code",
        ),
        sa.CheckConstraint(
            "max_adults > 0",
            name="ck_room_types_max_adults_positive",
        ),
        sa.CheckConstraint(
            "max_children >= 0",
            name="ck_room_types_max_children_non_negative",
        ),
        sa.CheckConstraint(
            "nightly_rate >= 0",
            name="ck_room_types_nightly_rate_non_negative",
        ),
        sa.CheckConstraint(
            "total_rooms > 0",
            name="ck_room_types_total_rooms_positive",
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
            name="fk_room_types_property_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id",
        ),
        sa.UniqueConstraint(
            "organization_id",
            "property_id",
            "id",
            name="uq_room_types_organization_property_id",
        ),
        sa.UniqueConstraint(
            "property_id",
            "code",
            name="uq_room_types_property_id_code",
        ),
    )

    op.create_index(
        "ix_room_types_property_active",
        "room_types",
        [
            "organization_id",
            "property_id",
            "is_active",
        ],
        unique=False,
    )

    # Alembic does not infer PostgreSQL/Supabase RLS automatically.
    op.execute(
        """
        ALTER TABLE public.room_types
        ENABLE ROW LEVEL SECURITY
        """
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_index(
        "ix_room_types_property_active",
        table_name="room_types",
    )

    op.drop_table(
        "room_types",
    )

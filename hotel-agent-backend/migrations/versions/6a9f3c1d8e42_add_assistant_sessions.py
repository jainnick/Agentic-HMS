"""add assistant sessions and booking idempotency

Revision ID: 6a9f3c1d8e42
Revises: 2f8110355a4d
Create Date: 2026-08-10

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = "6a9f3c1d8e42"

down_revision: (
    str | Sequence[str] | None
) = "2f8110355a4d"

branch_labels: (
    str | Sequence[str] | None
) = None

depends_on: (
    str | Sequence[str] | None
) = None


def upgrade() -> None:
    """
    Add stateful assistant conversations and
    booking-command idempotency.
    """

    op.add_column(
        "room_bookings",
        sa.Column(
            "idempotency_key",
            sa.UUID(),
            nullable=True,
        ),
    )

    op.create_unique_constraint(
        "uq_room_bookings_idempotency_key",
        "room_bookings",
        [
            "idempotency_key",
        ],
    )

    op.create_table(
        "assistant_sessions",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text(
                "gen_random_uuid()"
            ),
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
            "messages",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            server_default=sa.text(
                "'[]'::jsonb"
            ),
            nullable=False,
        ),
        sa.Column(
            "pending_booking",
            postgresql.JSONB(
                astext_type=sa.Text()
            ),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=sa.text(
                "now()"
            ),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(
                timezone=True
            ),
            server_default=sa.text(
                "now()"
            ),
            nullable=False,
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
            name=(
                "fk_assistant_sessions_"
                "property_organization"
            ),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "id"
        ),
    )

    op.create_index(
        "ix_assistant_sessions_property",
        "assistant_sessions",
        [
            "organization_id",
            "property_id",
        ],
        unique=False,
    )

    op.execute(
        """
        ALTER TABLE public.assistant_sessions
        ENABLE ROW LEVEL SECURITY
        """
    )


def downgrade() -> None:
    """
    Remove assistant session state and idempotency.
    """

    op.drop_index(
        "ix_assistant_sessions_property",
        table_name="assistant_sessions",
    )

    op.drop_table(
        "assistant_sessions"
    )

    op.drop_constraint(
        "uq_room_bookings_idempotency_key",
        "room_bookings",
        type_="unique",
    )

    op.drop_column(
        "room_bookings",
        "idempotency_key",
    )
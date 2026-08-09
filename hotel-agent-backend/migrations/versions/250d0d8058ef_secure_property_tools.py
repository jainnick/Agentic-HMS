"""secure property tools

Revision ID: 250d0d8058ef
Revises: 86f9c1691f20
Create Date: 2026-08-09 01:28:29.606989

"""

from collections.abc import Sequence

from alembic import op

revision: str = "250d0d8058ef"
down_revision: str | Sequence[str] | None = "86f9c1691f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Secure the property-tools table."""

    op.execute(
        """
        ALTER TABLE public.property_tools
        ALTER COLUMN id
        SET DEFAULT gen_random_uuid()
        """
    )

    op.execute(
        """
        ALTER TABLE public.property_tools
        ENABLE ROW LEVEL SECURITY
        """
    )


def downgrade() -> None:
    """Reverse property-tools security changes."""

    op.execute(
        """
        ALTER TABLE public.property_tools
        ALTER COLUMN id
        DROP DEFAULT
        """
    )

    op.execute(
        """
        ALTER TABLE public.property_tools
        DISABLE ROW LEVEL SECURITY
        """
    )
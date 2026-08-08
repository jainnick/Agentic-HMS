"""secure property tools

Revision ID: 250d0d8058ef
Revises: 86f9c1691f20
Create Date: 2026-08-09 01:28:29.606989

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '250d0d8058ef'
down_revision: Union[str, Sequence[str], None] = '86f9c1691f20'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
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


def downgrade() -> None:
    """Downgrade schema."""
    pass

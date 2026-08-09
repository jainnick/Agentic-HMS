"""secure property tools

Revision ID: 250d0d8058ef
Revises: 86f9c1691f20
Create Date: 2026-08-09 01:28:29.606989
"""

from collections.abc import Sequence

revision: str = "250d0d8058ef"
down_revision: str | Sequence[str] | None = "86f9c1691f20"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """No-op revision.

    The property_tools ID default and RLS configuration are already
    defined in revision 86f9c1691f20.
    """
    pass


def downgrade() -> None:
    """No-op downgrade."""
    pass

"""initialize backend foundation

Revision ID: cdff641a8945
Revises:
Create Date: 2026-07-23 13:01:36.414808

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "cdff641a8945"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    pass


def downgrade() -> None:
    """Downgrade schema."""
    pass

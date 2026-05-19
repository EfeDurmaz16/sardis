"""spending state persistence

Revision ID: 009
Revises: 008
Create Date: 2026-02-13 00:00:00.000000
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "009"
down_revision: str | None = "008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("009_spending_state_persistence.sql")


def downgrade() -> None:
    # No rollback SQL for this migration.
    pass

"""canonical ledger state machine and reconciliation ops tables

Revision ID: 019
Revises: 018
Create Date: 2026-02-16 00:00:00.000000
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "019"
down_revision: str | None = "018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("019_canonical_ledger_state.sql")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS manual_review_queue CASCADE")
    op.execute("DROP TABLE IF EXISTS reconciliation_breaks CASCADE")
    op.execute("DROP TABLE IF EXISTS canonical_ledger_events CASCADE")
    op.execute("DROP TABLE IF EXISTS canonical_ledger_journeys CASCADE")


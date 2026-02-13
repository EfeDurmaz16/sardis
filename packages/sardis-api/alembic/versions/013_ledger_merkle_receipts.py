"""ledger merkle receipts

Revision ID: 013
Revises: 012
Create Date: 2026-02-13 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("013_ledger_merkle_receipts.sql")


def downgrade() -> None:
    # No rollback SQL for this migration.
    pass

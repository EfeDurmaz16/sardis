"""024_secure_checkout_jobs.sql migration wrapper

Revision ID: 024
Revises: 023
Create Date: 2026-02-25 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "024"
down_revision: Union[str, None] = "023"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("024_secure_checkout_jobs.sql")


def downgrade() -> None:
    # Reverse operations are managed via dedicated SQL rollback strategy where applicable.
    pass

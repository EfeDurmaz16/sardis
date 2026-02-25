"""025_issuer_funding_attempts.sql migration wrapper

Revision ID: 025
Revises: 024
Create Date: 2026-02-25 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "025"
down_revision: Union[str, None] = "024"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("025_issuer_funding_attempts.sql")


def downgrade() -> None:
    # Reverse operations are managed via dedicated SQL rollback strategy where applicable.
    pass

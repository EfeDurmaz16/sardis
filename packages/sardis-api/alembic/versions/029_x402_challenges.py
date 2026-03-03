"""029_x402_challenges.sql migration wrapper

Revision ID: 029
Revises: 028
Create Date: 2026-03-03 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "029"
down_revision: Union[str, None] = "028"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("029_x402_challenges.sql")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_x402_challenges_expires;")
    op.execute("DROP INDEX IF EXISTS idx_x402_challenges_wallet;")
    op.execute("DROP TABLE IF EXISTS x402_challenges;")

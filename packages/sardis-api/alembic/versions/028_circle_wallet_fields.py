"""028_circle_wallet_fields.sql migration wrapper

Revision ID: 028
Revises: 027
Create Date: 2026-03-02 00:00:00.000000
"""

from collections.abc import Sequence
from pathlib import Path

from alembic import op

revision: str = "028"
down_revision: str | None = "027"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("028_circle_wallet_fields.sql")


def downgrade() -> None:
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS circle_wallet_id;")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS kya_attestation_uid;")
    op.execute("DROP INDEX IF EXISTS idx_wallets_circle_id;")
    op.execute("DROP INDEX IF EXISTS idx_wallets_kya_uid;")

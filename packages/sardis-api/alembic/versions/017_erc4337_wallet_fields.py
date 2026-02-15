"""erc4337 wallet metadata fields

Revision ID: 017
Revises: 016
Create Date: 2026-02-15 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("017_erc4337_wallet_fields.sql")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_wallets_smart_account")
    op.execute("DROP INDEX IF EXISTS idx_wallets_account_type")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS bundler_profile")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS paymaster_enabled")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS entrypoint_address")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS smart_account_address")
    op.execute("ALTER TABLE wallets DROP COLUMN IF EXISTS account_type")

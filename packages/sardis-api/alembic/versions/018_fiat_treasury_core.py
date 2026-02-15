"""fiat treasury core tables

Revision ID: 018
Revises: 017
Create Date: 2026-02-15 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "018"
down_revision: Union[str, None] = "017"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("018_fiat_treasury_core.sql")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS treasury_webhook_events CASCADE")
    op.execute("DROP TABLE IF EXISTS treasury_reservations CASCADE")
    op.execute("DROP TABLE IF EXISTS treasury_balance_snapshots CASCADE")
    op.execute("DROP TABLE IF EXISTS ach_payment_events CASCADE")
    op.execute("DROP TABLE IF EXISTS ach_payments CASCADE")
    op.execute("DROP TABLE IF EXISTS external_bank_accounts CASCADE")
    op.execute("DROP TABLE IF EXISTS lithic_financial_accounts CASCADE")


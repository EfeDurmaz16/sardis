"""card and ledger persistence

Revision ID: 015
Revises: 014
Create Date: 2026-02-15 00:00:00.000000

Adds tables for:
- card_conversions: Auto USDC<->USD conversion records
- card_wallet_mappings: Card-to-wallet mapping for auto-conversion
- offramp_transactions: USDC->USD off-ramp transaction records
- processed_webhook_events: Webhook deduplication
- ledger_entries_v2: Full-precision append-only ledger (38,18 decimals)
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("015_card_and_ledger_persistence.sql")
    op.execute(
        """
        INSERT INTO schema_migrations (version, description)
        VALUES ('015', 'Card persistence and ledger v2 tables')
        ON CONFLICT (version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS ledger_entries_v2 CASCADE")
    op.execute("DROP TABLE IF EXISTS processed_webhook_events CASCADE")
    op.execute("DROP TABLE IF EXISTS offramp_transactions CASCADE")
    op.execute("DROP TABLE IF EXISTS card_wallet_mappings CASCADE")
    op.execute("DROP TABLE IF EXISTS card_conversions CASCADE")

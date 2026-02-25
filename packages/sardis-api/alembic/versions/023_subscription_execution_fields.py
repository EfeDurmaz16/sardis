"""subscription execution fields

Revision ID: 023
Revises: 022
Create Date: 2026-02-26 00:00:00.000000
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op


revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("023_subscription_execution_fields.sql")
    op.execute(
        """
        INSERT INTO schema_migrations (version, description)
        VALUES ('023', 'Subscription execution fields')
        ON CONFLICT (version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_subscriptions_chain_status")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS last_autofund_at")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS autofund_amount_cents")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS autofund_enabled")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS memo")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS chain")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS token")
    op.execute("ALTER TABLE subscriptions DROP COLUMN IF EXISTS destination_address")


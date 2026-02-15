"""recurring payments subscriptions

Revision ID: 016
Revises: 015
Create Date: 2026-02-15 00:00:00.000000

Adds tables for:
- subscriptions: Recurring payment registry
- billing_events: Per-cycle billing execution records
- subscription_notifications: Owner notification queue
"""

from pathlib import Path
from typing import Sequence, Union

from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _run_sql_file(filename: str) -> None:
    migration_path = Path(__file__).resolve().parents[2] / "migrations" / filename
    op.execute(migration_path.read_text(encoding="utf-8"))


def upgrade() -> None:
    _run_sql_file("016_subscriptions.sql")
    op.execute(
        """
        INSERT INTO schema_migrations (version, description)
        VALUES ('016', 'Recurring payments subscriptions')
        ON CONFLICT (version) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS subscription_notifications CASCADE")
    op.execute("DROP TABLE IF EXISTS billing_events CASCADE")
    op.execute("DROP TABLE IF EXISTS subscriptions CASCADE")

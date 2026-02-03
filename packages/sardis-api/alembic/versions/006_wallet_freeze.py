"""wallet freeze

Revision ID: 006
Revises: 005
Create Date: 2024-01-06 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '006'
down_revision: Union[str, None] = '005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add freeze columns to wallets table
    op.add_column('wallets', sa.Column('is_frozen', sa.Boolean, nullable=False, server_default='false'))
    op.add_column('wallets', sa.Column('frozen_at', sa.TIMESTAMP(timezone=True)))
    op.add_column('wallets', sa.Column('frozen_by', sa.String(255)))
    op.add_column('wallets', sa.Column('freeze_reason', sa.Text))

    # Create indexes for frozen wallets
    op.create_index('idx_wallets_is_frozen', 'wallets', ['is_frozen'], postgresql_where=sa.text('is_frozen = TRUE'))
    op.create_index('idx_wallets_frozen_at', 'wallets', [sa.text('frozen_at DESC')], postgresql_where=sa.text('frozen_at IS NOT NULL'))

    # Add column comments
    op.execute("COMMENT ON COLUMN wallets.is_frozen IS 'Whether wallet is frozen (blocks all transactions). Set via freeze/unfreeze endpoints.'")
    op.execute("COMMENT ON COLUMN wallets.frozen_at IS 'Timestamp when wallet was frozen. NULL if wallet is not frozen or has been unfrozen.'")
    op.execute("COMMENT ON COLUMN wallets.frozen_by IS 'Admin email, system identifier, or compliance rule that froze the wallet.'")
    op.execute("COMMENT ON COLUMN wallets.freeze_reason IS 'Human-readable reason for freezing: compliance violation, suspicious activity, manual freeze, etc.'")

    # Record migration
    op.execute("INSERT INTO schema_migrations (version, description) VALUES ('006', 'Add wallet freeze columns for compliance blocking') ON CONFLICT (version) DO NOTHING")


def downgrade() -> None:
    op.drop_index('idx_wallets_frozen_at', table_name='wallets')
    op.drop_index('idx_wallets_is_frozen', table_name='wallets')
    op.drop_column('wallets', 'freeze_reason')
    op.drop_column('wallets', 'frozen_by')
    op.drop_column('wallets', 'frozen_at')
    op.drop_column('wallets', 'is_frozen')

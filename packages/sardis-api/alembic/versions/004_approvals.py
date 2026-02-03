"""approvals

Revision ID: 004
Revises: 003
Create Date: 2024-01-04 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '004'
down_revision: Union[str, None] = '003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute("CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'denied', 'expired', 'cancelled')")
    op.execute("CREATE TYPE approval_urgency AS ENUM ('low', 'medium', 'high')")

    # Create approvals table
    op.create_table(
        'approvals',
        sa.Column('id', sa.String(64), primary_key=True),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('vendor', sa.String(255)),
        sa.Column('amount', sa.Numeric(18, 6)),
        sa.Column('purpose', sa.Text),
        sa.Column('reason', sa.Text),
        sa.Column('card_limit', sa.Numeric(18, 6)),
        sa.Column('status', postgresql.ENUM('pending', 'approved', 'denied', 'expired', 'cancelled', name='approval_status'), nullable=False, server_default='pending'),
        sa.Column('urgency', postgresql.ENUM('low', 'medium', 'high', name='approval_urgency'), nullable=False, server_default='medium'),
        sa.Column('requested_by', sa.String(64), nullable=False),
        sa.Column('reviewed_by', sa.String(255)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('reviewed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('agent_id', sa.String(64)),
        sa.Column('wallet_id', sa.String(64)),
        sa.Column('organization_id', sa.String(64)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
    )

    # Create indexes
    op.create_index('idx_approvals_status', 'approvals', ['status'])
    op.create_index('idx_approvals_agent_id', 'approvals', ['agent_id'])
    op.create_index('idx_approvals_wallet_id', 'approvals', ['wallet_id'])
    op.create_index('idx_approvals_organization_id', 'approvals', ['organization_id'])
    op.create_index('idx_approvals_requested_by', 'approvals', ['requested_by'])
    op.create_index('idx_approvals_expires_at', 'approvals', ['expires_at'], postgresql_where=sa.text("status = 'pending'"))
    op.create_index('idx_approvals_created_at', 'approvals', [sa.text('created_at DESC')])
    op.create_index('idx_approvals_status_urgency', 'approvals', ['status', 'urgency'], postgresql_where=sa.text("status = 'pending'"))

    # Add comments
    op.execute("COMMENT ON TABLE approvals IS 'Human approval requests for agent actions exceeding policy limits'")
    op.execute("COMMENT ON COLUMN approvals.id IS 'Unique approval ID, format: appr_<base36_timestamp>'")
    op.execute("COMMENT ON COLUMN approvals.action IS 'Type of action: payment, create_card, transfer, etc.'")
    op.execute("COMMENT ON COLUMN approvals.requested_by IS 'Agent ID that initiated the approval request'")
    op.execute("COMMENT ON COLUMN approvals.reviewed_by IS 'Human reviewer email or admin ID'")


def downgrade() -> None:
    op.drop_table('approvals')
    op.execute('DROP TYPE approval_urgency')
    op.execute('DROP TYPE approval_status')

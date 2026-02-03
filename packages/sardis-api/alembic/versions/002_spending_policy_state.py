"""spending policy state

Revision ID: 002
Revises: 001
Create Date: 2024-01-02 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add spent_total to spending_policies for lifetime limit tracking
    op.add_column('spending_policies',
        sa.Column('spent_total', sa.Numeric(20, 6), server_default='0', nullable=False))

    # Add currency to time_window_limits for multi-token support
    op.add_column('time_window_limits',
        sa.Column('currency', sa.String(10), server_default='USDC', nullable=False))

    # Create index for fast policy lookups by agent
    op.create_index('idx_spending_policies_agent', 'spending_policies', ['agent_id'])


def downgrade() -> None:
    op.drop_index('idx_spending_policies_agent', table_name='spending_policies')
    op.drop_column('time_window_limits', 'currency')
    op.drop_column('spending_policies', 'spent_total')

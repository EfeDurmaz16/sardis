"""ledger compliance tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Ledger: Receipts
    op.create_table(
        'receipts',
        sa.Column('tx_id', sa.String(128), primary_key=True),
        sa.Column('tx_hash', sa.String(128)),
        sa.Column('chain', sa.String(32)),
        sa.Column('block_number', sa.BigInteger),
        sa.Column('status', sa.String(32)),
        sa.Column('audit_anchor', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_receipts_created', 'receipts', ['created_at'])
    op.create_index('idx_receipts_tx_hash', 'receipts', ['tx_hash'])

    # Ledger: Metadata
    op.create_table(
        'ledger_meta',
        sa.Column('key', sa.String(128), primary_key=True),
        sa.Column('value', sa.Text, nullable=False),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Ledger: Balance Snapshots
    op.create_table(
        'balance_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('account_id', sa.String(128), nullable=False),
        sa.Column('currency', sa.String(16), nullable=False),
        sa.Column('balance', sa.Numeric(20, 6), nullable=False),
        sa.Column('snapshot_at', sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text('NOW()')),
        sa.Column('entry_count', sa.BigInteger, server_default='0'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
    )
    op.create_index('idx_snapshots_account', 'balance_snapshots', ['account_id', 'currency'])
    op.create_index('idx_snapshots_time', 'balance_snapshots', ['snapshot_at'])

    # Ledger: Pending Reconciliation
    op.create_table(
        'pending_reconciliation',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('mandate_id', sa.String(128), nullable=False),
        sa.Column('expected_amount', sa.Numeric(20, 6)),
        sa.Column('actual_amount', sa.Numeric(20, 6)),
        sa.Column('discrepancy_type', sa.String(64)),
        sa.Column('priority', sa.Integer, server_default='0'),
        sa.Column('resolved', sa.Boolean, server_default='false'),
        sa.Column('resolution_notes', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('resolved_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('idx_reconciliation_resolved', 'pending_reconciliation', ['resolved'])
    op.create_index('idx_reconciliation_mandate', 'pending_reconciliation', ['mandate_id'])
    op.create_index('idx_reconciliation_priority', 'pending_reconciliation', ['priority', 'created_at'])

    # Ledger: Audit Logs (ledger-specific)
    op.create_table(
        'audit_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('entity_type', sa.String(64), nullable=False),
        sa.Column('entity_id', sa.String(128), nullable=False),
        sa.Column('action', sa.String(64), nullable=False),
        sa.Column('actor', sa.String(128)),
        sa.Column('details', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_audit_entity', 'audit_logs', ['entity_type', 'entity_id'])
    op.create_index('idx_audit_created', 'audit_logs', ['created_at'])

    # Ledger: Row Locks
    op.create_table(
        'row_locks',
        sa.Column('lock_key', sa.String(128), primary_key=True),
        sa.Column('locked_by', sa.String(128)),
        sa.Column('locked_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Compliance: Audit Trail
    op.create_table(
        'compliance_audit_trail',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('mandate_id', sa.String(128), nullable=False),
        sa.Column('subject', sa.String(128), nullable=False),
        sa.Column('decision', sa.String(32), nullable=False),
        sa.Column('reason', sa.Text),
        sa.Column('rule_id', sa.String(64)),
        sa.Column('risk_score', sa.Numeric(5, 2)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('evaluated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_audit_mandate_id', 'compliance_audit_trail', ['mandate_id'])
    op.create_index('idx_audit_subject', 'compliance_audit_trail', ['subject'])
    op.create_index('idx_audit_evaluated_at', 'compliance_audit_trail', ['evaluated_at'])

    # Protocol: Mandate Chains
    op.create_table(
        'mandate_chains',
        sa.Column('chain_id', sa.String(128), primary_key=True),
        sa.Column('mandate_id', sa.String(128), nullable=False),
        sa.Column('chain_data', postgresql.JSONB, nullable=False),
        sa.Column('verified', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Virtual Cards
    op.create_table(
        'virtual_cards',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('wallet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wallets.id')),
        sa.Column('provider', sa.String(32), nullable=False, server_default='lithic'),
        sa.Column('provider_card_id', sa.String(128)),
        sa.Column('card_number_last4', sa.String(4)),
        sa.Column('status', sa.String(32), server_default='active'),
        sa.Column('spending_limit', sa.Numeric(20, 6)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_virtual_cards_wallet', 'virtual_cards', ['wallet_id'])
    op.create_index('idx_virtual_cards_provider', 'virtual_cards', ['provider', 'provider_card_id'])
    op.create_index('idx_virtual_cards_status', 'virtual_cards', ['status'])

    # Card Transactions
    op.create_table(
        'card_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('card_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('virtual_cards.id')),
        sa.Column('provider_tx_id', sa.String(128)),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('currency', sa.String(16), server_default='USD'),
        sa.Column('merchant_name', sa.String(255)),
        sa.Column('merchant_category', sa.String(64)),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_card_tx_card', 'card_transactions', ['card_id'])
    op.create_index('idx_card_tx_status', 'card_transactions', ['status'])
    op.create_index('idx_card_tx_created', 'card_transactions', [sa.text('created_at DESC')])
    op.create_index('idx_card_tx_provider', 'card_transactions', ['provider_tx_id'])

    # KYC Verifications
    op.create_table(
        'kyc_verifications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id')),
        sa.Column('inquiry_id', sa.String(128)),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('provider', sa.String(32), server_default='persona'),
        sa.Column('risk_level', sa.String(32)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_kyc_agent', 'kyc_verifications', ['agent_id'])
    op.create_index('idx_kyc_inquiry', 'kyc_verifications', ['inquiry_id'])

    # Invoices
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id')),
        sa.Column('invoice_number', sa.String(64), unique=True),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('currency', sa.String(16), server_default='USD'),
        sa.Column('status', sa.String(32), server_default='draft'),
        sa.Column('due_date', sa.TIMESTAMP(timezone=True)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_invoices_org', 'invoices', ['organization_id'])
    op.create_index('idx_invoices_status', 'invoices', ['status'])

    # Checkouts
    op.create_table(
        'checkouts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id')),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('currency', sa.String(16), server_default='USD'),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('payment_method', sa.String(32)),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('idx_checkouts_org', 'checkouts', ['organization_id'])
    op.create_index('idx_checkouts_status', 'checkouts', ['status'])

    # Marketplace Services
    op.create_table(
        'marketplace_services',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('category', sa.String(64)),
        sa.Column('price', sa.Numeric(20, 6)),
        sa.Column('currency', sa.String(16), server_default='USD'),
        sa.Column('status', sa.String(32), server_default='active'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_marketplace_services_provider', 'marketplace_services', ['provider_agent_id'])
    op.create_index('idx_marketplace_services_category', 'marketplace_services', ['category'])
    op.create_index('idx_marketplace_services_status', 'marketplace_services', ['status'])

    # Marketplace Offers
    op.create_table(
        'marketplace_offers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('marketplace_services.id')),
        sa.Column('provider_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id')),
        sa.Column('consumer_agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id')),
        sa.Column('amount', sa.Numeric(20, 6)),
        sa.Column('currency', sa.String(16), server_default='USD'),
        sa.Column('status', sa.String(32), server_default='pending'),
        sa.Column('metadata', postgresql.JSONB, server_default='{}'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_marketplace_offers_service', 'marketplace_offers', ['service_id'])
    op.create_index('idx_marketplace_offers_provider', 'marketplace_offers', ['provider_agent_id'])
    op.create_index('idx_marketplace_offers_consumer', 'marketplace_offers', ['consumer_agent_id'])
    op.create_index('idx_marketplace_offers_status', 'marketplace_offers', ['status'])

    # Marketplace Reviews
    op.create_table(
        'marketplace_reviews',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('service_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('marketplace_services.id')),
        sa.Column('offer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('marketplace_offers.id')),
        sa.Column('rating', sa.Integer, sa.CheckConstraint('rating >= 1 AND rating <= 5')),
        sa.Column('review_text', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_marketplace_reviews_service', 'marketplace_reviews', ['service_id'])
    op.create_index('idx_marketplace_reviews_offer', 'marketplace_reviews', ['offer_id'])

    # Record migration
    op.execute("INSERT INTO schema_migrations (version, description) VALUES ('003', 'Add ledger receipts, compliance audit trail, and supporting tables') ON CONFLICT (version) DO NOTHING")


def downgrade() -> None:
    op.drop_table('marketplace_reviews')
    op.drop_table('marketplace_offers')
    op.drop_table('marketplace_services')
    op.drop_table('checkouts')
    op.drop_table('invoices')
    op.drop_table('kyc_verifications')
    op.drop_table('card_transactions')
    op.drop_table('virtual_cards')
    op.drop_table('mandate_chains')
    op.drop_table('compliance_audit_trail')
    op.drop_table('row_locks')
    op.drop_table('audit_logs')
    op.drop_table('pending_reconciliation')
    op.drop_table('balance_snapshots')
    op.drop_table('ledger_meta')
    op.drop_table('receipts')

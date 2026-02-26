"""initial schema

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable UUID extension
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # Organizations
    op.create_table(
        'organizations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('settings', postgresql.JSONB, server_default='{}'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Agents
    op.create_table(
        'agents',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id')),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('public_key', sa.LargeBinary),
        sa.Column('key_algorithm', sa.String(20), server_default='ed25519'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_agents_org', 'agents', ['organization_id'])
    op.create_index('idx_agents_active', 'agents', ['is_active'], postgresql_where=sa.text('is_active = TRUE'))

    # Wallets
    op.create_table(
        'wallets',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), nullable=False),
        sa.Column('chain_address', sa.String(66)),
        sa.Column('chain', sa.String(20), server_default='base'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_wallets_agent', 'wallets', ['agent_id'])
    op.create_index('idx_wallets_chain', 'wallets', ['chain', 'chain_address'])

    # Token Balances
    op.create_table(
        'token_balances',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('wallet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wallets.id'), nullable=False),
        sa.Column('token', sa.String(10), nullable=False),
        sa.Column('balance', sa.Numeric(20, 6), server_default='0'),
        sa.Column('spent_total', sa.Numeric(20, 6), server_default='0'),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('wallet_id', 'token'),
    )
    op.create_index('idx_balances_wallet', 'token_balances', ['wallet_id'])

    # Spending Policies
    op.create_table(
        'spending_policies',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('agent_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('agents.id'), unique=True, nullable=False),
        sa.Column('trust_level', sa.String(20), server_default='low'),
        sa.Column('limit_per_tx', sa.Numeric(20, 6), server_default='100'),
        sa.Column('limit_total', sa.Numeric(20, 6), server_default='1000'),
        sa.Column('require_preauth', sa.Boolean, server_default='false'),
        sa.Column('allowed_scopes', postgresql.ARRAY(sa.String), server_default="ARRAY['all']"),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Time Window Limits
    op.create_table(
        'time_window_limits',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('spending_policies.id'), nullable=False),
        sa.Column('window_type', sa.String(20), nullable=False),
        sa.Column('limit_amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('current_spent', sa.Numeric(20, 6), server_default='0'),
        sa.Column('window_start', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.UniqueConstraint('policy_id', 'window_type'),
    )

    # Merchant Rules
    op.create_table(
        'merchant_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('policy_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('spending_policies.id'), nullable=False),
        sa.Column('rule_type', sa.String(10), nullable=False),
        sa.Column('merchant_id', sa.String(64)),
        sa.Column('category', sa.String(50)),
        sa.Column('max_per_tx', sa.Numeric(20, 6)),
        sa.Column('daily_limit', sa.Numeric(20, 6)),
        sa.Column('reason', sa.Text),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_merchant_rules_policy', 'merchant_rules', ['policy_id'])
    op.create_index('idx_merchant_rules_merchant', 'merchant_rules', ['merchant_id'])

    # Transactions
    op.create_table(
        'transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('from_wallet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wallets.id')),
        sa.Column('to_wallet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wallets.id')),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('fee', sa.Numeric(20, 6), server_default='0'),
        sa.Column('token', sa.String(10), nullable=False),
        sa.Column('purpose', sa.Text),
        sa.Column('status', sa.String(20), nullable=False),
        sa.Column('error_message', sa.Text),
        sa.Column('idempotency_key', sa.String(64)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('completed_at', sa.TIMESTAMP(timezone=True)),
    )
    op.create_index('idx_tx_from', 'transactions', ['from_wallet_id'])
    op.create_index('idx_tx_to', 'transactions', ['to_wallet_id'])
    op.create_index('idx_tx_status', 'transactions', ['status'])
    op.create_index('idx_tx_created', 'transactions', [sa.text('created_at DESC')])
    op.create_index('idx_tx_status_created', 'transactions', ['status', sa.text('created_at DESC')])
    op.create_index('idx_tx_idempotency', 'transactions', ['idempotency_key'], postgresql_where=sa.text('idempotency_key IS NOT NULL'))

    # On-Chain Records
    op.create_table(
        'on_chain_records',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id'), nullable=False),
        sa.Column('chain', sa.String(20), nullable=False),
        sa.Column('tx_hash', sa.String(66), nullable=False),
        sa.Column('block_number', sa.BigInteger),
        sa.Column('from_address', sa.String(66)),
        sa.Column('to_address', sa.String(66)),
        sa.Column('status', sa.String(20), server_default='pending'),
        sa.Column('confirmed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_chain_records_tx', 'on_chain_records', ['transaction_id'])
    op.create_index('idx_chain_records_hash', 'on_chain_records', ['chain', 'tx_hash'])

    # Holds
    op.create_table(
        'holds',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('wallet_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('wallets.id'), nullable=False),
        sa.Column('merchant_id', sa.String(64)),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('token', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), server_default='active'),
        sa.Column('purpose', sa.Text),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('captured_amount', sa.Numeric(20, 6)),
        sa.Column('captured_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('capture_tx_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id')),
        sa.Column('voided_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_holds_wallet', 'holds', ['wallet_id'])
    op.create_index('idx_holds_status', 'holds', ['status'])
    op.create_index('idx_holds_capture_tx', 'holds', ['capture_tx_id'])

    # Mandates
    op.create_table(
        'mandates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('mandate_id', sa.String(64), unique=True, nullable=False),
        sa.Column('mandate_type', sa.String(20), nullable=False),
        sa.Column('issuer', sa.String(255), nullable=False),
        sa.Column('subject', sa.String(255), nullable=False),
        sa.Column('domain', sa.String(255)),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('proof', postgresql.JSONB),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('verified_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('executed_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('transaction_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('transactions.id')),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_mandates_subject', 'mandates', ['subject'])
    op.create_index('idx_mandates_type', 'mandates', ['mandate_type'])
    op.create_index('idx_mandates_tx', 'mandates', ['transaction_id'])

    # Replay Cache
    op.create_table(
        'replay_cache',
        sa.Column('mandate_id', sa.String(64), primary_key=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=False),
    )
    op.create_index('idx_replay_expires', 'replay_cache', ['expires_at'])

    # Ledger Entries
    op.create_table(
        'ledger_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tx_id', sa.String(64), unique=True, nullable=False),
        sa.Column('mandate_id', sa.String(64)),
        sa.Column('from_wallet', sa.String(255)),
        sa.Column('to_wallet', sa.String(255)),
        sa.Column('amount', sa.Numeric(20, 6), nullable=False),
        sa.Column('currency', sa.String(10), nullable=False),
        sa.Column('chain', sa.String(20)),
        sa.Column('chain_tx_hash', sa.String(66)),
        sa.Column('audit_anchor', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_ledger_created', 'ledger_entries', [sa.text('created_at DESC')])
    op.create_index('idx_ledger_from', 'ledger_entries', ['from_wallet'])
    op.create_index('idx_ledger_to', 'ledger_entries', ['to_wallet'])

    # Webhook Subscriptions
    op.create_table(
        'webhook_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('organization_id', sa.String(64), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('secret', sa.String(64), nullable=False),
        sa.Column('events', postgresql.ARRAY(sa.String), server_default="ARRAY[]::VARCHAR[]"),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('total_deliveries', sa.Integer, server_default='0'),
        sa.Column('successful_deliveries', sa.Integer, server_default='0'),
        sa.Column('failed_deliveries', sa.Integer, server_default='0'),
        sa.Column('last_delivery_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_webhook_subs_org', 'webhook_subscriptions', ['organization_id'])
    op.create_index('idx_webhook_subs_active', 'webhook_subscriptions', ['is_active'], postgresql_where=sa.text('is_active = TRUE'))

    # Webhook Deliveries
    op.create_table(
        'webhook_deliveries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('external_id', sa.String(64), unique=True, nullable=False),
        sa.Column('subscription_id', sa.String(64), nullable=False),
        sa.Column('event_id', sa.String(64), nullable=False),
        sa.Column('event_type', sa.String(50), nullable=False),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('status_code', sa.Integer),
        sa.Column('response_body', sa.Text),
        sa.Column('error', sa.Text),
        sa.Column('duration_ms', sa.Integer, server_default='0'),
        sa.Column('success', sa.Boolean, server_default='false'),
        sa.Column('attempt_number', sa.Integer, server_default='1'),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_deliveries_subscription', 'webhook_deliveries', ['subscription_id'])
    op.create_index('idx_deliveries_event', 'webhook_deliveries', ['event_id'])
    op.create_index('idx_deliveries_created', 'webhook_deliveries', [sa.text('created_at DESC')])

    # API Keys
    op.create_table(
        'api_keys',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('key_prefix', sa.String(12), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False),
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('organizations.id'), nullable=False),
        sa.Column('name', sa.String(255)),
        sa.Column('scopes', postgresql.ARRAY(sa.String), server_default="ARRAY['read']"),
        sa.Column('rate_limit', sa.Integer, server_default='100'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('last_used_at', sa.TIMESTAMP(timezone=True)),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_api_keys_prefix', 'api_keys', ['key_prefix'])
    op.create_index('idx_api_keys_org', 'api_keys', ['organization_id'])

    # Audit Log
    op.create_table(
        'audit_log',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text('gen_random_uuid()')),
        sa.Column('actor_type', sa.String(20), nullable=False),
        sa.Column('actor_id', sa.String(64), nullable=False),
        sa.Column('action', sa.String(50), nullable=False),
        sa.Column('resource_type', sa.String(50), nullable=False),
        sa.Column('resource_id', sa.String(64), nullable=False),
        sa.Column('changes', postgresql.JSONB),
        sa.Column('ip_address', postgresql.INET),
        sa.Column('user_agent', sa.Text),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )
    op.create_index('idx_audit_actor', 'audit_log', ['actor_type', 'actor_id'])
    op.create_index('idx_audit_resource', 'audit_log', ['resource_type', 'resource_id'])
    op.create_index('idx_audit_created', 'audit_log', [sa.text('created_at DESC')])

    # Schema Migrations
    op.create_table(
        'schema_migrations',
        sa.Column('version', sa.String(20), primary_key=True),
        sa.Column('applied_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('NOW()')),
    )

    # Record migration
    op.execute("INSERT INTO schema_migrations (version) VALUES ('001_initial_schema') ON CONFLICT (version) DO NOTHING")


def downgrade() -> None:
    op.drop_table('schema_migrations')
    op.drop_table('audit_log')
    op.drop_table('api_keys')
    op.drop_table('webhook_deliveries')
    op.drop_table('webhook_subscriptions')
    op.drop_table('ledger_entries')
    op.drop_table('replay_cache')
    op.drop_table('mandates')
    op.drop_table('holds')
    op.drop_table('on_chain_records')
    op.drop_table('transactions')
    op.drop_table('merchant_rules')
    op.drop_table('time_window_limits')
    op.drop_table('spending_policies')
    op.drop_table('token_balances')
    op.drop_table('wallets')
    op.drop_table('agents')
    op.drop_table('organizations')

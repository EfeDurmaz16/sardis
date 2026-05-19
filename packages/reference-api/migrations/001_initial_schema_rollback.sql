-- =============================================================================
-- Sardis Migration Rollback: 001_initial_schema
-- =============================================================================
--
-- WARNING: This will DROP all tables and data!
-- Only use for development or if you need to completely reset the database.
--
-- Apply: psql $DATABASE_URL -f migrations/001_initial_schema_rollback.sql
--
-- =============================================================================

-- Drop indexes first
DROP INDEX IF EXISTS idx_audit_created;
DROP INDEX IF EXISTS idx_audit_resource;
DROP INDEX IF EXISTS idx_audit_actor;
DROP INDEX IF EXISTS idx_api_keys_org;
DROP INDEX IF EXISTS idx_api_keys_prefix;
DROP INDEX IF EXISTS idx_deliveries_created;
DROP INDEX IF EXISTS idx_deliveries_event;
DROP INDEX IF EXISTS idx_deliveries_subscription;
DROP INDEX IF EXISTS idx_webhook_subs_active;
DROP INDEX IF EXISTS idx_webhook_subs_org;
DROP INDEX IF EXISTS idx_ledger_to;
DROP INDEX IF EXISTS idx_ledger_from;
DROP INDEX IF EXISTS idx_ledger_created;
DROP INDEX IF EXISTS idx_replay_expires;
DROP INDEX IF EXISTS idx_mandates_type;
DROP INDEX IF EXISTS idx_mandates_subject;
DROP INDEX IF EXISTS idx_holds_status;
DROP INDEX IF EXISTS idx_holds_wallet;
DROP INDEX IF EXISTS idx_chain_records_hash;
DROP INDEX IF EXISTS idx_chain_records_tx;
DROP INDEX IF EXISTS idx_tx_idempotency;
DROP INDEX IF EXISTS idx_tx_created;
DROP INDEX IF EXISTS idx_tx_status;
DROP INDEX IF EXISTS idx_tx_to;
DROP INDEX IF EXISTS idx_tx_from;
DROP INDEX IF EXISTS idx_merchant_rules_merchant;
DROP INDEX IF EXISTS idx_merchant_rules_policy;
DROP INDEX IF EXISTS idx_balances_wallet;
DROP INDEX IF EXISTS idx_wallets_chain;
DROP INDEX IF EXISTS idx_wallets_agent;
DROP INDEX IF EXISTS idx_agents_active;
DROP INDEX IF EXISTS idx_agents_org;

-- Drop tables in reverse dependency order
DROP TABLE IF EXISTS audit_log CASCADE;
DROP TABLE IF EXISTS api_keys CASCADE;
DROP TABLE IF EXISTS webhook_deliveries CASCADE;
DROP TABLE IF EXISTS webhook_subscriptions CASCADE;
DROP TABLE IF EXISTS ledger_entries CASCADE;
DROP TABLE IF EXISTS replay_cache CASCADE;
DROP TABLE IF EXISTS mandate_chains CASCADE;
DROP TABLE IF EXISTS mandates CASCADE;
DROP TABLE IF EXISTS holds CASCADE;
DROP TABLE IF EXISTS on_chain_records CASCADE;
DROP TABLE IF EXISTS transactions CASCADE;
DROP TABLE IF EXISTS merchant_rules CASCADE;
DROP TABLE IF EXISTS time_window_limits CASCADE;
DROP TABLE IF EXISTS spending_policies CASCADE;
DROP TABLE IF EXISTS token_balances CASCADE;
DROP TABLE IF EXISTS wallets CASCADE;
DROP TABLE IF EXISTS agents CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Remove migration record
DELETE FROM schema_migrations WHERE version = '001_initial_schema';

-- Note: We don't drop schema_migrations table itself to preserve other migration history

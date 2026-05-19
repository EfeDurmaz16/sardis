-- =============================================================================
-- Sardis Migration: 005_audit_triggers
-- =============================================================================
--
-- Adds audit triggers for critical tables to automatically log all changes
-- to transactions, wallets, and approvals tables into the audit_logs table.
--
-- Apply: psql $DATABASE_URL -f migrations/005_audit_triggers.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('005', 'Add audit triggers for transactions/wallets/approvals')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Generic Audit Trigger Function
-- -----------------------------------------------------------------------------
-- This function captures INSERT, UPDATE, DELETE operations and logs them
-- to the audit_logs table with full before/after state.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION audit_trigger_func()
RETURNS TRIGGER AS $$
DECLARE
    entity_id_value TEXT;
    old_data JSONB;
    new_data JSONB;
    actor_value TEXT;
BEGIN
    -- Determine entity ID based on table structure
    IF TG_TABLE_NAME = 'transactions' THEN
        entity_id_value := COALESCE(NEW.id::TEXT, OLD.id::TEXT);
    ELSIF TG_TABLE_NAME = 'wallets' THEN
        entity_id_value := COALESCE(NEW.external_id, OLD.external_id);
    ELSIF TG_TABLE_NAME = 'approvals' THEN
        entity_id_value := COALESCE(NEW.id, OLD.id);
    ELSE
        entity_id_value := COALESCE(NEW.id::TEXT, OLD.id::TEXT);
    END IF;

    -- Extract actor information from context or data
    IF TG_OP = 'DELETE' THEN
        actor_value := COALESCE(
            current_setting('app.current_user', TRUE),
            'system'
        );
    ELSE
        actor_value := COALESCE(
            current_setting('app.current_user', TRUE),
            NEW.updated_by,
            'system'
        );
    END IF;

    -- Build old/new data payloads
    IF TG_OP = 'DELETE' THEN
        old_data := to_jsonb(OLD);
        new_data := NULL;
    ELSIF TG_OP = 'UPDATE' THEN
        old_data := to_jsonb(OLD);
        new_data := to_jsonb(NEW);
    ELSIF TG_OP = 'INSERT' THEN
        old_data := NULL;
        new_data := to_jsonb(NEW);
    END IF;

    -- Insert audit log entry
    INSERT INTO audit_logs (
        entity_type,
        entity_id,
        action,
        actor,
        details,
        created_at
    ) VALUES (
        TG_TABLE_NAME,
        entity_id_value,
        TG_OP,
        actor_value,
        jsonb_build_object(
            'operation', TG_OP,
            'table', TG_TABLE_NAME,
            'old_data', old_data,
            'new_data', new_data,
            'changed_fields', CASE
                WHEN TG_OP = 'UPDATE' THEN (
                    SELECT jsonb_object_agg(key, value)
                    FROM jsonb_each(new_data)
                    WHERE new_data->key IS DISTINCT FROM old_data->key
                )
                ELSE NULL
            END
        ),
        NOW()
    );

    -- Return appropriate value for trigger chain
    IF TG_OP = 'DELETE' THEN
        RETURN OLD;
    ELSE
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Audit Trigger: Transactions
-- -----------------------------------------------------------------------------
-- Logs all changes to the transactions table (INSERT, UPDATE, DELETE)
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS audit_transactions_trigger ON transactions;

CREATE TRIGGER audit_transactions_trigger
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

COMMENT ON TRIGGER audit_transactions_trigger ON transactions IS
    'Audit trigger that logs all transaction changes to audit_logs table';

-- -----------------------------------------------------------------------------
-- Audit Trigger: Wallets
-- -----------------------------------------------------------------------------
-- Logs all changes to the wallets table, including freeze/unfreeze operations
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS audit_wallets_trigger ON wallets;

CREATE TRIGGER audit_wallets_trigger
    AFTER INSERT OR UPDATE OR DELETE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

COMMENT ON TRIGGER audit_wallets_trigger ON wallets IS
    'Audit trigger that logs all wallet changes to audit_logs table';

-- -----------------------------------------------------------------------------
-- Audit Trigger: Approvals
-- -----------------------------------------------------------------------------
-- Logs all changes to the approvals table (create, approve, deny, expire)
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS audit_approvals_trigger ON approvals;

CREATE TRIGGER audit_approvals_trigger
    AFTER INSERT OR UPDATE OR DELETE ON approvals
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

COMMENT ON TRIGGER audit_approvals_trigger ON approvals IS
    'Audit trigger that logs all approval changes to audit_logs table';

-- -----------------------------------------------------------------------------
-- Audit Trigger: Token Balances
-- -----------------------------------------------------------------------------
-- Logs balance changes for fraud detection and reconciliation
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS audit_token_balances_trigger ON token_balances;

CREATE TRIGGER audit_token_balances_trigger
    AFTER INSERT OR UPDATE OR DELETE ON token_balances
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

COMMENT ON TRIGGER audit_token_balances_trigger ON token_balances IS
    'Audit trigger that logs all balance changes to audit_logs table';

-- -----------------------------------------------------------------------------
-- Audit Trigger: Spending Policies
-- -----------------------------------------------------------------------------
-- Logs policy changes for compliance and security audits
-- -----------------------------------------------------------------------------

DROP TRIGGER IF EXISTS audit_spending_policies_trigger ON spending_policies;

CREATE TRIGGER audit_spending_policies_trigger
    AFTER INSERT OR UPDATE OR DELETE ON spending_policies
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func();

COMMENT ON TRIGGER audit_spending_policies_trigger ON spending_policies IS
    'Audit trigger that logs all policy changes to audit_logs table';

-- -----------------------------------------------------------------------------
-- Indexes for Audit Log Queries
-- -----------------------------------------------------------------------------

-- These indexes are already in 003_ledger_compliance_tables.sql:
-- CREATE INDEX IF NOT EXISTS idx_audit_entity ON audit_logs(entity_type, entity_id);
-- CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);

-- Add additional composite index for actor-based queries
CREATE INDEX IF NOT EXISTS idx_audit_actor_created ON audit_logs(actor, created_at DESC);

-- Index for operation-based queries (e.g., all UPDATEs)
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_logs(action);

COMMENT ON INDEX idx_audit_actor_created IS 'Index for querying audit logs by actor and time';
COMMENT ON INDEX idx_audit_action IS 'Index for querying audit logs by operation type (INSERT/UPDATE/DELETE)';

-- -----------------------------------------------------------------------------
-- Usage Examples (for documentation)
-- -----------------------------------------------------------------------------

-- Query all changes to a specific transaction:
-- SELECT * FROM audit_logs WHERE entity_type = 'transactions' AND entity_id = 'tx_123' ORDER BY created_at;

-- Query all wallet freeze operations:
-- SELECT * FROM audit_logs WHERE entity_type = 'wallets' AND details->'changed_fields'->>'is_frozen' = 'true';

-- Query all approval status changes:
-- SELECT * FROM audit_logs WHERE entity_type = 'approvals' AND details->'changed_fields' ? 'status';

-- Find who modified a specific record:
-- SELECT actor, action, created_at, details FROM audit_logs WHERE entity_type = 'wallets' AND entity_id = 'wallet_xyz';

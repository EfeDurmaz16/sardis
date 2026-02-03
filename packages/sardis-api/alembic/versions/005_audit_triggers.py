"""audit triggers

Revision ID: 005
Revises: 004
Create Date: 2024-01-05 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '005'
down_revision: Union[str, None] = '004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create generic audit trigger function
    op.execute("""
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
    """)

    # Create audit trigger for transactions
    op.execute("DROP TRIGGER IF EXISTS audit_transactions_trigger ON transactions")
    op.execute("""
CREATE TRIGGER audit_transactions_trigger
    AFTER INSERT OR UPDATE OR DELETE ON transactions
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func()
    """)
    op.execute("COMMENT ON TRIGGER audit_transactions_trigger ON transactions IS 'Audit trigger that logs all transaction changes to audit_logs table'")

    # Create audit trigger for wallets
    op.execute("DROP TRIGGER IF EXISTS audit_wallets_trigger ON wallets")
    op.execute("""
CREATE TRIGGER audit_wallets_trigger
    AFTER INSERT OR UPDATE OR DELETE ON wallets
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func()
    """)
    op.execute("COMMENT ON TRIGGER audit_wallets_trigger ON wallets IS 'Audit trigger that logs all wallet changes to audit_logs table'")

    # Create audit trigger for approvals
    op.execute("DROP TRIGGER IF EXISTS audit_approvals_trigger ON approvals")
    op.execute("""
CREATE TRIGGER audit_approvals_trigger
    AFTER INSERT OR UPDATE OR DELETE ON approvals
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func()
    """)
    op.execute("COMMENT ON TRIGGER audit_approvals_trigger ON approvals IS 'Audit trigger that logs all approval changes to audit_logs table'")

    # Create audit trigger for token balances
    op.execute("DROP TRIGGER IF EXISTS audit_token_balances_trigger ON token_balances")
    op.execute("""
CREATE TRIGGER audit_token_balances_trigger
    AFTER INSERT OR UPDATE OR DELETE ON token_balances
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func()
    """)
    op.execute("COMMENT ON TRIGGER audit_token_balances_trigger ON token_balances IS 'Audit trigger that logs all balance changes to audit_logs table'")

    # Create audit trigger for spending policies
    op.execute("DROP TRIGGER IF EXISTS audit_spending_policies_trigger ON spending_policies")
    op.execute("""
CREATE TRIGGER audit_spending_policies_trigger
    AFTER INSERT OR UPDATE OR DELETE ON spending_policies
    FOR EACH ROW
    EXECUTE FUNCTION audit_trigger_func()
    """)
    op.execute("COMMENT ON TRIGGER audit_spending_policies_trigger ON spending_policies IS 'Audit trigger that logs all policy changes to audit_logs table'")

    # Create additional indexes
    op.create_index('idx_audit_actor_created', 'audit_logs', ['actor', 'created_at'])
    op.create_index('idx_audit_action', 'audit_logs', ['action'])

    op.execute("COMMENT ON INDEX idx_audit_actor_created IS 'Index for querying audit logs by actor and time'")
    op.execute("COMMENT ON INDEX idx_audit_action IS 'Index for querying audit logs by operation type (INSERT/UPDATE/DELETE)'")

    # Record migration
    op.execute("INSERT INTO schema_migrations (version, description) VALUES ('005', 'Add audit triggers for transactions/wallets/approvals') ON CONFLICT (version) DO NOTHING")


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_spending_policies_trigger ON spending_policies")
    op.execute("DROP TRIGGER IF EXISTS audit_token_balances_trigger ON token_balances")
    op.execute("DROP TRIGGER IF EXISTS audit_approvals_trigger ON approvals")
    op.execute("DROP TRIGGER IF EXISTS audit_wallets_trigger ON wallets")
    op.execute("DROP TRIGGER IF EXISTS audit_transactions_trigger ON transactions")
    op.execute("DROP FUNCTION IF EXISTS audit_trigger_func()")
    op.drop_index('idx_audit_action', table_name='audit_logs')
    op.drop_index('idx_audit_actor_created', table_name='audit_logs')

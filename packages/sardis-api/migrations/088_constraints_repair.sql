-- Migration 088: Repair idempotency partial index, add FK constraints
-- Fixes several constraint issues identified in schema audit.

-- ============================================================================
-- 1. Fix useless partial index on idempotency_records
-- The existing index has WHERE expires_at < now() which is evaluated at
-- CREATE INDEX time and becomes a static constant, making it useless for
-- ongoing cleanup queries. Replace with a plain index on expires_at.
-- ============================================================================
DROP INDEX IF EXISTS idx_idempotency_expires;
CREATE INDEX IF NOT EXISTS idx_idempotency_expires
    ON idempotency_records(expires_at);

-- ============================================================================
-- 2. Add UNIQUE constraint on transactions.idempotency_key
-- Prevents duplicate payments at the DB level. DEFERRABLE so that
-- application code can set the key before committing.
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'uq_transactions_idempotency_key'
    ) THEN
        ALTER TABLE transactions
            ADD CONSTRAINT uq_transactions_idempotency_key
            UNIQUE (idempotency_key)
            DEFERRABLE INITIALLY DEFERRED;
    END IF;
END $$;

-- ============================================================================
-- 3. Add FK on email_verification_tokens.user_id -> users(id) ON DELETE CASCADE
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_email_verification_user'
    ) THEN
        ALTER TABLE email_verification_tokens
            ADD CONSTRAINT fk_email_verification_user
            FOREIGN KEY (user_id) REFERENCES users(id)
            ON DELETE CASCADE;
    END IF;
END $$;

-- ============================================================================
-- 4. Add FK on funding_cells.owner_mandate_id -> spending_mandates(id)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_funding_cells_mandate'
    ) THEN
        ALTER TABLE funding_cells
            ADD CONSTRAINT fk_funding_cells_mandate
            FOREIGN KEY (owner_mandate_id) REFERENCES spending_mandates(id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- ============================================================================
-- 5. Add FK on funding_cells.payment_object_id -> payment_objects(object_id)
-- ============================================================================
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'fk_funding_cells_payment_object'
    ) THEN
        ALTER TABLE funding_cells
            ADD CONSTRAINT fk_funding_cells_payment_object
            FOREIGN KEY (payment_object_id) REFERENCES payment_objects(object_id)
            ON DELETE SET NULL;
    END IF;
END $$;

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('088_constraints_repair', 'Repair idempotency partial index, add FK constraints on email_verification and funding_cells')
ON CONFLICT DO NOTHING;

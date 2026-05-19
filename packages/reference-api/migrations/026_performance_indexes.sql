-- =============================================================================
-- Sardis Migration: 026_performance_indexes
-- =============================================================================
--
-- Adds performance indexes for high-volume read paths and FK lookups.
--
-- Apply: psql $DATABASE_URL -f migrations/026_performance_indexes.sql
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_tx_status_created
    ON transactions(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_holds_capture_tx
    ON holds(capture_tx_id);

CREATE INDEX IF NOT EXISTS idx_mandates_tx
    ON mandates(transaction_id);

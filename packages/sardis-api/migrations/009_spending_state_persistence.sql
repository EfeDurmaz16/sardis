-- =============================================================================
-- Sardis Migration: 009_spending_state_persistence
-- =============================================================================
--
-- Adds velocity tracking and ensures atomic spending enforcement.
--
-- SECURITY: Without velocity tracking, agents can fire rapid small transactions
-- that individually pass limits but collectively exceed intended spending.
--
-- NOTE: spending_policies + time_window_limits tables already exist from the
-- base schema + migration 002. This migration adds the missing velocity layer.
--
-- Apply: psql $DATABASE_URL -f migrations/009_spending_state_persistence.sql
--
-- =============================================================================

-- Guard: record migration
INSERT INTO schema_migrations (version, description)
VALUES ('009', 'Velocity tracking and atomic spending enforcement')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Velocity tracking: per-policy transaction count within time windows
-- Prevents rapid-fire small transactions that individually pass limits
-- -----------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS spending_velocity (
    id              BIGSERIAL PRIMARY KEY,
    policy_id       UUID NOT NULL,
    tx_timestamp    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    amount          NUMERIC(20,6) NOT NULL,
    merchant_id     TEXT,

    CONSTRAINT fk_velocity_policy
        FOREIGN KEY (policy_id) REFERENCES spending_policies(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_velocity_policy_time
    ON spending_velocity(policy_id, tx_timestamp DESC);

-- Auto-cleanup: remove velocity records older than 24 hours
-- (run via pg_cron or application-level scheduled task)
-- DELETE FROM spending_velocity WHERE tx_timestamp < NOW() - INTERVAL '24 hours';

-- -----------------------------------------------------------------------------
-- Helper function: atomic spend recording with window reset
-- Returns TRUE if spend was allowed and recorded, FALSE if limit exceeded.
-- Uses SELECT ... FOR UPDATE for race-condition safety.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION record_spend(
    p_policy_id UUID,
    p_amount NUMERIC,
    p_merchant_id TEXT DEFAULT NULL
) RETURNS TABLE(allowed BOOLEAN, reason TEXT) AS $$
DECLARE
    v_policy spending_policies%ROWTYPE;
    v_window time_window_limits%ROWTYPE;
    v_now TIMESTAMPTZ := NOW();
    v_duration INTERVAL;
BEGIN
    -- Lock the spending policy row
    SELECT * INTO v_policy
    FROM spending_policies
    WHERE id = p_policy_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN QUERY SELECT FALSE, 'policy_not_found'::TEXT;
        RETURN;
    END IF;

    -- Check per-transaction limit
    IF p_amount > v_policy.limit_per_tx THEN
        RETURN QUERY SELECT FALSE, 'per_transaction_limit'::TEXT;
        RETURN;
    END IF;

    -- Check total limit
    IF v_policy.spent_total + p_amount > v_policy.limit_total THEN
        RETURN QUERY SELECT FALSE, 'total_limit_exceeded'::TEXT;
        RETURN;
    END IF;

    -- Check each time window
    FOR v_window IN
        SELECT * FROM time_window_limits tw
        WHERE tw.policy_id = p_policy_id
        FOR UPDATE
    LOOP
        -- Determine window duration
        v_duration := CASE v_window.window_type
            WHEN 'daily' THEN INTERVAL '1 day'
            WHEN 'weekly' THEN INTERVAL '7 days'
            WHEN 'monthly' THEN INTERVAL '30 days'
        END;

        -- Reset window if expired
        IF v_now >= v_window.window_start + v_duration THEN
            UPDATE time_window_limits
            SET current_spent = 0,
                window_start = v_now
            WHERE id = v_window.id;
            v_window.current_spent := 0;
        END IF;

        -- Check window limit
        IF v_window.current_spent + p_amount > v_window.limit_amount THEN
            RETURN QUERY SELECT FALSE, (v_window.window_type || '_limit_exceeded')::TEXT;
            RETURN;
        END IF;
    END LOOP;

    -- All checks passed — record the spend atomically
    UPDATE spending_policies
    SET spent_total = spent_total + p_amount,
        updated_at = v_now
    WHERE id = p_policy_id;

    UPDATE time_window_limits
    SET current_spent = current_spent + p_amount
    WHERE time_window_limits.policy_id = p_policy_id;

    -- Record velocity entry
    INSERT INTO spending_velocity (policy_id, tx_timestamp, amount, merchant_id)
    VALUES (p_policy_id, v_now, p_amount, p_merchant_id);

    RETURN QUERY SELECT TRUE, 'OK'::TEXT;
END;
$$ LANGUAGE plpgsql;

-- -----------------------------------------------------------------------------
-- Helper function: check velocity limits (tx count within time windows)
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION check_velocity(
    p_policy_id UUID,
    p_max_per_minute INTEGER DEFAULT 5,
    p_max_per_hour INTEGER DEFAULT 60
) RETURNS TABLE(allowed BOOLEAN, reason TEXT) AS $$
DECLARE
    v_count_minute INTEGER;
    v_count_hour INTEGER;
BEGIN
    SELECT COUNT(*) INTO v_count_minute
    FROM spending_velocity
    WHERE policy_id = p_policy_id
      AND tx_timestamp > NOW() - INTERVAL '1 minute';

    IF v_count_minute >= p_max_per_minute THEN
        RETURN QUERY SELECT FALSE, 'velocity_limit_per_minute'::TEXT;
        RETURN;
    END IF;

    SELECT COUNT(*) INTO v_count_hour
    FROM spending_velocity
    WHERE policy_id = p_policy_id
      AND tx_timestamp > NOW() - INTERVAL '1 hour';

    IF v_count_hour >= p_max_per_hour THEN
        RETURN QUERY SELECT FALSE, 'velocity_limit_per_hour'::TEXT;
        RETURN;
    END IF;

    RETURN QUERY SELECT TRUE, 'OK'::TEXT;
END;
$$ LANGUAGE plpgsql;

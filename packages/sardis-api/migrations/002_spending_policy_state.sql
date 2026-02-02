-- Migration 002: Add persistent spending policy state tracking
-- Required for atomic enforcement of spending limits across multiple instances

-- Add spent_total to spending_policies for lifetime limit tracking
ALTER TABLE spending_policies
    ADD COLUMN IF NOT EXISTS spent_total NUMERIC(20,6) DEFAULT 0 NOT NULL;

-- Add currency to time_window_limits for multi-token support
ALTER TABLE time_window_limits
    ADD COLUMN IF NOT EXISTS currency VARCHAR(10) DEFAULT 'USDC' NOT NULL;

-- Create index for fast policy lookups by agent
CREATE INDEX IF NOT EXISTS idx_spending_policies_agent ON spending_policies(agent_id);

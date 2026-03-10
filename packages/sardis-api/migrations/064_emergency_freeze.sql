-- Emergency freeze events audit table for incident response
CREATE TABLE IF NOT EXISTS emergency_freeze_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action TEXT NOT NULL,  -- 'freeze_all' | 'unfreeze_all'
    triggered_by TEXT NOT NULL,
    wallets_affected INTEGER NOT NULL,
    reason TEXT,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_emergency_freeze_events_created
    ON emergency_freeze_events (created_at DESC);

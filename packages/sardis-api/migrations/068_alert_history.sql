-- Migration 068: Persist alert history to PostgreSQL
-- Adds alert_history table for durable storage of dispatched alerts

CREATE TABLE IF NOT EXISTS alert_history (
    id TEXT PRIMARY KEY,
    alert_type TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    agent_id TEXT,
    org_id TEXT,
    data JSONB DEFAULT '{}',
    channels_delivered TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alert_history_org ON alert_history(org_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_alert_history_type ON alert_history(alert_type);
CREATE INDEX IF NOT EXISTS idx_alert_history_severity ON alert_history(severity);

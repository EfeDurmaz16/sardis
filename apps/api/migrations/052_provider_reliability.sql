-- Migration 052: Provider reliability tracking
-- Records RPC/chain provider health events and computed scorecards.

CREATE TABLE IF NOT EXISTS provider_health_events (
    event_id        TEXT PRIMARY KEY,
    provider        TEXT NOT NULL,
    chain           TEXT NOT NULL,
    event_type      TEXT NOT NULL,       -- 'rpc_call', 'tx_submission', 'tx_confirmation'
    success         BOOLEAN NOT NULL,
    latency_ms      INT,
    error_type      TEXT,                -- 'timeout', 'rate_limit', '5xx', 'revert'
    gas_used        BIGINT,
    gas_price_gwei  REAL,
    recorded_at     TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_provider_events_provider ON provider_health_events(provider, chain);
CREATE INDEX IF NOT EXISTS idx_provider_events_time ON provider_health_events(recorded_at);

CREATE TABLE IF NOT EXISTS provider_scorecards (
    provider        TEXT NOT NULL,
    chain           TEXT NOT NULL,
    period          TEXT NOT NULL,        -- '1h', '24h', '7d'
    total_calls     INT DEFAULT 0,
    success_count   INT DEFAULT 0,
    failure_count   INT DEFAULT 0,
    avg_latency_ms  REAL,
    p95_latency_ms  REAL,
    error_rate      REAL DEFAULT 0,
    availability    REAL DEFAULT 1.0,
    computed_at     TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (provider, chain, period)
);

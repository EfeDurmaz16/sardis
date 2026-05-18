-- Migration 093: API activity log for agent sync (Layer 1)
-- Append-only table for fire-and-forget activity logging.
-- No FKs for write performance.

CREATE TABLE IF NOT EXISTS api_activity_log (
    id              BIGSERIAL PRIMARY KEY,
    org_id          VARCHAR(64)  NOT NULL,
    principal_kind  VARCHAR(16),              -- 'api_key' | 'jwt'
    actor_id        VARCHAR(64),              -- user or key id
    agent_id        VARCHAR(64),              -- from X-Sardis-Agent-Id header
    session_id      VARCHAR(64),              -- from X-Sardis-Session-Id header
    method          VARCHAR(10)  NOT NULL,    -- GET, POST, etc.
    path            VARCHAR(512) NOT NULL,
    status_code     SMALLINT     NOT NULL,
    latency_ms      INTEGER,
    wallet_id       VARCHAR(64),
    request_id      VARCHAR(64),
    ip              INET,
    user_agent      VARCHAR(512),
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT now()
);

-- Query patterns: recent activity by org, by agent, by session
CREATE INDEX IF NOT EXISTS idx_api_activity_log_org_created
    ON api_activity_log (org_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_api_activity_log_agent_created
    ON api_activity_log (agent_id, created_at DESC)
    WHERE agent_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_api_activity_log_session_created
    ON api_activity_log (session_id, created_at DESC)
    WHERE session_id IS NOT NULL;

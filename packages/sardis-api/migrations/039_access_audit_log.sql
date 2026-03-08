-- Access audit log for SOC 2 compliance.
-- Records all authentication events, admin actions, and API access.

CREATE TABLE IF NOT EXISTS access_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    event_type      TEXT NOT NULL,              -- 'auth_success', 'auth_failure', 'admin_action', 'api_access'
    user_id         TEXT,
    org_id          TEXT,
    ip_address      TEXT,
    user_agent      TEXT,
    endpoint        TEXT,
    method          TEXT,
    status_code     INT,
    auth_method     TEXT,                       -- 'api_key', 'jwt', 'anonymous'
    details         JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON access_audit_log (created_at);
CREATE INDEX IF NOT EXISTS idx_audit_log_user_id ON access_audit_log (user_id) WHERE user_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON access_audit_log (event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_org_id ON access_audit_log (org_id) WHERE org_id IS NOT NULL;

-- Retention: keep for 1 year
-- DELETE FROM access_audit_log WHERE created_at < now() - interval '1 year';

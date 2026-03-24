-- Notification configuration and delivery tracking.
--
-- Orgs configure webhook URLs + event type filters.
-- Delivery log tracks every attempt for debugging and unhealthy-webhook detection.

CREATE TABLE IF NOT EXISTS notification_configs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id TEXT NOT NULL,
    webhook_url TEXT NOT NULL,
    event_types TEXT[] DEFAULT '{}',
    provider TEXT DEFAULT 'slack',
    is_active BOOLEAN DEFAULT true,
    consecutive_failures INT DEFAULT 0,
    last_failure_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_configs_org ON notification_configs(org_id);

-- Delivery log for debugging and dedup
CREATE TABLE IF NOT EXISTS notification_delivery_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    config_id UUID NOT NULL REFERENCES notification_configs(id),
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}',
    status_code INT,
    error TEXT,
    attempt_number INT DEFAULT 1,
    success BOOLEAN DEFAULT false,
    duration_ms INT DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_notification_delivery_config ON notification_delivery_log(config_id);
CREATE INDEX IF NOT EXISTS idx_notification_delivery_created ON notification_delivery_log(created_at);

INSERT INTO schema_migrations (version, name, applied_at)
VALUES (89, '089_notification_configs', now())
ON CONFLICT (version) DO NOTHING;

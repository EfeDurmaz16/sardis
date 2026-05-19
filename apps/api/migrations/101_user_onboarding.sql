-- 101_user_onboarding.sql
--
-- Per-user onboarding wizard state. Tracks where each org is in the
-- multi-step first-run onboarding flow so the dashboard can resume
-- mid-flow on subsequent logins.
--
-- Keyed by organizations.external_id (the same org_id slug carried in
-- ba_user.org_id and exposed via Principal.organization_id) so the
-- backend handlers can look up state directly from the request
-- principal without an extra ba_user join.
--
-- Steps (canonical order, mirrored in TypeScript):
--   profile, api_key, kyc, agent_wallet, spending_policy,
--   sandbox_payment, tour_ready
--
-- A row exists for an org from the first time they hit the wizard.
-- `current_step` is whichever step the user is currently on (or the
-- last incomplete one). `completed_at` is set when the user reaches
-- the terminal `tour_ready` state. `metadata` carries per-step bits
-- like which steps were skipped.

BEGIN;

CREATE TABLE IF NOT EXISTS user_onboarding (
  org_id          TEXT PRIMARY KEY
                    REFERENCES organizations (external_id)
                    ON DELETE CASCADE
                    ON UPDATE CASCADE,
  current_step    TEXT NOT NULL DEFAULT 'profile',
  completed_at    TIMESTAMPTZ,
  metadata        JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_onboarding_completed_at
  ON user_onboarding (completed_at);

COMMENT ON TABLE user_onboarding IS
  'Per-org onboarding wizard state. One row per organization, populated on first wizard load.';

COMMENT ON COLUMN user_onboarding.current_step IS
  'Current/last-incomplete step. One of: profile, api_key, kyc, agent_wallet, spending_policy, sandbox_payment, tour_ready.';

COMMENT ON COLUMN user_onboarding.metadata IS
  'JSON bag for per-step state. Conventionally contains a "skipped" array of step ids and arbitrary per-step payloads.';

COMMIT;

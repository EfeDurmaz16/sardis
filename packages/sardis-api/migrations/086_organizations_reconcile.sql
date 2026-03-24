-- Migration 086: Reconcile duplicate organizations schema
-- Migration 001 creates organizations with UUID id and minimal columns.
-- Migration 022 tries to CREATE TABLE IF NOT EXISTS with TEXT id (skipped
-- because the table already exists). Code in organizations.py router and
-- OrganizationManager queries slug, plan, billing_email, stripe_customer_id,
-- subscription_status, and metadata which don't exist on the 001 schema.
-- Fix: add the missing columns so both old and new schemas converge.

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS slug TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS plan TEXT DEFAULT 'free';
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS billing_email TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS subscription_status TEXT;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;

-- Create indexes if they don't exist (022 creates these but only if the
-- table was freshly created there, which doesn't happen on existing DBs)
CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);
CREATE INDEX IF NOT EXISTS idx_organizations_plan ON organizations(plan);

-- Create a unique index on slug where not null (slug may be null for
-- orgs created before this migration)
CREATE UNIQUE INDEX IF NOT EXISTS idx_organizations_slug_unique
    ON organizations(slug) WHERE slug IS NOT NULL;

-- Track migration
INSERT INTO schema_migrations (version, description)
VALUES ('086_organizations_reconcile', 'Reconcile duplicate organizations schema — add missing columns from 022')
ON CONFLICT DO NOTHING;

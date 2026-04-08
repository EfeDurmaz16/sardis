-- 100_ba_user_org_consistency.sql
--
-- Guarantees that every ba_user.org_id has a matching row in the
-- organizations table. Closes the ghost-organization hole discovered
-- on 2026-04-08 where users could end up with a dangling org_id if
-- the application-layer databaseHooks.user.create.after hook failed
-- or was skipped.
--
-- Two layers of defense:
--
--   1. BEFORE INSERT trigger on ba_user — auto-creates the matching
--      organizations row inside the same transaction as the ba_user
--      insert. Idempotent via ON CONFLICT DO NOTHING. Runs before the
--      FK check below, so the FK never fires for auto-created orgs.
--
--   2. Foreign key constraint ba_user.org_id -> organizations.external_id
--      (NOT VALID so it never fails on the existing data, but enforced
--      for every future insert/update). Effectively: "the DB refuses
--      to let ba_user.org_id diverge from organizations.external_id."
--
-- Historical data (pre-trigger) was cleaned up separately in the
-- 2026-04-08 ghost org cleanup. This migration is additive and safe
-- to run against a clean database.

BEGIN;

-- ─── 1. Trigger function: auto-provision organization from ba_user row
CREATE OR REPLACE FUNCTION ba_user_ensure_organization()
RETURNS TRIGGER AS $$
BEGIN
  -- Only act if org_id is set. Rows without org_id are a separate
  -- problem (caught by a CHECK constraint in a future migration).
  IF NEW.org_id IS NOT NULL AND NEW.org_id <> '' THEN
    INSERT INTO organizations (
      external_id,
      name,
      plan,
      billing_email,
      is_active,
      created_at,
      updated_at
    )
    VALUES (
      NEW.org_id,
      COALESCE(NULLIF(NEW.display_name, ''), NULLIF(NEW.name, ''), NEW.email, 'New User'),
      'free',
      NEW.email,
      TRUE,
      NOW(),
      NOW()
    )
    ON CONFLICT (external_id) DO NOTHING;
  END IF;

  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION ba_user_ensure_organization() IS
  'Auto-provisions an organizations row matching ba_user.org_id. Closes the ghost-org race where the app-layer databaseHooks hook could fail and leave a dangling FK.';

-- Drop any prior version of the trigger so this migration is idempotent
DROP TRIGGER IF EXISTS ba_user_ensure_organization_trigger ON ba_user;

CREATE TRIGGER ba_user_ensure_organization_trigger
  BEFORE INSERT OR UPDATE OF org_id ON ba_user
  FOR EACH ROW
  EXECUTE FUNCTION ba_user_ensure_organization();

-- ─── 2. Foreign key ba_user.org_id -> organizations.external_id
--     NOT VALID so existing rows are not re-checked (should all be
--     valid after the 2026-04-08 cleanup, but NOT VALID is cheap
--     insurance against any row I missed). Future inserts + updates
--     are enforced. ON DELETE SET NULL so deleting an organization
--     does not cascade-delete user accounts.
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.table_constraints
    WHERE constraint_name = 'ba_user_org_id_fk'
      AND table_name = 'ba_user'
  ) THEN
    ALTER TABLE ba_user
      ADD CONSTRAINT ba_user_org_id_fk
      FOREIGN KEY (org_id)
      REFERENCES organizations (external_id)
      ON DELETE SET NULL
      ON UPDATE CASCADE
      NOT VALID;
  END IF;
END$$;

-- Validate the constraint against existing data. Safe because the
-- 2026-04-08 cleanup already fixed every broken FK. If this fails,
-- there is fresh drift and the migration should stop.
ALTER TABLE ba_user VALIDATE CONSTRAINT ba_user_org_id_fk;

COMMIT;

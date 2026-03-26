-- Migration 090: Fix kyc_verifications for dashboard user compatibility
--
-- The kyc_verifications table was originally designed for AI agents (UUID agent_id
-- referencing agents(id)).  Dashboard users authenticate with text IDs (usr_xxx)
-- from the users table.  This migration:
--
-- 1. Changes agent_id from UUID to TEXT so it can hold both agent UUIDs and user IDs
-- 2. Drops the FK constraint to agents(id) since it now holds heterogeneous IDs
-- 3. Adds missing columns (verified_at, expires_at) that the KYC router expects
-- 4. Adds a kyc_status column to the users table for direct status lookups

-- Step 1: Drop FK constraint on agent_id (if it exists)
ALTER TABLE kyc_verifications DROP CONSTRAINT IF EXISTS kyc_verifications_agent_id_fkey;

-- Step 2: Change agent_id from UUID to TEXT
ALTER TABLE kyc_verifications ALTER COLUMN agent_id TYPE TEXT USING agent_id::TEXT;

-- Step 3: Allow NULL agent_id (webhook may not have user context initially)
ALTER TABLE kyc_verifications ALTER COLUMN agent_id DROP NOT NULL;

-- Step 4: Add missing columns that the KYC router already references
ALTER TABLE kyc_verifications ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ;
ALTER TABLE kyc_verifications ADD COLUMN IF NOT EXISTS expires_at TIMESTAMPTZ;
ALTER TABLE kyc_verifications ADD COLUMN IF NOT EXISTS reason TEXT;

-- Step 5: Add kyc_status to users table for direct lookups
ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_status TEXT NOT NULL DEFAULT 'not_started';

-- Step 6: Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_kyc_verifications_agent_id_text ON kyc_verifications(agent_id);
CREATE INDEX IF NOT EXISTS idx_users_kyc_status ON users(kyc_status) WHERE kyc_status != 'not_started';

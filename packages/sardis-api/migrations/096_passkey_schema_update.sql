-- Migration: passkey schema update for better-auth passkey plugin
-- Adds aaguid column and fixes device_type constraint

-- Add aaguid column (authenticator attestation GUID)
ALTER TABLE ba_passkey ADD COLUMN IF NOT EXISTS aaguid TEXT;

-- Set default for device_type on existing rows before adding NOT NULL
UPDATE ba_passkey SET device_type = 'singleDevice' WHERE device_type IS NULL;

-- Make device_type NOT NULL with default
ALTER TABLE ba_passkey ALTER COLUMN device_type SET DEFAULT 'singleDevice';
ALTER TABLE ba_passkey ALTER COLUMN device_type SET NOT NULL;

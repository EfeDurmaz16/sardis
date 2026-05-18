-- Migration 099: Add columns for new better-auth plugins
-- Phone number plugin: phoneNumber + phoneNumberVerified on ba_user
-- Stripe plugin: stripeCustomerId on ba_user

-- Phone number fields
ALTER TABLE ba_user ADD COLUMN IF NOT EXISTS phone_number TEXT UNIQUE;
ALTER TABLE ba_user ADD COLUMN IF NOT EXISTS phone_number_verified BOOLEAN NOT NULL DEFAULT FALSE;

-- Stripe customer ID (for @better-auth/stripe plugin)
ALTER TABLE ba_user ADD COLUMN IF NOT EXISTS stripe_customer_id TEXT;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_ba_user_phone_number ON ba_user(phone_number) WHERE phone_number IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_ba_user_stripe_customer_id ON ba_user(stripe_customer_id) WHERE stripe_customer_id IS NOT NULL;

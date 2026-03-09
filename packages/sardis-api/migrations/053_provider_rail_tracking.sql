-- Migration 053: Provider rail tracking for multi-provider payment execution
-- Adds columns to track which provider rail processed each transaction

ALTER TABLE transactions ADD COLUMN IF NOT EXISTS provider_rail VARCHAR(50);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS provider_payment_reference VARCHAR(255);

CREATE INDEX IF NOT EXISTS idx_transactions_provider
    ON transactions(provider_rail, created_at);

COMMENT ON COLUMN transactions.provider_rail IS 'Payment provider rail used: stripe_spt, visa_tap, mastercard_agent_pay, circle_cpn, bridge_ach, bridge_sepa, bridge_pix';
COMMENT ON COLUMN transactions.provider_payment_reference IS 'Provider-specific payment reference ID (e.g., Stripe pi_xxx, Visa auth_xxx)';

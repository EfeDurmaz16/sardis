-- Multi-currency balance tracking and conversion records
ALTER TABLE wallets ADD COLUMN IF NOT EXISTS eur_balance_cents BIGINT DEFAULT 0;
ALTER TABLE wallets ADD COLUMN IF NOT EXISTS eurc_balance_minor BIGINT DEFAULT 0;

-- Add currency column to conversion records if table exists
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'conversion_records') THEN
        ALTER TABLE conversion_records ADD COLUMN IF NOT EXISTS currency TEXT DEFAULT 'USD';
    END IF;
END $$;

-- Conversion records table (if not exists)
CREATE TABLE IF NOT EXISTS conversion_records (
    id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
    wallet_id TEXT NOT NULL,
    direction TEXT NOT NULL, -- usdc_to_usd, eurc_to_eur, usdc_to_eur, eurc_to_usd
    input_amount_minor BIGINT NOT NULL,
    output_amount_cents BIGINT NOT NULL,
    exchange_rate NUMERIC(20,8) DEFAULT 1.0,
    fee_cents INTEGER DEFAULT 0,
    currency TEXT DEFAULT 'USD',
    status TEXT DEFAULT 'pending',
    trigger_type TEXT DEFAULT 'card_payment',
    provider_tx_id TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_conversion_records_wallet ON conversion_records(wallet_id);
CREATE INDEX IF NOT EXISTS idx_conversion_records_status ON conversion_records(status);

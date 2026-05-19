-- Migration 074: Tempo chain support fields
-- Adds Tempo-specific fields to transactions for TIP-20 stablecoin gas model

-- Add memo field for TIP-20 transferWithMemo support
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS memo TEXT;

-- Fee token tracking (which stablecoin was used for gas on Tempo)
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fee_token VARCHAR(20);
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS fee_token_amount BIGINT;

-- Flag for TIP-20 vs ERC-20 transfer type
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS tip20_transfer BOOLEAN DEFAULT FALSE;

-- Settlement method tracking
ALTER TABLE merchant_checkout_sessions ADD COLUMN IF NOT EXISTS settlement_method VARCHAR(50);

-- Index for Tempo transaction queries
CREATE INDEX IF NOT EXISTS idx_transactions_tip20
    ON transactions (tip20_transfer) WHERE tip20_transfer = TRUE;

COMMENT ON COLUMN transactions.memo IS 'TIP-20 transferWithMemo bytes32 memo (e.g. Sardis payment ID)';
COMMENT ON COLUMN transactions.fee_token IS 'Stablecoin used for gas on Tempo (e.g. USDC, pathUSD)';
COMMENT ON COLUMN transactions.fee_token_amount IS 'Gas fee paid in stablecoin minor units';
COMMENT ON COLUMN transactions.tip20_transfer IS 'True if payment used TIP-20 transferWithMemo on Tempo';

-- Persist x402 payment challenges for multi-instance verification flow.

CREATE TABLE IF NOT EXISTS x402_challenges (
    payment_id TEXT PRIMARY KEY,
    wallet_id TEXT NOT NULL,
    challenge JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_x402_challenges_wallet ON x402_challenges(wallet_id);
CREATE INDEX IF NOT EXISTS idx_x402_challenges_expires ON x402_challenges(expires_at);

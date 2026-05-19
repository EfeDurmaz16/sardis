-- FX Quotes and Bridge Transfers for cross-currency stablecoin swaps.
--
-- Sardis routes FX through chain-native infrastructure:
-- Tempo: enshrined DEX orderbook, Base: Uniswap V3/V4

CREATE TABLE IF NOT EXISTS fx_quotes (
    quote_id TEXT PRIMARY KEY,                    -- fxq_xxx
    from_currency TEXT NOT NULL,
    to_currency TEXT NOT NULL,
    from_amount NUMERIC(20,6) NOT NULL,
    to_amount NUMERIC(20,6) NOT NULL,
    rate NUMERIC(20,12) NOT NULL,
    slippage_bps INTEGER DEFAULT 50,

    provider TEXT DEFAULT 'tempo_dex'
        CHECK (provider IN ('tempo_dex', 'uniswap_v3', 'uniswap_v4', '1inch', 'paraswap')),
    chain TEXT DEFAULT 'tempo',
    tx_hash TEXT,

    status TEXT DEFAULT 'quoted'
        CHECK (status IN ('pending', 'quoted', 'executing', 'completed', 'expired', 'failed')),
    expires_at TIMESTAMPTZ NOT NULL,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_fx_status ON fx_quotes(status);
CREATE INDEX IF NOT EXISTS idx_fx_created ON fx_quotes(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_fx_pair ON fx_quotes(from_currency, to_currency);

CREATE TABLE IF NOT EXISTS bridge_transfers (
    transfer_id TEXT PRIMARY KEY,                 -- brt_xxx
    from_chain TEXT NOT NULL,
    to_chain TEXT NOT NULL,
    token TEXT NOT NULL DEFAULT 'USDC',
    amount NUMERIC(20,6) NOT NULL,

    bridge_provider TEXT DEFAULT 'relay',
    bridge_fee NUMERIC(20,6) DEFAULT 0,

    source_tx_hash TEXT,
    destination_tx_hash TEXT,

    status TEXT DEFAULT 'pending'
        CHECK (status IN ('pending', 'bridging', 'completed', 'failed')),
    estimated_seconds INTEGER DEFAULT 60,

    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_bridge_status ON bridge_transfers(status);
CREATE INDEX IF NOT EXISTS idx_bridge_created ON bridge_transfers(created_at DESC);

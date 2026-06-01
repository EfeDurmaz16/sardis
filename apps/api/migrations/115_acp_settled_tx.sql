-- ACP on-chain settlement claim registry — one settled tx settles ONE order.
--
-- A confirmed on-chain Transfer to the (single, global) merchant settlement
-- address proves SOMEONE paid, not that a SPECIFIC ACP checkout session was
-- paid.  Without a uniqueness guard the same tx_hash can be replayed across
-- many same-amount sessions, each independently passing on-chain verification
-- and being marked `succeeded` — one payment, N fulfilled orders.
--
-- This table is the durable, multi-process guard: the crypto completion path
-- claims the (chain, tx_hash) pair for exactly one session BEFORE crediting.
-- The PRIMARY KEY on claim_key makes the claim atomic across processes — a
-- concurrent second claim hits ON CONFLICT and is refused (HTTP 409), so the
-- order is never double-credited even under a cross-process race.
--
-- claim_key format: "<chain_lower>:<tx_hash_lower>"

CREATE TABLE IF NOT EXISTS acp_settled_tx (
    claim_key  TEXT PRIMARY KEY,           -- "<chain>:<tx_hash>", lowercased
    session_id TEXT NOT NULL,              -- the single session that owns this tx
    claimed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_acp_settled_tx_session
    ON acp_settled_tx (session_id);

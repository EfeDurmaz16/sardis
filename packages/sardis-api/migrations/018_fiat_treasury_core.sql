-- =============================================================================
-- Migration 018: Fiat Treasury Core
-- =============================================================================
-- Adds USD-first treasury primitives with multi-currency-ready schema:
-- - lithic_financial_accounts
-- - external_bank_accounts
-- - ach_payments
-- - ach_payment_events
-- - treasury_balance_snapshots
-- - treasury_reservations
-- - treasury_webhook_events
-- =============================================================================

INSERT INTO schema_migrations (version, description)
VALUES ('018', 'Add fiat treasury core tables for financial accounts, external bank accounts, ACH, and reconciliation')
ON CONFLICT (version) DO NOTHING;

-- -----------------------------------------------------------------------------
-- Lithic financial accounts (program/account-holder level)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS lithic_financial_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    account_token TEXT,
    financial_account_token TEXT NOT NULL UNIQUE,
    account_role TEXT NOT NULL, -- ISSUING, OPERATING, RESERVE
    currency TEXT NOT NULL DEFAULT 'USD',
    status TEXT NOT NULL DEFAULT 'OPEN',
    is_program_level BOOLEAN NOT NULL DEFAULT FALSE,
    nickname TEXT,
    routing_number TEXT,
    account_number_last4 TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT chk_lfa_role CHECK (account_role IN ('ISSUING', 'OPERATING', 'RESERVE'))
);

CREATE INDEX IF NOT EXISTS idx_lfa_org ON lithic_financial_accounts(organization_id);
CREATE INDEX IF NOT EXISTS idx_lfa_account_token ON lithic_financial_accounts(account_token);
CREATE INDEX IF NOT EXISTS idx_lfa_role ON lithic_financial_accounts(organization_id, account_role);

-- -----------------------------------------------------------------------------
-- External bank accounts used for ACH counterparties
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS external_bank_accounts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    external_bank_account_token TEXT NOT NULL UNIQUE,
    financial_account_token TEXT NOT NULL,
    owner_type TEXT NOT NULL,          -- INDIVIDUAL, BUSINESS
    owner TEXT NOT NULL,
    account_type TEXT NOT NULL,        -- CHECKING, SAVINGS
    verification_method TEXT NOT NULL, -- MICRO_DEPOSIT, PRENOTE, EXTERNALLY_VERIFIED
    verification_state TEXT NOT NULL DEFAULT 'PENDING',
    state TEXT NOT NULL DEFAULT 'ENABLED',
    currency TEXT NOT NULL DEFAULT 'USD',
    country TEXT NOT NULL DEFAULT 'USA',
    name TEXT,
    routing_number TEXT,
    last_four TEXT,
    user_defined_id TEXT,
    company_id TEXT,
    is_paused BOOLEAN NOT NULL DEFAULT FALSE,
    pause_reason TEXT,
    last_return_reason_code TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_eba_org ON external_bank_accounts(organization_id);
CREATE INDEX IF NOT EXISTS idx_eba_financial_account ON external_bank_accounts(financial_account_token);
CREATE INDEX IF NOT EXISTS idx_eba_states ON external_bank_accounts(organization_id, state, verification_state);
CREATE INDEX IF NOT EXISTS idx_eba_user_defined_id ON external_bank_accounts(user_defined_id)
    WHERE user_defined_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- ACH payments (authoritative treasury payment records)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ach_payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_token TEXT NOT NULL UNIQUE,
    organization_id TEXT NOT NULL,
    financial_account_token TEXT NOT NULL,
    external_bank_account_token TEXT NOT NULL,
    direction TEXT NOT NULL, -- COLLECTION, PAYMENT
    method TEXT NOT NULL,    -- ACH_NEXT_DAY, ACH_SAME_DAY
    sec_code TEXT NOT NULL DEFAULT 'CCD',
    currency TEXT NOT NULL DEFAULT 'USD',
    amount_minor BIGINT NOT NULL,
    status TEXT NOT NULL DEFAULT 'PENDING',
    result TEXT,
    source TEXT DEFAULT 'CUSTOMER',
    provider_reference TEXT,
    user_defined_id TEXT,
    idempotency_key TEXT,
    retry_count INTEGER NOT NULL DEFAULT 0,
    last_return_reason_code TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    settled_at TIMESTAMPTZ,
    released_at TIMESTAMPTZ,
    CONSTRAINT chk_ach_direction CHECK (direction IN ('COLLECTION', 'PAYMENT'))
);

CREATE INDEX IF NOT EXISTS idx_ach_org_status ON ach_payments(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_ach_org_created ON ach_payments(organization_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ach_financial_account ON ach_payments(financial_account_token);
CREATE INDEX IF NOT EXISTS idx_ach_external_bank_account ON ach_payments(external_bank_account_token);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ach_org_idempotency
    ON ach_payments(organization_id, idempotency_key)
    WHERE idempotency_key IS NOT NULL;

-- -----------------------------------------------------------------------------
-- ACH payment event log (append-only lifecycle events)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ach_payment_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_token TEXT NOT NULL REFERENCES ach_payments(payment_token) ON DELETE CASCADE,
    organization_id TEXT NOT NULL,
    event_token TEXT,
    event_type TEXT NOT NULL,
    amount_minor BIGINT,
    result TEXT,
    detailed_results JSONB NOT NULL DEFAULT '[]'::jsonb,
    return_reason_code TEXT,
    raw_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_ach_events_payment_created ON ach_payment_events(payment_token, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_ach_events_org_created ON ach_payment_events(organization_id, created_at DESC);
CREATE UNIQUE INDEX IF NOT EXISTS idx_ach_events_org_event_token
    ON ach_payment_events(organization_id, event_token)
    WHERE event_token IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Treasury balance snapshots (reconciliation source)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS treasury_balance_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id TEXT NOT NULL,
    financial_account_token TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'USD',
    available_amount_minor BIGINT NOT NULL DEFAULT 0,
    pending_amount_minor BIGINT NOT NULL DEFAULT 0,
    total_amount_minor BIGINT NOT NULL DEFAULT 0,
    as_of_event_token TEXT,
    provider_updated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_tbs_org_financial_created
    ON treasury_balance_snapshots(organization_id, financial_account_token, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_tbs_currency_created
    ON treasury_balance_snapshots(currency, created_at DESC);

-- -----------------------------------------------------------------------------
-- Treasury reservations for card and payout pre-allocation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS treasury_reservations (
    reservation_id TEXT PRIMARY KEY,
    organization_id TEXT NOT NULL,
    wallet_id TEXT,
    card_id TEXT,
    currency TEXT NOT NULL DEFAULT 'USD',
    amount_minor BIGINT NOT NULL,
    status TEXT NOT NULL, -- held, consumed, released, cancelled
    reason TEXT,
    reference_id TEXT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_treasury_res_org_status ON treasury_reservations(organization_id, status);
CREATE INDEX IF NOT EXISTS idx_treasury_res_wallet ON treasury_reservations(wallet_id)
    WHERE wallet_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_treasury_res_card ON treasury_reservations(card_id)
    WHERE card_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_treasury_res_reference ON treasury_reservations(reference_id)
    WHERE reference_id IS NOT NULL;

-- -----------------------------------------------------------------------------
-- Webhook replay ledger for treasury providers
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS treasury_webhook_events (
    provider TEXT NOT NULL,
    event_id TEXT NOT NULL,
    body_hash TEXT,
    status TEXT NOT NULL DEFAULT 'processed',
    processed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (provider, event_id)
);

CREATE INDEX IF NOT EXISTS idx_treasury_webhook_processed_at
    ON treasury_webhook_events(processed_at DESC);


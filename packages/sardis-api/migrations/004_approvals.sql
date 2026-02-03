-- Migration: 004_approvals.sql
-- Description: Create approvals table for human approval workflow

-- Create enum types
CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'denied', 'expired', 'cancelled');
CREATE TYPE approval_urgency AS ENUM ('low', 'medium', 'high');

-- Create approvals table
CREATE TABLE IF NOT EXISTS approvals (
    -- Primary key
    id VARCHAR(64) PRIMARY KEY,  -- Format: appr_<timestamp_base36>

    -- Core fields (from MCP TypeScript interface)
    action VARCHAR(64) NOT NULL,           -- 'payment', 'create_card', etc.
    vendor VARCHAR(255),                    -- Vendor name for payments
    amount DECIMAL(18, 6),                  -- Payment amount (nullable for non-payment actions)
    purpose TEXT,                           -- Purpose description
    reason TEXT,                            -- Reason for approval request
    card_limit DECIMAL(18, 6),             -- Card limit (for create_card action)

    -- Status tracking
    status approval_status NOT NULL DEFAULT 'pending',
    urgency approval_urgency NOT NULL DEFAULT 'medium',

    -- Actor tracking
    requested_by VARCHAR(64) NOT NULL,     -- Agent ID who requested
    reviewed_by VARCHAR(255),               -- Email/ID of human reviewer

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,        -- When approval request expires
    reviewed_at TIMESTAMPTZ,                -- When decision was made

    -- Foreign keys (soft references - IDs stored, not enforced)
    agent_id VARCHAR(64),                   -- FK to agents table
    wallet_id VARCHAR(64),                  -- FK to wallets table
    organization_id VARCHAR(64),            -- FK to organizations table (future)

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb      -- Extensible metadata
);

-- Required indexes for performance
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_agent_id ON approvals(agent_id);
CREATE INDEX idx_approvals_wallet_id ON approvals(wallet_id);
CREATE INDEX idx_approvals_organization_id ON approvals(organization_id);
CREATE INDEX idx_approvals_requested_by ON approvals(requested_by);
CREATE INDEX idx_approvals_expires_at ON approvals(expires_at) WHERE status = 'pending';
CREATE INDEX idx_approvals_created_at ON approvals(created_at DESC);

-- Composite index for common query patterns
CREATE INDEX idx_approvals_status_urgency ON approvals(status, urgency) WHERE status = 'pending';

-- Comments for documentation
COMMENT ON TABLE approvals IS 'Human approval requests for agent actions exceeding policy limits';
COMMENT ON COLUMN approvals.id IS 'Unique approval ID, format: appr_<base36_timestamp>';
COMMENT ON COLUMN approvals.action IS 'Type of action: payment, create_card, transfer, etc.';
COMMENT ON COLUMN approvals.requested_by IS 'Agent ID that initiated the approval request';
COMMENT ON COLUMN approvals.reviewed_by IS 'Human reviewer email or admin ID';

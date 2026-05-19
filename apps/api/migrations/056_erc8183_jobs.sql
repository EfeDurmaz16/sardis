-- ERC-8183 Agentic Commerce: Job lifecycle tables
-- Three-party job primitive: Client, Provider, Evaluator

CREATE TABLE IF NOT EXISTS erc8183_jobs (
    id TEXT PRIMARY KEY,
    client_agent_id TEXT NOT NULL,
    provider_agent_id TEXT NOT NULL,
    evaluator_agent_id TEXT NOT NULL,
    amount NUMERIC NOT NULL CHECK (amount > 0),
    token TEXT NOT NULL DEFAULT 'USDC',
    chain TEXT NOT NULL DEFAULT 'base',
    state TEXT NOT NULL DEFAULT 'open'
        CHECK (state IN ('open','funded','submitted','completed','rejected','expired','disputed')),
    description TEXT DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    deadline TIMESTAMPTZ NOT NULL,
    funded_at TIMESTAMPTZ,
    funding_tx_hash TEXT,
    deliverable_uri TEXT,
    deliverable_hash TEXT,
    submitted_at TIMESTAMPTZ,
    evaluation_result TEXT,
    evaluation_reason TEXT,
    evaluated_at TIMESTAMPTZ,
    evaluation_tx_hash TEXT,
    settlement_tx_hash TEXT,
    settled_at TIMESTAMPTZ,
    onchain_job_id BIGINT,
    contract_address TEXT,
    hook_contract_address TEXT,
    metadata JSONB DEFAULT '{}'::JSONB,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CHECK (client_agent_id != provider_agent_id),
    CHECK (evaluator_agent_id != client_agent_id),
    CHECK (evaluator_agent_id != provider_agent_id)
);

CREATE INDEX idx_erc8183_client ON erc8183_jobs(client_agent_id);
CREATE INDEX idx_erc8183_provider ON erc8183_jobs(provider_agent_id);
CREATE INDEX idx_erc8183_evaluator ON erc8183_jobs(evaluator_agent_id);
CREATE INDEX idx_erc8183_state ON erc8183_jobs(state);
CREATE INDEX idx_erc8183_deadline ON erc8183_jobs(deadline) WHERE state IN ('open','funded','submitted');

CREATE TABLE IF NOT EXISTS erc8183_evaluations (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES erc8183_jobs(id),
    evaluator_agent_id TEXT NOT NULL,
    result TEXT NOT NULL CHECK (result IN ('approved','rejected')),
    reason TEXT,
    evidence_uri TEXT,
    trust_score_at_eval NUMERIC,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_erc8183_eval_job ON erc8183_evaluations(job_id);

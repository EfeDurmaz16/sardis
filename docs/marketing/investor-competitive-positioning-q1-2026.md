# Sardis Investor Competitive Positioning (Q1 2026)

Date: 2026-02-25  
Audience: Seed / pre-Series A fintech + AI infrastructure investors

## One-line position

Sardis is the deterministic trust and control layer between AI agents and payment execution across fiat, card, and on-chain rails.

## Deterministic vs Probabilistic Boundary

- LLM/model layer is advisory only (intent suggestion).
- Final execution authority is deterministic: policy + compliance + approval + runtime guardrails.
- Outcome for a payment request is reproducible from persisted inputs, not model variability.
- Practical message for diligence: "Model can suggest; policy decides."

## Why now

- Agentic commerce is moving from experimentation to production workloads.
- Existing payment rails are human-centric and weak against autonomous error patterns (goal drift, retry loops, prompt-injection influenced intent).
- Enterprises need auditable controls before they allow real money movement by agents.

## Sardis moat stack

- Deterministic policy enforcement (fail-closed default behavior).
- Approval orchestration (quorum + distinct reviewer / 4-eyes controls).
- Verifiable audit trail (Merkle-proof export path + compliance evidence).
- Multi-agent trust controls (trusted peer graph + wallet-aware broadcast targets).
- Multi-rail execution under one control plane (cards, fiat treasury, on-chain).

## What shipped recently (v0.10 hardening)

- Immutable hard-limit layer for NL policy parser + fuzz/property coverage.
- Agent-level sliding-window limiter on payment endpoints (429 + Retry-After).
- ERC-4337 production signer path (Turnkey/Fireblocks) + staged sponsor cap controls.
- CI gas ceiling tests + gas report artifact publishing.
- Turnkey outage DR playbook with RTO/RPO and failover mode guidance.
- Secure checkout evidence export bundle with digest/hash-chain integrity metadata.
- Enterprise SLA/support endpoints + dashboard workflows for ticket lifecycle.

## Verified diligence numbers

Source: `python3 scripts/audit/claims_check.py --json` (2026-02-25)

- MCP tools: 52
- Total packages: 27 (22 Python + 4 npm + 1 root meta)
- Tests: 825 selected / 887 total collected

## Competitive framing

- Card issuers provide rails; Sardis provides execution governance and proof.
- Crypto wallet infra provides settlement; Sardis provides policy + approval + compliance controls.
- Agent frameworks provide orchestration; Sardis provides payment-grade safety guarantees.
- If providers add agent-facing APIs, Sardis remains the control and evidence layer above them.

## Corner-case Diligence Answers

### 1) Agent-level rate limiting implementation detail

- Current implementation: sliding-window limiter, Redis-backed for multi-instance accuracy.
- Behavior on Redis issues: graceful fallback to in-memory limiter to preserve service continuity.
- Enterprise posture: Redis must be provisioned for production-grade consistency and predictable throttling.

### 2) Merkle/audit proof generation speed

- Decision-time policy/audit events are written inline with execution flow.
- Secure checkout evidence export is generated on-demand from persisted artifacts with digest/hash-chain integrity.
- Bulk compliance exports can run as batch jobs, while per-job evidence remains near real-time.

### 3) Turnkey outage fallback UX

- Mode 1 (degraded): policy/compliance remain active, high-risk flows blocked, low-risk constrained flows continue.
- Mode 2 (containment): new executions denied fail-closed, read/admin/audit surfaces remain available.
- User-facing impact is explicit and deterministic (clear reason codes, no silent partial behavior).

## Provider Diligence: Sardis Response Templates

Use these concise answers in partner/investor diligence calls.

1. "Can Stripe/Lithic/Rain replace Sardis directly?"
- They provide payment rails; Sardis provides governance (deterministic policy, approval orchestration, verifiable audit proofs) across multiple rails.

2. "How do you handle real-time authorization latency constraints?"
- Sardis keeps deterministic checks pre-computed where possible and enforces fail-closed decision paths; if runtime checks cannot complete safely, request is denied or escalated.

3. "What happens if signer infrastructure fails?"
- Deterministic failover modes (degraded/containment) preserve policy and audit guarantees; no unsafe bypass path from agent output to funds movement.

4. "How do you prove transaction legitimacy after the fact?"
- Evidence exports include approval context, policy snapshot hash, audit events, digest, and hash-chain tail for tamper-evident verification.

5. "Where do compliance responsibilities split?"
- Sardis orchestrates policy/compliance gates and evidence; issuer/onramp partners provide their regulated rail controls. Ownership is explicit in integration contracts and runbooks.

## Key diligence question to ask providers (Stripe, Lithic, Rain, Bridge)

- Real-time authorization SLA and timeout behavior.
- PAN delivery mode (hosted/iframe/tokenized vs raw reveal API).
- Funding/settlement model and prefunding requirements.
- Compliance ownership split (KYB/KYC/KYT/sanctions/reporting).
- Production onboarding timeline and blocker dependencies.

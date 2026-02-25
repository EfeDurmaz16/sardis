# Sardis Investor Competitive Positioning (Q1 2026)

Date: 2026-02-25  
Audience: Seed / pre-Series A fintech + AI infrastructure investors

## One-line position

Sardis is the deterministic trust and control layer between AI agents and payment execution across fiat, card, and on-chain rails.

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

## What shipped recently (v0.9.2 hardening)

- Secure checkout quorum with PAN-lane specific approval minimums.
- Distinct reviewer enforcement for high-risk PAN execution.
- Lithic ASA fail-closed defaults for lookup/matcher failures in production.
- Runtime security-policy introspection endpoints for checkout, ASA, and A2A trust.
- Wallet-aware A2A trusted peer directory + broadcast target visibility.

## Verified diligence numbers

Source: `python3 scripts/audit/claims_check.py --json` (2026-02-25)

- MCP tools: 52
- Total packages: 27 (22 Python + 4 npm + 1 root meta)
- Tests: 825 selected / 887 total collected

## Competitive framing

- Card issuers provide rails; Sardis provides execution governance and proof.
- Crypto wallet infra provides settlement; Sardis provides policy + approval + compliance controls.
- Agent frameworks provide orchestration; Sardis provides payment-grade safety guarantees.

## Key diligence question to ask providers (Stripe, Lithic, Rain, Bridge)

- Real-time authorization SLA and timeout behavior.
- PAN delivery mode (hosted/iframe/tokenized vs raw reveal API).
- Funding/settlement model and prefunding requirements.
- Compliance ownership split (KYB/KYC/KYT/sanctions/reporting).
- Production onboarding timeline and blocker dependencies.

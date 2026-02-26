# Sardis Pitch Deck Outline (Q1 2026)

Date: 2026-02-26  
Audience: Seed / pre-Series A fintech + AI infra investors

## Slide 1: Title

- Sardis: Payment Control Plane for AI Agents
- Tagline: "Deterministic policy + approval + proof across fiat, card, and on-chain rails."

## Slide 2: Problem

- AI agents can initiate payments, but current rails assume human operators.
- Core enterprise blockers:
  - goal drift / prompt-injection risk
  - lack of deterministic guardrails
  - weak auditability and compliance evidence

## Slide 3: Why Existing Stack Fails

- Issuers solve card rails, not agent governance.
- Wallet infra solves signing, not approval/policy enforcement.
- Agent frameworks solve orchestration, not payment safety.

## Slide 4: Sardis Solution

- Deterministic policy engine (fail-closed)
- Approval orchestration (quorum + distinct reviewers)
- Verifiable audit trail (Merkle anchors + evidence exports)
- Multi-rail execution (cards + fiat treasury + on-chain)

## Slide 5: Product Architecture

- Control plane:
  - intent validation
  - policy hard-limits
  - approval + compliance gate
- Execution plane:
  - tokenized/embedded checkout path preferred
  - PAN lane isolated behind secure checkout
- Proof plane:
  - audit events + digest/hash-chain evidence bundle

## Slide 6: Security & Hardening (Now)

- Immutable NL parser hard-limits + fuzz/property tests
- Agent-level sliding-window payment limiter
- ASA fail-closed posture (issuer auth stream safety)
- Turnkey outage DR runbook (RTO/RPO + failover modes)
- Gas ceiling CI guardrails for ERC-4337 paths

## Slide 7: Differentiation

- "Intent-aware payments" instead of balance-only checks
- Built-in human approval for high-risk flows
- Audit-ready evidence artifacts per critical payment path
- Wallet-aware A2A trust and approval-gated trust mutation model

## Slide 8: Enterprise Readiness

- Enterprise SLA profile + ticket lifecycle endpoints
- Dashboard support workflows
- Runtime policy/security posture endpoints for ops visibility
- Provider capability matrix for funding and routing readiness

## Slide 9: GTM

- Design-partner motion with issuer/onramp partners
- API-first developer adoption via SDK/MCP ecosystem
- Compliance-forward positioning for enterprise buying centers

## Slide 10: Roadmap (Q1-Q2 2026)

- ERC-4337 staged mainnet rollout with sponsor caps
- Stablecoin allowlist + recurring billing engine
- Multi-tenant org hardening + policy templates
- Advanced analytics and enterprise support expansion

## Slide 11: Ask

- Raise: seed round to accelerate:
  - production partner onboarding
  - compliance/security hiring
  - enterprise deployment reliability
- Investor support needed:
  - sponsor bank / issuer partnerships
  - enterprise design-partner intros

## Slide 12: Appendix (Diligence Artifacts)

- Hardening test suites and CI gates
- Security posture endpoints (checkout/ASA/A2A)
- DR runbooks and incident response checklists
- Evidence export API examples

## Notes for Presenter

- Keep model decisions "advisory"; deterministic policy + approval is final decision layer.
- Emphasize PCI-minimization path: tokenized/embedded first, isolated PAN lane only when necessary.
- Show one real evidence payload during demo (`/api/v2/checkout/secure/jobs/{job_id}/evidence`).

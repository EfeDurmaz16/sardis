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
- Key line to say: "Model output is advisory; deterministic policy is final authority."

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
- Positioning line: "Rails are replaceable modules; governance and proof are the moat."

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

### Suggested allocation example (for a $6M seed)

| Area | Allocation | Why |
|------|------------|-----|
| Mainnet deployment + reliability | 60% | signer redundancy, ops hardening, on-call maturity |
| Enterprise sales + pilots | 25% | shorten design-partner to paid conversion |
| Security/compliance engineering | 15% | SOC2/PCI readiness and continuous assurance |

## Slide 12: Diligence Q&A (Investor Objections)

- "Stripe/issuer can build this."
  - Response: "They provide rails; Sardis provides deterministic governance and cross-rail proof."
- "What if agent wallet access is compromised?"
  - Response: "Fail-closed policy, approval quorum, velocity controls, freeze/rotate response prevent large unauthorized outflow."
- "How do auditors verify what happened?"
  - Response: "Per-flow evidence bundle with digest/hash-chain integrity and explicit verifier hints."

## Slide 13: Appendix (Diligence Artifacts)

- Hardening test suites and CI gates
- Security posture endpoints (checkout/ASA/A2A)
- DR runbooks and incident response checklists
- Evidence export API examples

## Notes for Presenter

- Keep model decisions "advisory"; deterministic policy + approval is final decision layer.
- Emphasize PCI-minimization path: tokenized/embedded first, isolated PAN lane only when necessary.
- Show one real evidence payload during demo (`/api/v2/checkout/secure/jobs/{job_id}/evidence`).
- While demoing evidence payload, call out integrity fields explicitly (`digest_sha256`, `hash_chain_tail`) as verifiability primitives.

# Partner Outreach Email Drafts

Use these as plain-text drafts. Replace bracketed placeholders before sending.

## 1) Lithic (Production Card Issuing)

Subject: Sardis x Lithic — Production Enablement for Agentic Virtual Cards

Hi Lithic team,

I’m [Your Name], founder at Sardis. We’re building open-core payment infrastructure for AI agents, and we are now in design-partner onboarding with selected teams.

Quick context:
- We provide policy-controlled agent payments with non-custodial wallet architecture.
- We already run simulated and staging-live payment lanes.
- We have production hardening in place for auth, rate limiting, idempotency, and auditability.
- We recently upgraded our cryptographic audit trail verification flow (Merkle-linked receipts + verification endpoint).

What we’re looking for from Lithic now:
- Move from sandbox to production card issuing.
- Confirm production requirements for card create/freeze/unfreeze/transaction lifecycle webhooks.
- Align on compliance and operational guardrails for agent-initiated spend.
- Validate expected volume/rate limits and best practices for reliable webhook operations.

Current stage:
- We are in design-partner onboarding (not broad GA).
- We want a tight, controlled production lane with explicit policy enforcement and auditable controls.

If helpful, we can share:
- API docs and architecture overview
- End-to-end demo flow (policy allow/deny + card lifecycle)
- Security controls checklist and incident response plan

Would your team be open to a 30-minute technical onboarding call next week?

Best,  
[Name]  
[Title], Sardis  
[Email]  
[Phone]  

---

## 2) Persona (KYC + KYB)

Subject: Sardis x Persona — KYC/KYB Production Rollout for Agentic Payments

Hi Persona team,

I’m [Your Name], founder at Sardis. We’re an open-core payment infrastructure platform for AI agents, currently onboarding design partners.

What Sardis does:
- Policy-controlled payments for agents (with approval thresholds and explicit deny paths).
- Non-custodial wallet execution architecture.
- End-to-end auditability with cryptographic receipt verification.

Where we need Persona:
- Production KYC and KYB rollout for our design-partner cohort.
- Guidance on best-practice flows for: onboarding, re-verification, webhook handling, and risk/failure states.
- Validation that our current fail-closed compliance behavior aligns with Persona-recommended patterns.

Current stage:
- Design-partner onboarding with controlled production exposure.
- We need robust identity/compliance operations before broader rollout.

Requested next steps:
- Confirm production onboarding checklist.
- Review required webhooks/events and signature verification expectations.
- Align on escalation path for edge-case verification outcomes.

Happy to share our API endpoints and test scenarios ahead of a call.

Best,  
[Name]  
[Title], Sardis  
[Email]  
[Phone]  

---

## 3) Elliptic (AML / Sanctions)

Subject: Sardis x Elliptic — AML/Sanctions Integration for Agent Payment Controls

Hi Elliptic team,

I’m [Your Name], founder at Sardis. We build open-core payment infrastructure for AI agents and are currently in design-partner onboarding.

Context:
- Agents execute payments under strict policy controls.
- We enforce compliance checks before execution and fail closed where required.
- We maintain an append-only, cryptographically verifiable audit trail for payment actions.

What we need from Elliptic:
- Production AML/sanctions integration guidance.
- Recommended thresholds, policy tuning, and risk response playbooks.
- Best practices for address and transaction screening flow design for agent-led payments.
- Operational guidance for high-confidence block/allow decisions and audit evidence requirements.

Stage:
- Controlled design-partner rollout, focused on safety, explainability, and operator oversight.

Would you be open to a technical review session to validate our integration architecture and risk controls?

Best,  
[Name]  
[Title], Sardis  
[Email]  
[Phone]  

---

## 4) Bridge.xyz (Partnership / Fiat Rails)

Subject: Sardis x Bridge — Partnership Discussion for Agentic Fiat On/Off-Ramp

Hi Bridge team,

I’m [Your Name], founder at Sardis. We’re building open-core payment infrastructure for AI agents, and we are currently onboarding design partners.

What we’ve built:
- Policy-gated agent payment execution across wallet/card/checkout flows.
- Operational controls: auth, rate limits, idempotency, and webhook security.
- Cryptographically verifiable audit trail for payment events.

What we’re looking for:
- Partnership path for reliable fiat on/off-ramp in controlled production.
- Technical alignment on Bridge API/webhook lifecycle, settlement states, and reconciliation.
- Guidance on production readiness requirements, limits, and risk controls.

Current stage:
- Design-partner onboarding with staged rollout, not open public scale yet.
- Priority is reliability and compliance-grade observability before broader launch.

If relevant, we can share our current integration surface and a concrete rollout plan by phase.

Would your partnerships + solutions engineering teams be open to an intro call?

Best,  
[Name]  
[Title], Sardis  
[Email]  
[Phone]  

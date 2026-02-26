# Provider Meeting Kit (Stripe + Rain, 15 min)

Date: 2026-02-26  
Owner: Sardis GTM + Infra

## Goal of each call

Lock a concrete path to production for:
1. Real-time auth decisioning under Sardis policy controls
2. Funding reliability and cutoff behavior
3. PAN handling model with minimal PCI scope expansion
4. Compliance ownership split (KYB/KYC/KYT, sanctions, incident reporting)

---

## Stripe 15-minute agenda

### 0-2 min: Context
- Sardis = deterministic control plane above payment rails.
- Need issuer lane for autonomous agents with fail-closed policy/approval/audit.

### 2-7 min: Hard blockers
1. Auth callback SLA + timeout hard limits
2. Issuing funding mechanics (prefund, settlement windows, failure behavior)
3. PAN reveal options (hosted/ephemeral/tokenized vs raw access)
4. Connect account mapping for multi-tenant orgs

### 7-11 min: Integration detail
1. Webhook idempotency + replay guidance
2. Recommended failover posture (primary/fallback provider behavior)
3. Test mode -> production cutover checklist and typical timeline

### 11-15 min: Commercial/operational close
1. Required contracts and compliance prerequisites
2. Named technical owner + next technical deep-dive slot
3. Success criteria for live-lane certification

---

## Rain 15-minute agenda

### 0-2 min: Context
- Sardis runs policy, approval, and audit rails for AI agent spend.
- Want stablecoin-native issuing + money movement in one operating lane.

### 2-7 min: Hard blockers
1. API availability level (GA/private) and onboarding path
2. Stablecoin-to-card funding path and settlement SLA
3. PAN model (hosted/ephemeral/raw) and PCI scope impact
4. Geography/entity limitations

### 7-11 min: Integration detail
1. Real-time auth and webhook reliability guarantees
2. Money-in / accounts / money-out interoperability with card issuing
3. Failure handling during liquidity/chain stress

### 11-15 min: Commercial/operational close
1. Required compliance docs and RACI split
2. Sandbox/prod timeline with concrete milestones
3. Design-partner pilot scope (volume, regions, cards)

---

## Must-capture answers (both calls)

1. Authorization decision timeout threshold (exact seconds)
2. Webhook retry strategy and replay/idempotency recommendations
3. Funding cutoff windows and reversal behavior
4. PAN exposure model and PCI implications
5. KYB/KYC/KYT ownership map
6. Incident SLA and escalation path
7. Production onboarding timeline with prerequisites

---

## Decision output template (post-call)

- Provider:
- Call date:
- Technical owner on provider side:
- Auth SLA:
- Funding model:
- PAN model:
- Compliance split:
- Timeline to live lane:
- Top 3 risks:
- Decision: `GO` / `HOLD` / `NO-GO`

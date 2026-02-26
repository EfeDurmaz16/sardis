# Stripe Diligence Response Sheet (Q1 2026)

Date: 2026-02-26  
Owner: Sardis GTM + Infra

## 1) Role in Sardis Stack

- Secondary or fallback card issuer for Sardis-controlled agent spend.
- Strong fit for enterprise distribution and global acceptance.
- Works best as a rail under Sardis deterministic policy, approval, and audit layers.

## 2) What Stripe Can Solve

- Card issuance: virtual cards and authorization webhooks.
- PAN handling: can be done via hosted/ephemeral retrieval patterns to reduce PCI exposure.
- Enterprise trust: recognizable brand, procurement-friendly.

## 3) What Stripe Does Not Automatically Solve

- Agent governance: goal-drift controls, deterministic intent validation, and 4-eyes approvals remain Sardis scope.
- End-to-end stablecoin-native funding for each autonomous agent is not guaranteed by default card setup.
- Multi-rail orchestration across card + on-chain + fallback rails still needs Sardis router logic.

## 4) Funding Model Notes (Critical)

- "Stripe-compatible funding" usually means keeping enough issuer balance or treasury liquidity for authorizations.
- If fiat enters via another provider, practical path is typically off-ramp to bank/account rails, then fund Stripe-side balances.
- Direct stablecoin-to-issuing-balance flow must be confirmed contractually and operationally.

## 5) Compliance Split (Who Owns What)

- Stripe side: regulated rail controls around issuing stack and required account/cardholder checks in their model.
- Sardis side: deterministic policy enforcement, risk scoring, KYT overlays, approval workflow, audit evidence integrity.
- Shared: incident handling, dispute workflows, and clear RACI in MSA/SOW.

## 6) Must-Ask Diligence Questions

1. Real-time auth SLA and hard timeout behavior for authorization callbacks.
2. PAN/CVV reveal mode: hosted iframe/tokenized/ephemeral vs raw API exposure.
3. Funding requirements: prefund thresholds, sweep behavior, cutoff times, and failure modes.
4. Geo coverage and KYB/KYC responsibility boundaries by market.
5. Program-level controls: merchant locks, MCC blocks, velocity, and single-use semantics.

## 7) Go / No-Go Criteria

- GO if auth callback + webhook reliability, funding mechanics, and PAN security model meet Sardis guardrail requirements.
- NO-GO if funding introduces manual bottlenecks or raw PAN handling expands PCI scope beyond planned enclave model.

## 8) Recommendation (Current)

- Keep Stripe as strategic rail and fallback provider.
- Prioritize deterministic policy + approval + audit controls above Stripe, not inside prompts/agents.
- Finalize only after written confirmation on funding and PAN handling model.

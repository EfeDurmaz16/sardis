# Bridge Diligence Response Sheet (Q1 2026)

Date: 2026-02-26  
Owner: Sardis GTM + Infra

## 1) Role in Sardis Stack

- Stablecoin liquidity and conversion infrastructure candidate.
- Potential bridge between on-chain treasury and fiat/account-based payment rails.
- Usually complementary to, not a replacement for, card issuer controls.

## 2) What Bridge Can Solve

- Stablecoin treasury operations and potential programmable transfer workflows.
- Faster movement between crypto-native balances and traditional payout/account contexts.
- Better alignment with agentic micropayment and always-on settlement patterns.

## 3) What Bridge Does Not Automatically Solve

- Card authorization governance and issuer-grade auth controls by itself.
- Merchant acceptance logic for card-not-present transactions.
- Sardis deterministic policy, approval, and verifiable audit requirements.

## 4) Funding Model Notes (Critical)

- Clarify if Bridge can directly feed issuer funding accounts in production and under what constraints.
- Define settlement timing, fees, reversals, and reconciliation format for finance operations.
- Ensure failure modes are explicit (conversion fail, liquidity constraints, chain congestion).

## 5) Compliance Split (Who Owns What)

- Bridge side: regulated obligations in their licensed/partner structure for supported jurisdictions.
- Sardis side: policy hard-limits, approval gates, KYT overlays, immutable audit evidence.
- Shared: KYB/KYC ownership matrix, sanctions controls, SAR/escalation processes where applicable.

## 6) Must-Ask Diligence Questions

1. Supported jurisdictions, entities, and production onboarding requirements.
2. Stablecoin coverage and conversion depth for required corridors.
3. SLA for conversion/payout operations and operational cutoff windows.
4. API/webhook idempotency and deterministic reconciliation guarantees.
5. Card-issuer interoperability details (Stripe/Lithic/Rain handoff patterns).

## 7) Go / No-Go Criteria

- GO if Bridge can provide contractually reliable treasury conversion rails with clear compliance boundaries.
- NO-GO if issuer funding interoperability is unclear or operationally manual.

## 8) Recommendation (Current)

- Position Bridge as treasury/connectivity layer, not the sole payment-control plane.
- Keep Sardis as deterministic governance layer across Bridge + issuer providers.
- Decide after receiving written integration architecture and commercial terms.

# Rain Diligence Response Sheet (Q1 2026)

Date: 2026-02-26  
Owner: Sardis GTM + Infra

## 1) Role in Sardis Stack

- Stablecoin-native card and money movement candidate.
- Potentially strongest fit for combined money-in, accounts, money-out, and card flows.
- Can reduce integration surface if commercial/API access is confirmed.

## 2) What Rain Can Solve

- Card issuance with stablecoin-aware settlement posture.
- Money-in and money-out primitives that may simplify treasury operations.
- Accounts layer that can map well to per-customer or per-organization funding structure.

## 3) What Rain Does Not Automatically Solve

- Sardis-specific agent governance (goal drift protection, deterministic policy, approvals).
- Proof-grade audit evidence model required for enterprise and regulator-facing workflows.
- Cross-provider fallback if Rain is unavailable still requires Sardis router architecture.

## 4) Funding Model Notes (Critical)

- Validate exact stablecoin-to-card funding path and operational SLAs.
- Confirm whether prefunding is required per tenant, per organization, or per program.
- Confirm reconciliation exports and settlement transparency needed for finance/audit teams.

## 5) Compliance Split (Who Owns What)

- Rain side: their regulated partner stack for issuing/payment products and internal risk controls.
- Sardis side: deterministic policy enforcement, approval orchestration, KYT overlays, evidence generation.
- Shared: KYB/KYC handoff boundaries, sanctions escalation, suspicious activity escalation procedures.

## 6) Must-Ask Diligence Questions

1. API availability and production onboarding timeline for enterprise partners.
2. PAN delivery mode and PCI scope implications (hosted reveal vs raw details).
3. Jurisdiction coverage and legal entity constraints.
4. Stablecoin support matrix and conversion mechanics.
5. Incident response SLA, webhook guarantees, and auth-timeout behavior.

## 7) Go / No-Go Criteria

- GO if Rain can provide stablecoin-native funding + issuing + compliance posture with clear API and SLA guarantees.
- NO-GO if commercial access or contractual responsibilities remain ambiguous for production timelines.

## 8) Recommendation (Current)

- Keep Rain as high-upside strategic partner for unified stablecoin/card operations.
- Continue parallel rails (Lithic/Stripe) until Rain terms and production path are contractually concrete.
- Use Sardis governance layer regardless of provider to keep control plane consistent.

# Lithic Diligence Response Sheet (Q1 2026)

Date: 2026-02-26  
Owner: Sardis GTM + Infra

## 1) Role in Sardis Stack

- Primary issuer candidate for agent virtual cards.
- Strong real-time authorization posture via auth stream patterns.
- Good fit for fine-grained program controls when combined with Sardis policy engine.

## 2) What Lithic Can Solve

- Card issuance: virtual-first, API-first workflows.
- Authorization controls: near-real-time approve/deny hooks.
- Card lifecycle operations: freeze/unfreeze/rotate with automation.

## 3) What Lithic Does Not Automatically Solve

- Multi-agent trust orchestration and intent-level governance remain Sardis scope.
- End-to-end stablecoin funding + conversion path is not a default guarantee.
- On-chain proof and Merkle-backed audit evidence remain Sardis responsibility.

## 4) Funding Model Notes (Critical)

- Validate prefunding/liquidity expectations at program level.
- Confirm funding frequency, settlement windows, and failure handling under spikes.
- If stablecoin treasury is upstream, define explicit conversion/on-off-ramp handoff before issuer funding.

## 5) Compliance Split (Who Owns What)

- Lithic side: issuing-rail regulatory controls and card network obligations in their operating model.
- Sardis side: deterministic policy hard-limits, approvals, KYT overlays, anomaly response, evidence exports.
- Shared: fraud operations playbooks, breach notification paths, and escalation SLAs.

## 6) Must-Ask Diligence Questions

1. Authorization callback SLA, retries, and timeout fallback semantics.
2. PAN reveal and storage patterns: hosted/ephemeral/tokenized options.
3. Per-card and program controls: MCC, merchant locks, velocity, and temporary spending windows.
4. Geographic and legal entity constraints for production rollout.
5. Operational limits: rate limits, webhook guarantees, idempotency patterns.

## 7) Go / No-Go Criteria

- GO if auth stream latency + controls support fail-closed decisions with Sardis policy in the loop.
- NO-GO if latency variance or control gaps force unsafe approvals or broad PCI scope.

## 8) Recommendation (Current)

- Keep Lithic as a primary rail where fast authorization control is required.
- Pair with Sardis hard-limit layer, approval quorum, and automated freeze/rotate on anomalies.
- Lock commercial decision after written confirmation on funding and geography constraints.

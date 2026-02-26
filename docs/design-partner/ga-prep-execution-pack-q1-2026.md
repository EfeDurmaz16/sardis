# GA Prep Execution Pack (Q1 2026)

Date: 2026-02-26  
Owner: Platform + Product + SRE

## 1) API Versioning + Freeze Policy

- Current stable public surface: `/api/v2`.
- Every response must continue to include `X-API-Version`.
- GA freeze policy:
  1. No breaking response-shape changes in `v2`.
  2. Any breaking change requires new versioned route (`v3`) and migration window.
  3. Feature flags may add optional fields only.
  4. Deprecations require docs + changelog + sunset date.

## 2) Onboarding Automation

- Gate command:
```bash
python3 scripts/check_design_partner_readiness.py --scope launch --max-review-age-days 60
```
- Provider certification gate:
```bash
bash scripts/release/provider_live_lane_cert_check.sh
```
- Required outcome: all launch gates `pass` or approved `waived`, with linked evidence.

## 3) Incident Drill + Rollback Proof Package

- Incident/rollback runbook gate:
```bash
bash scripts/release/mainnet_ops_drill_check.sh
```
- Evidence package must include:
  1. rollback steps executed or dry-run proof,
  2. provider webhook replay/idempotency proof,
  3. secure checkout evidence export sample,
  4. operator signoff with timestamp and commit SHA.

## 4) GA Readiness Entry Criteria

1. API versioning/freeze policy published and enforced.
2. Launch onboarding automation gate passes.
3. Provider live-lane certification scorecards have no critical zeros.
4. Incident drill + rollback package refreshed this quarter.
5. Compliance execution check passes on main.

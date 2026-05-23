# Sardis Facility Gate v1

## Decision

Sardis Facility Gate v1 is a non-custodial control-plane feature for partner-backed agent facility access. Sardis does not lend, hold customer funds, service debt, or issue production cards in this version. Sardis records and evaluates delegated authority, policy, risk, evidence, approval state, revocation state, and audit reconstruction before any external rail adapter can execute.

The first executable rail is a simulator shaped like a merchant-bound virtual card adapter. Real card, ACH, invoice, stablecoin, collateral, collections, and consumer-credit flows are explicitly out of scope until the authorization ledger and audit path are stable.

## Scope

- Target customer: B2B teams running autonomous cloud, API, SaaS, and developer-tool procurement agents.
- Target authority: temporary purchase authority against an externally backed facility.
- Target rail: rail-agnostic authorization, simulator execution only.
- Required primitive: explicit facility authority in the mandate. Existing prepaid wallet authority is not enough.
- Required audit: every decision must reconstruct the request, mandate snapshot, policy result, risk assessment, evidence hashes, facility snapshot, and liability assignment.

## Non-Custodial Boundary

Sardis may approve, deny, step up, revoke, and record authority. Sardis must not be the repayment obligor, lender of record, custodian of prefunded balances, issuer of live credentials, or collections system in v1.

## Event Taxonomy

- `facility.request.created`
- `facility.evidence.attached`
- `facility.authorization.approved`
- `facility.authorization.denied`
- `facility.authorization.step_up_required`
- `facility.approval.recorded`
- `facility.execution.simulated`
- `facility.revocation.created`
- `facility.exception.created`

## API Contract

- `POST /api/v2/facility-requests`
- `POST /api/v2/facility-requests/{request_id}/authorize`
- `POST /api/v2/facility-requests/{request_id}/evidence`
- `POST /api/v2/facility-requests/{request_id}/approval`
- `POST /api/v2/facility-requests/{request_id}/execute`
- `GET /api/v2/facility-requests/{request_id}/audit`
- `GET /api/v2/facility-requests/manual-review`
- `GET /api/v2/facility-requests/exceptions`
- `POST /api/v2/facility-requests/revocations`

All endpoints are feature-flagged with `SARDIS_FACILITY_GATE_ENABLED=true`.

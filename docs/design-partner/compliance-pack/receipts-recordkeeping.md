# Receipts and Recordkeeping Controls

Date: 2026-03-04

## Receipt Delivery

For regulated money movement and card funding events:

1. Generate receipt URL or equivalent provider artifact.
2. Deliver receipt to user via dashboard and/or email.
3. Include fee disclosures for charged fees.
4. Persist receipt metadata in audit/event storage.

## Record Retention

Minimum artifacts to retain:

1. Customer consent records for account opening/terms acceptance.
2. Marketing and UI snapshots shown at onboarding.
3. Customer communications (support emails/tickets).
4. Statements (if provided) and transaction receipts.

## Repository Evidence Paths

1. Treasury/card webhook audit path: `packages/sardis-api/src/sardis_api/repositories/treasury_repository.py`
2. Compliance execution gate: `scripts/release/compliance_execution_check.sh`
3. Readiness gate: `scripts/release/readiness_check.sh`


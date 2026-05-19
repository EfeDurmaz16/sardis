# PCI Approvals And Database Hardening Checklist

Sardis should avoid handling raw PAN data whenever provider-hosted flows can
preserve the product behavior. Break-glass PAN entry is allowed only when the
provider profile, environment, and approval controls explicitly allow it.

## PCI Boundary

- Prefer provider-hosted card detail collection and reveal flows.
- Do not log PAN, CVV, card secrets, provider credentials, or raw webhook
  secrets.
- Redact audit payloads before persistence.
- Require shared secret storage in production-like secure checkout execution.
- Keep provider boundary mode deterministic and visible through the security
  policy endpoint.

## Approval Controls

- Configure distinct reviewer quorum for sensitive checkout execution.
- Reject approvals from the same reviewer when distinct quorum is required.
- Record approval reason, reviewer identity, timestamp, rail, and request id.
- Treat missing policy snapshot signer configuration as fail-closed in
  production-like environments.

## Database Hardening

- Do not silently fall back to in-memory stores in production-like modes.
- Migrations must create required trust, approval, evidence, and idempotency
  tables before enabling live rails.
- Payment execution records should retain idempotency hash and policy snapshot
  references for replay analysis.

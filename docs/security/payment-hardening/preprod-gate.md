# Payment Hardening Pre-Production Gate

This gate defines the minimum controls that must be true before a production-like
payment flow is enabled for a pilot or design partner environment.

## Required Controls

- Policy enforcement must run before signing, issuing, settling, refunding, or
  forwarding a payment request.
- Signed policy snapshots must be required for production-like secure checkout
  and on-chain execution paths.
- Prompt-injection and goal-drift signals must fail closed into approval or
  rejection paths.
- Idempotency keys must be preserved across retries and replay attempts.
- Evidence export cursors must be scoped to the requesting principal and must
  not be replayable across tenants.
- Card/PAN execution must use provider-hosted flows unless an explicit,
  approved break-glass mode is configured.
- Trust-table mutations for A2A peers must require approval when quorum
  controls are enabled.

## Validation

Run the release gate before enabling a production-like payment environment:

```bash
bash scripts/release/payment_hardening_gate.sh
RUN_PAYMENT_HARDENING_TESTS=1 bash scripts/release/payment_hardening_gate.sh
```

## Rollback

If any control regresses, disable the affected payment rail or environment flag,
revoke outstanding approval sessions, and keep the flow in simulation mode until
the gate passes again.

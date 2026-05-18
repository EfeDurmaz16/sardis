# Escrow Governance Timelock

Escrow and refund governance must be slow enough to review, but not so slow that
fund recovery becomes impossible during an incident.

## Required Controls

- Arbiter changes must be proposed before execution.
- Governance executor changes must have a pending state and an execution delay.
- Ownership transfer must be governance-gated in strict mode.
- Lockup policy changes must enforce a maximum lockup bound.
- Early-withdrawal or refund override paths must include replay protection and
  typed authorization where the active contract supports it.

## Validation

Run:

```bash
bash scripts/release/escrow_governance_check.sh
```

The gate validates either the current `RefundProtocol` surface or the legacy
`SardisEscrow` timelock surface, then runs forge tests when Foundry is
available.

## Rollback

If a governance release fails validation, do not deploy the affected contract.
Revert to the last audited contract artifact and keep disputed payment flows in
manual review until the timelock surface passes.

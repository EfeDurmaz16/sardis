# Key Governance

This runbook defines the public governance expectations for policy signer and
MPC-backed payment authority keys. Private provider credential procedures live
outside this repository.

## Required Controls

- Governance signer rotation must be explicit, reviewable, and auditable.
- Policy signer changes must be gated by the on-chain policy module or smart
  account authority surface.
- MPC provider configuration must be declared through environment/config fields,
  not hardcoded provider credentials.
- Production-like environments must document the active provider, signing
  authority, rotation owner, emergency revocation path, and evidence location.

## Validation

Run:

```bash
bash scripts/release/key_governance_check.sh
```

The gate checks the supported contract surface, key-provider config fields, and
key rotation tests.

## Incident Response

If a signer is suspected to be compromised, disable live execution, rotate the
policy signer through the governed path, invalidate queued approvals that
depended on the old signer, and preserve evidence for every failed or blocked
request during the incident window.

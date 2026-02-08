# Design Partner Readiness

This folder contains the staging hardening checklist used for the design partner program.

## Files

- `staging-hardening-checklist.json`: source of truth for engineering and launch gates.

## Validation

Validate engineering-only gates:

```bash
python3 scripts/check_design_partner_readiness.py --scope engineering
```

Validate full paid launch gates:

```bash
python3 scripts/check_design_partner_readiness.py --scope launch
```

## Gate semantics

- `engineering` scope: blocks merges/releases only on engineering-critical gates.
- `launch` scope: includes operational and legal/commercial gates required before paid partner launch.


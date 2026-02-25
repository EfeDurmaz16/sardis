# Payment Hardening Pre-Prod Gate

## Purpose
This gate blocks promotion when critical payment safety controls are missing.

Scope:
- Deterministic policy enforcement + policy pin fail-closed behavior
- Prompt-injection/jailbreak containment
- Evidence export replay-safe pagination + signature verification path
- PAN lane isolation (runtime readiness, reveal validation, audit redaction)
- Funding failover chaos coverage

## Commands
Quick structural gate:

```bash
bash scripts/release/payment_hardening_gate.sh
```

Strict gate with targeted tests:

```bash
RUN_PAYMENT_HARDENING_TESTS=1 bash scripts/release/payment_hardening_gate.sh
```

## Pass Criteria
All checks must pass:
- Required docs exist (`payment-hardening-slo-alerts`, PCI checklist)
- On-chain router includes policy pin fail-closed controls
- Compliance export includes replay-safe cursor scope binding
- Secure checkout rejects invalid PAN reveal payloads and redacts audit payloads
- Chaos/adversarial tests are present and executable

## Recommended Pre-Prod Sequence
1. Run payment gate in strict mode.
2. Run full release gate: `bash scripts/release/readiness_check.sh`.
3. Verify staging env vars for PAN executor runtime in production profile:
   - `SARDIS_CHECKOUT_EXECUTOR_DISPATCH_URL`
   - `SARDIS_CHECKOUT_DISPATCH_REQUIRED=1`
   - `SARDIS_CHECKOUT_EXECUTOR_TOKEN`
   - `SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION=1`
   - `SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY`
4. Validate funding failover behavior in staging (primary unavailable -> fallback success / all-failed alerting path).

## Failure Handling
If this gate fails:
- treat as release blocker,
- open an incident task against `payment-hardening` owner,
- attach failing command output and impacted file paths.

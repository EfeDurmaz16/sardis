# Payment Hardening Pre-Prod Gate

## Purpose
This gate blocks promotion when critical payment safety controls are missing.

Scope:
- Deterministic policy enforcement + policy pin fail-closed behavior
- Prompt-injection/jailbreak containment
- Evidence export replay-safe pagination + signature verification path
- PAN lane isolation (runtime readiness, reveal validation, audit redaction)
- Shared secret store enforcement for multi-instance PAN execution
- Severity-based risk response (freeze/rotate/cooldown + ops approval gate)
- A2A trust-table enforcement for multi-agent peer payments
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
- Secure checkout fails closed in prod when shared secret store is missing
- Risk incident taxonomy + response orchestration code paths are present
- A2A trust relation checks exist and are test-covered
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
   - `SARDIS_CHECKOUT_ALLOW_INMEMORY_SECRET_STORE=0`
4. Verify incident response config:
   - `SARDIS_CHECKOUT_AUTO_FREEZE_ON_SECURITY_INCIDENT=1`
   - `SARDIS_CHECKOUT_AUTO_ROTATE_ON_SECURITY_INCIDENT=1` (optional by risk appetite)
   - `SARDIS_CHECKOUT_AUTO_UNFREEZE_ON_SECURITY_INCIDENT=1` only with:
     - `SARDIS_CHECKOUT_AUTO_UNFREEZE_OPS_APPROVED=1`
     - severity allowlist + cooldowns explicitly set.
5. Verify A2A trust-table config:
   - `SARDIS_A2A_ENFORCE_TRUST_TABLE=1`
   - `SARDIS_A2A_TRUST_RELATIONS=sender_agent_id>recipient_a|recipient_b,...`
   - `SARDIS_A2A_TRUST_RELATION_MUTATION_REQUIRE_APPROVAL=1`
   - `SARDIS_A2A_TRUST_RELATION_MUTATION_ALLOWED_ACTIONS=a2a_trust_mutation,a2a_trust_relation_change`
   - `SARDIS_A2A_TRUST_RELATION_MUTATION_MIN_APPROVALS=2` (distinct reviewers / 4-eyes)
   - Ensure DB migration created `a2a_trust_relations` before production boot.
   - `GET /api/v2/a2a/trust/table` returns expected relations.
   - `GET /api/v2/a2a/trust/peers?sender_agent_id=...` returns only trusted peers by default.
   - `GET /api/v2/a2a/trust/security-policy` matches expected runtime guardrails.
   - `POST/DELETE /api/v2/a2a/trust/relations` responses include `audit_id` and are exported by compliance audit evidence APIs.
   - `GET /api/v2/a2a/trust/audit/recent` shows latest trust mutation entries for org.
6. Validate funding failover behavior in staging (primary unavailable -> fallback success / all-failed alerting path).
7. Validate on-chain goal-drift controls:
   - `SARDIS_GOAL_DRIFT_REVIEW_THRESHOLD` and `SARDIS_GOAL_DRIFT_BLOCK_THRESHOLD` set explicitly.
   - Drift in review band triggers approval; drift above block threshold is denied fail-closed.

## Failure Handling
If this gate fails:
- treat as release blocker,
- open an incident task against `payment-hardening` owner,
- attach failing command output and impacted file paths.

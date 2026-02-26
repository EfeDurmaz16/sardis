# Control Testing Cadence (Q1 2026)

Date: 2026-02-26  
Owner: Compliance Engineering

## Weekly Controls

| Control ID | Objective | Test/Check | Owner |
| --- | --- | --- | --- |
| `CTRL-POLICY-IMMUTABLE` | Hard limits cannot be bypassed by NL prompt | `pytest packages/sardis-core/tests/test_nl_policy_parser_hard_limits.py` | Core Platform |
| `CTRL-ATTEST-INTEGRITY` | Policy attestation and chain integrity remain valid | `pytest packages/sardis-core/tests/test_policy_attestation.py` | Core Platform |
| `CTRL-COMPLIANCE-GATE` | Compliance gate blocks invalid/unsafe payment requests | `pytest packages/sardis-api/tests/test_compliance_gate.py` | API Team |

## Monthly Controls

| Control ID | Objective | Test/Check | Owner |
| --- | --- | --- | --- |
| `CTRL-AUDIT-STORE` | Audit store writes/reads preserve evidence integrity | `pytest packages/sardis-compliance/tests/test_audit_store_async.py` | Compliance Team |
| `CTRL-OPS-ALERTING` | Alert routing/cooldown runbook remains executable | `bash scripts/release/ops_readiness_check.sh` | SRE |
| `CTRL-PROVIDER-CERT` | Live-lane provider certification artifacts remain valid | `bash scripts/release/provider_live_lane_cert_check.sh` | Integrations |

## Quarterly Controls

| Control ID | Objective | Test/Check | Owner |
| --- | --- | --- | --- |
| `CTRL-DR-ROLLBACK` | Incident and rollback drills remain actionable | `bash scripts/release/mainnet_ops_drill_check.sh` | SRE + Security |
| `CTRL-COMPLIANCE-EXEC` | Compliance execution pack is complete | `bash scripts/release/compliance_execution_check.sh` | Compliance Engineering |

## Escalation Policy

1. A failed weekly control blocks new production releases until resolved or explicitly waived by engineering + compliance owners.
2. A failed monthly/quarterly control requires CAPA entry with target remediation date.
3. Repeat failures on the same control in two consecutive runs escalate to SEV-2 internal compliance incident.

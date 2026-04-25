# Facility Gate Pilot Activation Runbook

Status: pilot gate

Use this runbook only after the simulator tabletop harness passes. Facility Gate remains a control plane for partner-backed authority; this runbook does not authorize live card issuance or Sardis balance-sheet lending.

## 1. Required Evidence Before Enablement

Run and archive the output from:

```bash
uv run python packages/sardis-api/scripts/facility_gate_pilot_tabletop.py --output /tmp/facility_gate_tabletop.json
SARDIS_FACILITY_GATE_ENABLED=true \
SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY=true \
SARDIS_FACILITY_GATE_ORG_ALLOWLIST=<pilot_org_id> \
  uv run python packages/sardis-api/scripts/facility_gate_pilot_readiness.py <pilot_org_id> \
    --run-tabletop \
    --require-alerts \
    --output /tmp/facility_gate_readiness.json
uv run pytest packages/sardis-api/tests/test_facility_gate_pilot_tabletop.py -q
uv run pytest packages/sardis-api/tests/test_facility_gate_repository.py packages/sardis-api/tests/test_facility_requests_router.py packages/sardis-api/tests/test_facility_adapter_contract.py packages/sardis-api/tests/test_facility_gate_limits.py packages/sardis-api/tests/test_facility_gate_migration.py packages/sardis-api/tests/test_facility_gate_authority.py -q
```

If a real Postgres DSN is available, also run:

```bash
SARDIS_TEST_POSTGRES_DSN=postgresql://... uv run pytest packages/sardis-api/tests/test_facility_gate_migration.py -q
```

## 2. Pilot Feature Flags

| Flag | Pilot Value | Production Default | Why |
|---|---|---|---|
| `SARDIS_FACILITY_GATE_ENABLED` | `true` only for pilot API deployment/org routing | `false` | Avoid accidental broad exposure. |
| `SARDIS_FACILITY_GATE_ORG_ALLOWLIST` | comma-separated pilot org IDs; use `*` only in isolated test environments | unset | Restrict enabled Facility Gate routes to approved pilot organizations. |
| `SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY` | `true` | `true` before any pilot | Prevent request-provided mandate/facility authority truth. |
| `SARDIS_FACILITY_PROVIDER_WEBHOOKS_ENABLED` | `false` for simulator-only pilot; `true` only for provider sandbox | `false` | Avoid accepting provider-shaped state before provider selection. |
| `SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET` | set only in provider sandbox | unset | Required for signed webhook tests. |
| `SARDIS_FACILITY_PROVIDER_WEBHOOK_SECRET_<PROVIDER>` | set only for named provider sandbox | unset | Prefer provider-specific secrets when available. |

Do not introduce a live-provider flag until a named provider adapter passes the contract suite and provider capability map is accepted.

## 3. Pilot Scopes And Roles

Minimum API-key/JWT scopes:

| Actor | Scopes |
|---|---|
| Agent runtime | `facility:write`, `facility:authorize`, `facility:execute`, `facility:read` |
| Finance reviewer | `facility:read`, `facility:review`, `facility:approve`, `facility:audit` |
| Operator | `facility:admin`, `facility:read`, `facility:review`, `facility:audit`, `facility:revoke` |
| Authority seeder | `facility:admin`, `facility:write` |

Wildcard scope is acceptable only for local tabletop and internal test orgs.

## 4. Required Pilot Seed Data

Before enabling a pilot org, seed or verify:

- facility record: `organization_id`, `facility_id`, `sponsor_id`, active status, per-transaction limit, allowed categories, approval threshold, version
- facility policy record: policy version, limit snapshot, allowed categories, evidence requirements if configured
- facility mandate record: agent-bound mandate, explicit `facility_authority_allowed`, allowed facility IDs, max draw, allowed rails, version
- operator roles: review, approval, audit, revoke
- dashboard access: `/facility-gate`

Strict mode should reject any request that lacks persisted mandate/facility authority.

## 5. Pilot Operating Bounds

- Categories: cloud, API, SaaS, developer tooling.
- Rail: simulator, or provider sandbox only after contract tests pass.
- Amounts: low per-transaction cap; temporary increases require human approval.
- Evidence: required for novel merchants, weak task graph, high amount, or limit increase.
- Manual review: required for step-up, novel merchant, weak evidence, approval fatigue, suspicious probing.
- Revocation: agent, merchant, mandate, facility, and global scopes must be available to the operator.

## 6. Go / No-Go Checklist

Go only if:

- tabletop harness returns `status: passed`
- pilot readiness report returns `status: passed`
- focused Facility Gate tests pass
- real Postgres migration test passes in CI or with supplied DSN
- alert inventory is mirrored into the selected alert backend or manually configured with evidence
- Facility Gate Grafana dashboard or equivalent panels are available
- incident runbook has been reviewed by the pilot operator
- pilot org has scoped feature flag enablement
- provider mode is simulator-only or sandbox-only

No-go if:

- strict persisted authority is disabled
- dashboard/operator role access is unclear
- alert destinations are not configured
- real provider live execution is requested before sandbox evidence
- audit export lacks decision packet hash, version refs, or event hash-chain verification

## 7. Pilot Day Procedure

1. Confirm feature flags and scopes.
2. Run the pilot readiness script with `--run-tabletop --require-alerts` and archive output.
3. Seed facility, mandate, and policy records.
4. Create a low-risk request and verify automatic approval.
5. Create a step-up request and verify manual review.
6. Approve the step-up and verify resumed authorization.
7. Execute simulator credential and verify duplicate execute is idempotent.
8. Export audit and verify decision packet hash, version refs, evidence refs, liability, and event hash chain.
9. Revoke the pilot agent and verify a future authorization is denied.
10. Run projection replay dry-run and verify zero drift.

## 8. Rollback

Immediate rollback order:

1. Disable `SARDIS_FACILITY_GATE_ENABLED` for the pilot org/deployment.
2. Revoke `global` or `organization` scope if the API remains reachable.
3. Disable provider webhooks if enabled.
4. Preserve audit exports, exception events, provider payload hashes, and replay output.
5. Run projection replay dry-run.
6. Open incident using `incident-runbook.md`.

Do not delete events. Corrections must append events.

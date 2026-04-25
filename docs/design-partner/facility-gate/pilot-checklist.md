# Facility Gate Pilot Checklist

Status: pilot gate

## Required Before Pilot

- [ ] `SARDIS_FACILITY_GATE_ENABLED=true` is paired with `SARDIS_FACILITY_GATE_ORG_ALLOWLIST=<pilot_org_ids>`; wildcard allowlist is not used outside isolated test environments.
- [ ] Pilot readiness script returns `status: passed` for the pilot org with `--run-tabletop --require-alerts`.
- [ ] Facility Gate `030` Postgres migration test passes with `SARDIS_TEST_POSTGRES_DSN`; CI now provisions this through `.github/workflows/test-api.yml`, and local ephemeral Postgres validation has passed.
- [ ] Focused Facility Gate core/API tests pass.
- [ ] Projection replay dry-run succeeds for pilot org.
- [ ] Audit export returns a decision packet with version refs and hash.
- [ ] Strict persisted-authority mode works for mandate and facility lookup.
- [ ] Duplicate execute returns the existing credential without another adapter call.
- [ ] Revocation blocks authorization and execution.
- [ ] Manual review queue is monitored.
- [ ] Exception list is monitored.
- [ ] Internal dashboard `/facility-gate` is reachable for the pilot operator.
- [ ] Python SDK and MCP Facility Gate request/authorize/audit surfaces pass focused tests.
- [ ] Facility Gate alert inventory and Prometheus-compatible rules exist for exceptions, adapter failures, revocation propagation failure, manual-review backlog, denial/step-up spikes, projection drift, and replay absence.
- [ ] Facility Gate alert inventory is either wired to the selected alert backend or manually mirrored into Sentry/Grafana with evidence captured.
- [ ] Facility Gate Grafana dashboard template is imported or equivalent dashboard panels exist for pilot operations.
- [ ] Pilot activation runbook is followed and evidence is archived.
- [ ] Incident runbook is reviewed by the operator.
- [ ] Threat model residual risks are accepted for pilot.

## Pilot Tabletop Harness

Run the readiness gate before enabling a pilot org:

```bash
SARDIS_FACILITY_GATE_ENABLED=true \
SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY=true \
SARDIS_FACILITY_GATE_ORG_ALLOWLIST=<pilot_org_id> \
  uv run python packages/sardis-api/scripts/facility_gate_pilot_readiness.py <pilot_org_id> \
    --run-tabletop \
    --require-alerts \
    --output /tmp/facility_gate_readiness.json
```

The readiness report must return `status: passed`.

The simulator-only tabletop can still be run directly for focused rehearsal:

```bash
uv run python packages/sardis-api/scripts/facility_gate_pilot_tabletop.py --output /tmp/facility_gate_tabletop.json
```

The report must return:

- `status: passed`
- approved request path succeeds
- duplicate execute is idempotent
- audit export includes decision packet hash and version references
- step-up request appears in manual review
- human approval resumes authorization
- revocation blocks future authorization
- projection replay reports zero drift

## Provider-Specific Gate

Only required if pilot uses a provider beyond the simulator.

- [ ] Adapter contract test suite passes for the provider skeleton or sandbox.
- [ ] Provider capability map is complete for a named provider.
- [ ] Live provider flag is off by default.
- [ ] Webhook signature verification is enabled.
- [ ] Webhook dedupe is tested.
- [ ] Settlement/capture provider events normalize into append-only settlement updates.
- [ ] Provider outage mode is documented.

## Pilot Operating Constraints

- Low transaction limits.
- Narrow categories: cloud, API, SaaS, developer tooling.
- No consumer spend.
- No direct Sardis lending.
- No high-limit autonomous spend.
- Manual review required for novel merchants, weak evidence, high amounts, and temporary limit expansion.

# Facility Gate P2 Completion Status

Status: implementation-complete pending external pilot inputs

## Completed P2 Surfaces

- Postgres-oriented migration coverage exists for Facility Gate event, request state, facility record, policy record, mandate record, webhook, and repayment mirror tables.
- The Facility Gate `030` Alembic migration has been validated against a real ephemeral Postgres cluster with `stamp 029 -> upgrade 030 -> inspect tables/indexes/constraints -> downgrade 029`.
- Replay and projection tooling exists for rebuilding Facility Gate request state from append-only events.
- Authorization now supports persisted facility, policy, and mandate version lookups instead of relying only on request-provided snapshots.
- Decision packets include version references, considered evidence, liability, risk, and audit-export surfaces.
- Step-up can integrate with the Sardis approvals service behind the Facility Gate approval integration flag.
- Operator/admin APIs can seed facility, policy, and mandate authority records for strict persisted authorization.
- Concurrency and failure tests cover duplicate authorization, duplicate execution, revocation races, projection failure, adapter failure, approval service failure, and idempotency paths.
- Durable rate limiting and approval fatigue controls are implemented behind the Facility Gate limiter abstraction.
- Adapter contract tests cover approved-only execution, duplicate execute, revoke-before-execute, unsupported capabilities, and provider error behavior.
- Provider preparation includes a disabled mock provider skeleton, provider capability map, webhook ingestion model, settlement event normalization, and repayment/delinquency mirror model.
- Python SDK exposes `client.facility_gate` for request, evidence, authorize, execute, audit, audit export, list, manual review, approval recording, revocation, exceptions, and limits.
- MCP server exposes agent-facing Facility Gate tools for request, evidence, authorize, execute, audit, audit export, and list.
- Dashboard exposes an internal Facility Gate page for request inspection, manual-review pressure, limiter snapshot, audit copy/export, and scoped agent revocation.
- Monitoring now includes Facility Gate metrics for decisions, adapter events, revocations, exceptions, manual-review depth, projection replay runs, and projection drift.
- Alert inventory, Prometheus-compatible rules, and Grafana dashboard templates include Facility Gate exception, adapter failure, revocation propagation, manual-review backlog, decision spike, replay absence, and projection drift surfaces.
- A simulator-only pilot tabletop harness exercises strict persisted authority, approved execution, duplicate execute idempotency, audit export, step-up/manual approval, revocation blocking, and projection replay.
- A pilot readiness gate now checks global Facility Gate enablement, strict persisted authority, org allowlist membership, alert/dashboard artifacts, and optionally runs the tabletop harness; CI uploads `facility-gate-readiness.json`.
- Facility Gate route enablement now supports `SARDIS_FACILITY_GATE_ORG_ALLOWLIST` so pilot exposure can be restricted by organization while keeping provider webhook enablement separate.
- Threat model, incident runbook, provider capability map, pilot checklist, and pilot activation runbook exist under this folder.

## Remaining External Gates

- Real Postgres migration execution is wired into `.github/workflows/test-api.yml` through a Postgres 16 service and `SARDIS_TEST_POSTGRES_DSN`.
- `.github/workflows/test-api.yml` also runs the Facility Gate pilot tabletop and readiness harnesses, uploading `facility-gate-tabletop.json` and `facility-gate-readiness.json` as CI evidence.
- Local real-Postgres validation can run with Homebrew/Postgres binaries or a supplied `SARDIS_TEST_POSTGRES_DSN`; the latest local ephemeral Postgres run passed for Facility Gate `030`.
- Real provider integration remains intentionally disabled until a provider is selected, sandbox credentials are configured, and capability gaps are accepted.
- Live card issuance remains out of scope until simulator, adapter contract, webhook, revocation, replay, and audit export checks are accepted for pilot.
- Production rollout still requires concrete pilot org IDs in `SARDIS_FACILITY_GATE_ORG_ALLOWLIST`, operator role assignment, alert destination configuration, and a pilot tabletop run.

## Verification Snapshot

- Core Facility Gate tests: `uv run pytest packages/sardis-core/tests/test_facility_gate.py -q`
- API Facility Gate focused tests: `uv run pytest packages/sardis-api/tests/test_facility_gate_repository.py packages/sardis-api/tests/test_facility_requests_router.py packages/sardis-api/tests/test_facility_adapter_contract.py packages/sardis-api/tests/test_facility_gate_limits.py packages/sardis-api/tests/test_facility_gate_migration.py packages/sardis-api/tests/test_facility_gate_authority.py -q`
- Local ephemeral Postgres migration gate: start a temporary Postgres cluster and run `SARDIS_TEST_POSTGRES_DSN=postgresql://... uv run pytest packages/sardis-api/tests/test_facility_gate_migration.py -q`
- SDK Facility Gate tests: `uv run pytest packages/sardis-sdk-python/tests/test_facility_gate.py packages/sardis-sdk-python/tests/test_client.py -q`
- MCP typecheck: `npm run typecheck` from `packages/sardis-mcp-server`
- MCP targeted tests: `npm run test -- facility-gate server mandates payments` from `packages/sardis-mcp-server`
- Dashboard typecheck: `npm run typecheck` from `apps/dashboard`
- Dashboard lint: `npm run lint` from `apps/dashboard`
- API CI workflow syntax: `ruby -e "require 'yaml'; YAML.load_file('.github/workflows/test-api.yml')"`
- CI tabletop artifact: `.github/workflows/test-api.yml` uploads `facility-gate-tabletop.json` as `facility-gate-tabletop`.
- Alert inventory syntax: `ruby -e "require 'yaml'; YAML.load_file('monitoring/alerts.yml')"`
- Facility Gate Prometheus rule syntax: `ruby -e "require 'yaml'; YAML.load_file('monitoring/facility-gate-prometheus-rules.yml')"`
- Grafana dashboard syntax: `find ops/grafana -maxdepth 1 -type f -name '*.json' -print -exec ruby -e 'require "json"; JSON.parse(File.read(ARGV[0]))' {} \;`
- Pilot tabletop harness: `uv run python packages/sardis-api/scripts/facility_gate_pilot_tabletop.py`
- Pilot tabletop regression: `uv run pytest packages/sardis-api/tests/test_facility_gate_pilot_tabletop.py -q`
- Pilot readiness harness: `SARDIS_FACILITY_GATE_ENABLED=true SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY=true SARDIS_FACILITY_GATE_ORG_ALLOWLIST=org_tabletop uv run python packages/sardis-api/scripts/facility_gate_pilot_readiness.py org_tabletop --run-tabletop --require-alerts`
- Pilot readiness regression: `uv run pytest packages/sardis-api/tests/test_facility_gate_pilot_readiness.py -q`

# CPN + Warm Issuing 30-Day Execution Plan

Date: 2026-03-04  
Scope: Base mainnet readiness with Circle CPN as active fiat rail and card issuing kept warm/sandbox.

## Goals

1. Ship production-safe CPN payout/collection path.
2. Keep issuer integrations technically ready but not live.
3. Reuse one compliance pack across Stripe/Lithic/Rain/Bridge.
4. Finish a go/no-go packet for issuer live enablement.

## Week 1 (Days 1-7): Rail Stabilization

Deliverables:

1. CPN funding adapter and webhook ingestion in API.
2. Capability matrix shows `circle_cpn` fiat readiness.
3. Production signature/replay protections verified.

Repo focus:

1. `packages/sardis-core/src/sardis_v2_core/cpn_funding_adapter.py`
2. `packages/sardis-api/src/sardis_api/routers/cpn.py`
3. `packages/sardis-api/src/sardis_api/routers/funding_capabilities.py`

Checks:

1. `uv run pytest -q packages/sardis-core/tests/test_cpn_funding_adapter.py`
2. `cd packages/sardis-api && uv run pytest -q tests/test_cpn_webhooks.py tests/test_funding_capabilities.py`

## Week 2 (Days 8-14): Issuer Warm Integration

Deliverables:

1. Issuer-agnostic adapter contract and shim.
2. Production warm-mode gate (`SARDIS_ISSUING_LIVE_ENABLED`) on card issue/fund paths.
3. Provider contract introspection endpoint for readiness visibility.

Repo focus:

1. `packages/sardis-cards/src/sardis_cards/providers/issuing_ports.py`
2. `packages/sardis-cards/src/sardis_cards/providers/issuer_adapter.py`
3. `packages/sardis-api/src/sardis_api/routers/cards.py`

Checks:

1. `cd packages/sardis-api && uv run pytest -q tests/test_cards_provider_introspection.py tests/test_cards_warm_mode_gate.py`
2. `PYTHONPATH=packages/sardis-cards/src uv run pytest -q packages/sardis-cards/tests/test_issuer_adapter.py`

## Week 3 (Days 15-21): Compliance Pack + Ops Evidence

Deliverables:

1. Reusable compliance pack documentation complete.
2. Complaints/disputes + receipts + retention controls evidenced.
3. Release gate validates compliance pack presence.

Repo focus:

1. `docs/design-partner/compliance-pack/`
2. `scripts/release/issuer_compliance_pack_check.sh`
3. `scripts/release/readiness_check.sh`

Checks:

1. `bash scripts/release/issuer_compliance_pack_check.sh`
2. `bash scripts/release/compliance_execution_check.sh`

## Week 4 (Days 22-30): Mainnet Readiness and Go/No-Go

Deliverables:

1. Base mainnet readiness checks green.
2. Issuer launch packet prepared (still warm by default).
3. Explicit live toggle procedure approved.

Repo focus:

1. `scripts/release/base_mainnet_readiness_check.sh`
2. `scripts/release/cpn_warm_issuing_check.sh`
3. `scripts/check_release_readiness.sh`
4. `docs/design-partner/mainnet-proof-and-rollback-runbook.md`

Checks:

1. `bash scripts/release/base_mainnet_readiness_check.sh`
2. `bash scripts/release/cpn_warm_issuing_check.sh`
3. `bash scripts/check_release_readiness.sh`

## Exit Criteria (Day 30)

1. CPN path stable and monitored.
2. Issuing integration warm-ready with no accidental live issuance risk.
3. Compliance artifacts current and reviewable.
4. Live issuing can be enabled only via explicit governance decision and env toggle.

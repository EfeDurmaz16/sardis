# Nightly Sandbox E2E Runbook

Date: 2026-02-26
Owner: Sardis Platform

## Purpose

Run a nightly sandbox pipeline that always validates deterministic payment hardening controls, and optionally runs live provider sandbox checks when secrets are available.

## Workflow

- GitHub Actions workflow: `.github/workflows/nightly-sandbox-e2e.yml`
- Runner script: `scripts/ci/run_nightly_sandbox_smoke.sh`
- Schedule: daily at `04:20 UTC`

## What runs every night (deterministic)

1. Issuer readiness snapshot (`scripts/check_issuer_readiness.py`)
2. Provider contract matrix tests:
   - `packages/sardis-cards/tests/test_provider_contract_matrix.py`
3. Webhook idempotency safety:
   - `packages/sardis-api/tests/test_partner_card_webhooks.py::test_partner_webhook_duplicate_event_is_idempotent`
4. Agent endpoint limiter hardening:
   - `tests/test_agent_payment_rate_limit.py`
5. ERC-4337 guardrail checks:
   - `tests/test_erc4337_guardrails.py`

## Optional live sandbox stage

Enable by setting `RUN_LIVE_SANDBOX_TESTS=1` (via workflow dispatch input `run_live_sandbox=true`).

Required secrets:
- `STRIPE_API_KEY`
- `LITHIC_API_KEY`
- `COINBASE_CDP_API_KEY_NAME`
- `COINBASE_CDP_API_KEY_PRIVATE_KEY`

Optional deploy probe:
- `SARDIS_SANDBOX_BASE_URL` (runs `/health` and `/api/v2/health` probes)

If live mode is enabled and required secrets are missing, the job fails fast with exit code `2`.

## Failure handling

1. Read failing test/service from workflow logs.
2. If provider sandbox flake is suspected, re-run via `workflow_dispatch`.
3. If deterministic suite fails, block merges touching payment routing, policy, approval, cards, or signer paths until fixed.
4. Record incident summary under `docs/design-partner/incident-response-247-drill.md`.

## Local dry-run

```bash
bash scripts/ci/run_nightly_sandbox_smoke.sh
```

Live local run:

```bash
RUN_LIVE_SANDBOX_TESTS=1 \
STRIPE_API_KEY=... \
LITHIC_API_KEY=... \
COINBASE_CDP_API_KEY_NAME=... \
COINBASE_CDP_API_KEY_PRIVATE_KEY=... \
bash scripts/ci/run_nightly_sandbox_smoke.sh
```

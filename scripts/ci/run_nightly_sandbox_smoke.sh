#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH="${ROOT_DIR}/packages/sardis-cards/src:${ROOT_DIR}/packages/sardis-api/src:${ROOT_DIR}/packages/sardis-core/src:${ROOT_DIR}/packages/sardis-ledger/src:${ROOT_DIR}/packages/sardis-protocol/src:${PYTHONPATH:-}"

echo "[nightly] Sardis sandbox smoke started at $(date -u +%Y-%m-%dT%H:%M:%SZ)"

echo "[nightly] Issuer readiness snapshot"
python3 scripts/check_issuer_readiness.py

echo "[nightly] Running deterministic provider/policy smoke tests"
python3 -m pytest -q packages/sardis-cards/tests/test_provider_contract_matrix.py
python3 -m pytest -q packages/sardis-api/tests/test_partner_card_webhooks.py::test_partner_webhook_duplicate_event_is_idempotent
python3 -m pytest -q tests/test_agent_payment_rate_limit.py tests/test_erc4337_guardrails.py

if [[ -n "${SARDIS_SANDBOX_BASE_URL:-}" ]]; then
  echo "[nightly] Probing deployed sandbox API at ${SARDIS_SANDBOX_BASE_URL}"
  curl --fail --silent --show-error --max-time 20 "${SARDIS_SANDBOX_BASE_URL%/}/health" >/tmp/sardis_nightly_health.json
  curl --fail --silent --show-error --max-time 20 "${SARDIS_SANDBOX_BASE_URL%/}/api/v2/health" >/tmp/sardis_nightly_api_v2_health.json
  echo "[nightly] API health probes passed"
else
  echo "[nightly] SARDIS_SANDBOX_BASE_URL not set; skipping remote API probes"
fi

if [[ "${RUN_LIVE_SANDBOX_TESTS:-0}" == "1" ]]; then
  echo "[nightly] Live sandbox mode enabled"
  missing=()
  [[ -z "${STRIPE_API_KEY:-}" ]] && missing+=("STRIPE_API_KEY")
  [[ -z "${LITHIC_API_KEY:-}" ]] && missing+=("LITHIC_API_KEY")
  [[ -z "${COINBASE_CDP_API_KEY_NAME:-}" ]] && missing+=("COINBASE_CDP_API_KEY_NAME")
  [[ -z "${COINBASE_CDP_API_KEY_PRIVATE_KEY:-}" ]] && missing+=("COINBASE_CDP_API_KEY_PRIVATE_KEY")

  if [[ ${#missing[@]} -gt 0 ]]; then
    echo "[nightly] Live sandbox tests requested but missing env: ${missing[*]}"
    exit 2
  fi

  echo "[nightly] Running live sandbox E2E subset"
  python3 -m pytest -q \
    tests/e2e/test_cards_fiat_flow.py \
    tests/e2e/test_base_sepolia_e2e.py
else
  echo "[nightly] RUN_LIVE_SANDBOX_TESTS != 1; skipping live sandbox E2E subset"
fi

echo "[nightly] Sardis sandbox smoke completed successfully"

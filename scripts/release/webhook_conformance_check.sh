#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[webhook-conformance] running webhook signature/replay/idempotency tests"

export SARDIS_ENVIRONMENT="${SARDIS_ENVIRONMENT:-dev}"
export SARDIS_SECRET_KEY="${SARDIS_SECRET_KEY:-test-secret-key-for-webhook-conformance-32chars}"
export SARDIS_TEST_API_KEY="${SARDIS_TEST_API_KEY:-sk_test_demo123}"

pytest -q packages/sardis-api/tests/test_middleware_security.py
pytest -q tests/test_checkout_webhook_security.py
pytest -q tests/test_webhooks.py
pytest -q tests/test_audit_f12_replay_cache.py

echo "[webhook-conformance] pass"

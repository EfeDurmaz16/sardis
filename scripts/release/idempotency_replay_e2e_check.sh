#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[idempotency-e2e] validating payment/webhook replay + idempotency guarantees"

python3 -m pytest -q packages/sardis-api/tests/test_partner_card_webhooks.py::test_partner_webhook_duplicate_event_is_idempotent
python3 -m pytest -q packages/sardis-api/tests/test_executor_worker.py::test_worker_dispatch_idempotency_by_job_id
python3 -m pytest -q packages/sardis-api/tests/test_secure_checkout_executor.py::test_completion_callback_is_idempotent_with_idempotency_key
python3 -m pytest -q packages/sardis-api/tests/test_secure_checkout_executor.py::test_executor_attestation_replay_is_rejected
python3 -m pytest -q packages/sardis-api/tests/test_idempotency.py::TestIdempotencyEdgeCases::test_replay_attack_prevention
python3 -m pytest -q tests/test_audit_f12_replay_cache.py

echo "[idempotency-e2e] pass"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[critical] running integration smoke checks for payment/policy/wallet lifecycle"
pytest -q \
  tests/test_protocol_stack_integration.py \
  tests/test_cross_tenant_isolation.py \
  tests/integration/test_full_scenario.py

echo "[critical] running wallet lifecycle contract e2e smoke check"
FOUNDRY_OFFLINE=true forge test --root contracts --match-test test_E2E_WalletLifecycle

echo "[critical] critical-path checks passed"

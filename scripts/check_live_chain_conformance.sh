#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STRICT_MODE="${STRICT_MODE:-0}"

echo "[live-chain] Starting live-chain conformance checks (STRICT_MODE=${STRICT_MODE})"

required_env=(
  TURNKEY_API_PUBLIC_KEY
  TURNKEY_API_PRIVATE_KEY
  TURNKEY_ORGANIZATION_ID
  SARDIS_TURNKEY__DEFAULT_WALLET_ID
)

missing=()
for key in "${required_env[@]}"; do
  if [[ -z "${!key:-}" ]]; then
    missing+=("$key")
  fi
done

if [[ ${#missing[@]} -gt 0 ]]; then
  echo "[live-chain] Missing required environment variables:"
  for key in "${missing[@]}"; do
    echo "  - $key"
  done
  if [[ "$STRICT_MODE" == "1" ]]; then
    echo "[live-chain] STRICT_MODE=1 -> failing due to missing live-chain credentials."
    exit 1
  fi
  echo "[live-chain] Skipping live-chain tests (set env vars above to enable)."
  exit 0
fi

echo "[live-chain] Credentials detected. Running live-chain integration tests..."
(
  cd "$ROOT_DIR"
  SARDIS_RUN_LIVE_CHAIN_TESTS=1 \
  pytest -v --tb=short \
    tests/integration/test_turnkey_eth_transfer.py \
    tests/integration/test_usdc_transfer.py
)

echo "[live-chain] Live-chain conformance checks completed."

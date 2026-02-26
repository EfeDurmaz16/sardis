#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[a2a-live-settlement] validating on-chain A2A settlement path"

TARGET_FILE="packages/sardis-core/src/sardis_v2_core/a2a_settlement.py"

if rg -q "generate a simulated tx_hash|TODO: Integrate with chain executor" "$TARGET_FILE"; then
  echo "[a2a-live-settlement][fail] simulated settlement markers still present in $TARGET_FILE"
  exit 1
fi

python3 -m pytest -q packages/sardis-core/tests/test_a2a_settlement.py

echo "[a2a-live-settlement] pass"

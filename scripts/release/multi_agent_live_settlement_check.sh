#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[multi-agent] validating live multi-agent settlement path"

failures=0

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[multi-agent][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

forbid_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if rg -q "$pattern" "$file"; then
    echo "[multi-agent][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

TARGET_FILE="packages/sardis-core/src/sardis_v2_core/multi_agent_payments.py"
require_match 'dispatch_payment' "$TARGET_FILE" "multi-agent flow must dispatch via chain executor when configured"
require_match '_evaluate_leg_trust' "$TARGET_FILE" "multi-agent flow must evaluate trust before execution"
forbid_match 'tx_hash = f"0x\{uuid4\(\)\.hex\}"' "$TARGET_FILE" "legacy uuid mock tx hashes must be removed"

if [[ "$failures" -gt 0 ]]; then
  echo "[multi-agent] completed with $failures failure(s)"
  exit 1
fi

python3 -m pytest -q packages/sardis-core/tests/test_multi_agent_payments_live_execution.py

echo "[multi-agent] pass"

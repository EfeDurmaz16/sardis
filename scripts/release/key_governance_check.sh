#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[key-governance] validating policy signer + MPC governance artifacts"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[key-governance][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[key-governance][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/policy-signer-mpc-key-governance-runbook.md"
require_match 'setPolicySigner' contracts/src/SardisSmartAccount.sol "smart account must support policy signer rotation"
require_match 'TURNKEY_' packages/sardis-core/src/sardis_v2_core/config.py "config must include turnkey surface"
require_match 'FIREBLOCKS_API_KEY' packages/sardis-core/src/sardis_v2_core/config.py "config validation must include fireblocks surface"

if [[ "$failures" -gt 0 ]]; then
  echo "[key-governance] completed with $failures failure(s)"
  exit 1
fi

python3 -m pytest -q packages/sardis-core/tests/test_key_rotation.py

echo "[key-governance] pass"

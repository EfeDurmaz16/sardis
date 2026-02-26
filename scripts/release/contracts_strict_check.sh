#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[contracts-strict] running strict forge checks"

if ! command -v forge >/dev/null 2>&1; then
  echo "[contracts-strict][fail] forge not found"
  exit 1
fi

cd contracts
forge fmt --check
forge build --profile ci --sizes -vv
forge test --profile ci -vvv

echo "[contracts-strict] pass"

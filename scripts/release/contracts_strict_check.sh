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

if ! grep -Eq '^solc_version = "0\.8\.24"$' foundry.toml; then
  echo "[contracts-strict][fail] foundry.toml must pin solc_version to 0.8.24"
  exit 1
fi

if ! grep -Eq '^\[profile\.ci\]' foundry.toml || ! grep -Eq 'fuzz = \{ runs = 50000 \}' foundry.toml; then
  echo "[contracts-strict][fail] CI profile must enforce fuzz runs = 50000"
  exit 1
fi

forge fmt --check
forge build --profile ci --sizes -vv
forge test --profile ci -vvv

echo "[contracts-strict] pass"

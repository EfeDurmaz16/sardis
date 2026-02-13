#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

failures=0

extract_toml_version() {
  local file="$1"
  rg -No '^version = "[^"]+"' "$file" | head -n1 | sed -E 's/version = "([^"]+)"/\1/'
}

extract_py_version() {
  local file="$1"
  rg -No '^__version__ = "[^"]+"' "$file" | head -n1 | sed -E 's/__version__ = "([^"]+)"/\1/'
}

echo "[version] checking root sardis package version parity"
root_toml_version="$(extract_toml_version pyproject.toml)"
root_init_version="$(extract_py_version sardis/__init__.py)"
if [[ "$root_toml_version" != "$root_init_version" ]]; then
  echo "[version][fail] root version mismatch: pyproject=$root_toml_version, sardis/__init__.py=$root_init_version"
  failures=$((failures + 1))
else
  echo "[version][pass] root sardis version: $root_toml_version"
fi

echo "[version] checking Python SDK version parity"
py_sdk_toml_version="$(extract_toml_version packages/sardis-sdk-python/pyproject.toml)"
py_sdk_init_version="$(extract_py_version packages/sardis-sdk-python/src/sardis_sdk/__init__.py)"
py_sdk_client_version="$(extract_py_version packages/sardis-sdk-python/src/sardis_sdk/client.py)"
if [[ "$py_sdk_toml_version" != "$py_sdk_init_version" || "$py_sdk_toml_version" != "$py_sdk_client_version" ]]; then
  echo "[version][fail] Python SDK version mismatch: pyproject=$py_sdk_toml_version, __init__=$py_sdk_init_version, client=$py_sdk_client_version"
  failures=$((failures + 1))
else
  echo "[version][pass] Python SDK version: $py_sdk_toml_version"
fi

echo "[version] checking TypeScript SDK version parity"
ts_sdk_pkg_version="$(node -p "require('./packages/sardis-sdk-js/package.json').version")"
ts_sdk_client_version="$(rg -No "const SDK_VERSION = '[^']+'" packages/sardis-sdk-js/src/client.ts | sed -E "s/const SDK_VERSION = '([^']+)'/\\1/")"
if [[ "$ts_sdk_pkg_version" != "$ts_sdk_client_version" ]]; then
  echo "[version][fail] TypeScript SDK version mismatch: package.json=$ts_sdk_pkg_version, client.ts=$ts_sdk_client_version"
  failures=$((failures + 1))
else
  echo "[version][pass] TypeScript SDK version: $ts_sdk_pkg_version"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[version] completed with $failures failure(s)"
  exit 1
fi

echo "[version] all version checks passed"

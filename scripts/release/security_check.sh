#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[security] starting checks"

failures=0

check_cmd() {
  local cmd="$1"
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "[security][fail] required command missing: $cmd"
    failures=$((failures + 1))
  fi
}

check_cmd rg
check_cmd git

if [[ "$failures" -gt 0 ]]; then
  echo "[security] failed preflight ($failures issue(s))"
  exit 1
fi

echo "[security] checking .gitignore coverage"
for pattern in ".env" ".env.local" ".env*.local" ".venv/"; do
  if ! rg -q --fixed-strings "$pattern" .gitignore; then
    echo "[security][fail] missing .gitignore pattern: $pattern"
    failures=$((failures + 1))
  fi
done

echo "[security] scanning for private key material"
private_key_hits="$(rg -n -e "-----BEGIN (RSA|EC|OPENSSH|PRIVATE) KEY-----" \
  --glob '!**/node_modules/**' --glob '!**/.venv/**' --glob '!**/dist/**' . || true)"
if [[ -n "$private_key_hits" ]]; then
  echo "[security][fail] private key material found:"
  echo "$private_key_hits"
  failures=$((failures + 1))
else
  echo "[security][pass] no private key material found"
fi

echo "[security] scanning for suspicious live API key literals"
live_key_hits="$(rg -n "sk_live_[A-Za-z0-9]{8,}" \
  --glob '!**/node_modules/**' --glob '!**/.venv/**' --glob '!**/dist/**' . \
  | rg -v "your|YOUR|example|abc|xxx|demo|openapi" || true)"
if [[ -n "$live_key_hits" ]]; then
  echo "[security][fail] suspicious live API key literals found:"
  echo "$live_key_hits"
  failures=$((failures + 1))
else
  echo "[security][pass] no suspicious live API key literals found"
fi

echo "[security] checking publish manifests for workspace dependencies"
workspace_hits="$(rg -n "workspace:" packages/*/package.json || true)"
if [[ -n "$workspace_hits" ]]; then
  echo "[security][fail] workspace dependency references detected:"
  echo "$workspace_hits"
  failures=$((failures + 1))
else
  echo "[security][pass] no workspace dependency references in package manifests"
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[security] completed with $failures failure(s)"
  exit 1
fi

echo "[security] all checks passed"

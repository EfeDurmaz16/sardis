#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

tmp_runtime="$(mktemp)"
tmp_documented="$(mktemp)"
trap 'rm -f "$tmp_runtime" "$tmp_documented"' EXIT

echo "[env-doc] scanning runtime env variable usage"
rg -No \
  "os\\.getenv\\(\\s*\\\"[A-Z0-9_]+\\\"|os\\.environ\\.get\\(\\s*\\\"[A-Z0-9_]+\\\"|os\\.environ\\[\\s*\\\"[A-Z0-9_]+\\\"" \
  packages/sardis-api/src \
  packages/sardis-core/src \
  packages/sardis-wallet/src \
  --glob '*.py' \
  | sed -E 's/.*\"([A-Z0-9_]+)\".*/\1/' \
  | sort -u > "$tmp_runtime"

echo "[env-doc] scanning .env.example"
rg -No "^[[:space:]]*#?[[:space:]]*[A-Z][A-Z0-9_]*=" .env.example \
  | sed -E 's/^[[:space:]]*#?[[:space:]]*([A-Z][A-Z0-9_]*)=.*/\1/' \
  | sort -u > "$tmp_documented"

missing="$(comm -23 "$tmp_runtime" "$tmp_documented" || true)"

if [[ -n "$missing" ]]; then
  echo "[env-doc][fail] runtime env vars missing from .env.example:"
  echo "$missing"
  exit 1
fi

runtime_count="$(wc -l < "$tmp_runtime" | tr -d ' ')"
documented_count="$(wc -l < "$tmp_documented" | tr -d ' ')"
echo "[env-doc][pass] documented all runtime env vars (runtime=$runtime_count, documented=$documented_count)"

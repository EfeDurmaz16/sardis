#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[demo-proof-assets] validating demo proof assets"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[demo-proof-assets][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[demo-proof-assets][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "scripts/investor_demo_flow.py"
require_file "scripts/release/demo_proof_check.sh"
require_file "docs/design-partner/demo-proof-flow-runbook.md"

require_match "simulate_denied_purchase" scripts/investor_demo_flow.py "investor demo must include denied scenario"
require_match "simulate_allowed_purchase" scripts/investor_demo_flow.py "investor demo must include allowed scenario"
require_match "verify_ledger_entry" scripts/investor_demo_flow.py "investor demo must include ledger verification step"

if ! python3 scripts/investor_demo_flow.py --help >/dev/null; then
  echo "[demo-proof-assets][fail] investor demo script --help failed"
  failures=$((failures + 1))
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[demo-proof-assets] completed with $failures failure(s)"
  exit 1
fi

echo "[demo-proof-assets] pass"

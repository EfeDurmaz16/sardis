#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[reconciliation-chaos] validating reconciliation chaos coverage"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[reconciliation-chaos][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[reconciliation-chaos][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/reconciliation-load-chaos-slos.md"
require_file "tests/test_canonical_ledger_repository.py"
require_file "tests/test_reconciliation_engine_load.py"
require_file "tests/test_treasury_ops_api.py"

require_match 'SLO' docs/design-partner/reconciliation-load-chaos-slos.md "runbook must define reconciliation SLOs"
require_match 'out-of-order' docs/design-partner/reconciliation-load-chaos-slos.md "runbook must include out-of-order scenario"
require_match 'Duplicate event suppression' docs/design-partner/reconciliation-load-chaos-slos.md "runbook must include duplicate suppression target"

if ! pytest -q tests/test_canonical_ledger_repository.py tests/test_reconciliation_engine_load.py tests/test_treasury_ops_api.py; then
  echo "[reconciliation-chaos][fail] reconciliation test suite failed"
  failures=$((failures + 1))
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[reconciliation-chaos] completed with $failures failure(s)"
  exit 1
fi

echo "[reconciliation-chaos] pass"


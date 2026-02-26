#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[mainnet-ops-drill] validating mainnet proof + incident drill artifacts"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[mainnet-ops-drill][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[mainnet-ops-drill][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/mainnet-proof-and-rollback-runbook.md"
require_file "docs/design-partner/incident-response-247-drill.md"
require_file "docs/audits/evidence/turnkey-outage-drill-latest.json"

require_match 'Rollback' docs/design-partner/mainnet-proof-and-rollback-runbook.md "mainnet runbook must include rollback steps"
require_match 'Cloud Run' docs/design-partner/mainnet-proof-and-rollback-runbook.md "mainnet runbook must include API rollback surface"
require_match 'ack' docs/design-partner/incident-response-247-drill.md "incident runbook must define ack targets"
require_match 'SEV-1' docs/design-partner/incident-response-247-drill.md "incident runbook must define severity levels"

if [[ "$failures" -gt 0 ]]; then
  echo "[mainnet-ops-drill] completed with $failures failure(s)"
  exit 1
fi

echo "[mainnet-ops-drill] validating measured RTO/RPO evidence"
bash scripts/release/drill_metrics_check.sh

echo "[mainnet-ops-drill] pass"

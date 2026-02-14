#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[ops-readiness] validating ops SLO/alert/rollback artifacts"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[ops-readiness][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[ops-readiness][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/ops-slo-alerts-rollback-runbook.md"
require_file "scripts/health_monitor.sh"
require_file ".github/workflows/monitoring.yml"

require_match 'schedule:' .github/workflows/monitoring.yml "monitoring workflow must run on a schedule"
require_match 'SLACK_WEBHOOK_URL' .github/workflows/monitoring.yml "monitoring workflow must support slack alerting"
require_match 'api/v2/health' .github/workflows/monitoring.yml "monitoring workflow must check API health endpoint"

require_match 'SLO' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must define SLOs"
require_match 'Rollback' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must define rollback procedures"
require_match 'Cloud Run' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must include API rollback"
require_match 'Vercel' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must include frontend rollback"

if [[ "$failures" -gt 0 ]]; then
  echo "[ops-readiness] completed with $failures failure(s)"
  exit 1
fi

echo "[ops-readiness] pass"

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
require_file "docs/design-partner/mainnet-proof-and-rollback-runbook.md"
require_file "docs/design-partner/incident-response-247-drill.md"
require_file "docs/design-partner/reconciliation-load-chaos-slos.md"
require_file "scripts/health_monitor.sh"
require_file ".github/workflows/monitoring.yml"

require_match 'schedule:' .github/workflows/monitoring.yml "monitoring workflow must run on a schedule"
require_match 'SLACK_WEBHOOK_URL' .github/workflows/monitoring.yml "monitoring workflow must support slack alerting"
require_match 'api/v2/health' .github/workflows/monitoring.yml "monitoring workflow must check API health endpoint"

require_match 'SLO' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must define SLOs"
require_match 'Rollback' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must define rollback procedures"
require_match 'Cloud Run' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must include API rollback"
require_match 'Vercel' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must include frontend rollback"
require_match 'SARDIS_ALERT_SEVERITY_CHANNELS_JSON' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must document severity routing"
require_match 'SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must document cooldown tuning"
require_match 'Mainnet' docs/design-partner/mainnet-proof-and-rollback-runbook.md "mainnet proof runbook must be explicit"
require_match 'SEV-1' docs/design-partner/incident-response-247-drill.md "incident drill doc must define severity tiers"
require_match 'SLO' docs/design-partner/reconciliation-load-chaos-slos.md "reconciliation chaos doc must define SLOs"

echo "[ops-readiness] running alert routing smoke tests"
python3 -m pytest -q \
  packages/sardis-core/tests/test_alert_channels.py::test_dispatcher_uses_severity_channel_map \
  packages/sardis-core/tests/test_alert_channels.py::test_dispatcher_cooldown_suppresses_duplicate

if [[ "$failures" -gt 0 ]]; then
  echo "[ops-readiness] completed with $failures failure(s)"
  exit 1
fi

echo "[ops-readiness] pass"

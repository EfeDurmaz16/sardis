#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[ops-readiness] validating ops SLO/alert/rollback artifacts"

failures=0
strict_mode="${SARDIS_STRICT_RELEASE_GATES:-0}"
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
if [[ "$environment" == "prod" || "$environment" == "production" ]]; then
  strict_mode=1
fi
strict_arg=""
if [[ "$strict_mode" == "1" || "$strict_mode" == "true" ]]; then
  strict_arg="--strict-routing"
  echo "[ops-readiness] strict routing mode enabled"
fi

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
require_file "docs/audits/evidence/turnkey-outage-drill-latest.json"
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
require_match 'PAGERDUTY_ROUTING_KEY' docs/design-partner/ops-slo-alerts-rollback-runbook.md "ops runbook must document PagerDuty routing"
require_match 'PagerDuty' docs/design-partner/incident-response-247-drill.md "incident drill doc must include PagerDuty escalation path"
require_match 'Mainnet' docs/design-partner/mainnet-proof-and-rollback-runbook.md "mainnet proof runbook must be explicit"
require_match 'SEV-1' docs/design-partner/incident-response-247-drill.md "incident drill doc must define severity tiers"
require_match 'SLO' docs/design-partner/reconciliation-load-chaos-slos.md "reconciliation chaos doc must define SLOs"

echo "[ops-readiness] running alert routing smoke tests"
python3 -m pytest -q \
  packages/sardis-core/tests/test_alert_channels.py::test_dispatcher_uses_severity_channel_map \
  packages/sardis-core/tests/test_alert_channels.py::test_dispatcher_cooldown_suppresses_duplicate \
  packages/sardis-core/tests/test_alert_channels.py::test_pagerduty_channel_send_success \
  packages/sardis-core/tests/test_alert_channels.py::test_pagerduty_channel_send_fails_on_non_success_status

echo "[ops-readiness] generating ops evidence artifact"
python3 scripts/release/generate_ops_readiness_evidence.py \
  --drill-evidence docs/audits/evidence/turnkey-outage-drill-latest.json \
  --output docs/audits/evidence/ops-readiness-latest.json \
  $strict_arg

require_file "docs/audits/evidence/ops-readiness-latest.json"
require_match '"routing_checks"' docs/audits/evidence/ops-readiness-latest.json "ops evidence must include routing checks"

if [[ "$failures" -gt 0 ]]; then
  echo "[ops-readiness] completed with $failures failure(s)"
  exit 1
fi

echo "[ops-readiness] pass"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

EVIDENCE_FILE="${SARDIS_DRILL_EVIDENCE_FILE:-docs/audits/evidence/turnkey-outage-drill-latest.json}"
MAX_FAILOVER_RTO_MIN="${SARDIS_DRILL_MAX_FAILOVER_RTO_MIN:-15}"
MAX_RECOVERY_RTO_MIN="${SARDIS_DRILL_MAX_RECOVERY_RTO_MIN:-60}"
MAX_RPO_SEC="${SARDIS_DRILL_MAX_RPO_SEC:-0}"

echo "[drill-metrics] validating DR evidence file: ${EVIDENCE_FILE}"
python3 scripts/release/validate_drill_metrics.py \
  --evidence "${EVIDENCE_FILE}" \
  --max-failover-rto-min "${MAX_FAILOVER_RTO_MIN}" \
  --max-recovery-rto-min "${MAX_RECOVERY_RTO_MIN}" \
  --max-rpo-sec "${MAX_RPO_SEC}"

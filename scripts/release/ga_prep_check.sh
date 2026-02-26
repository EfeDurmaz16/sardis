#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[ga-prep] validating GA prep artifacts"

failures=0

require_file() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    echo "[ga-prep][fail] missing file: $file"
    failures=$((failures + 1))
  fi
}

require_match() {
  local pattern="$1"
  local file="$2"
  local message="$3"
  if ! rg -q "$pattern" "$file"; then
    echo "[ga-prep][fail] $message ($file)"
    failures=$((failures + 1))
  fi
}

require_file "docs/design-partner/ga-prep-execution-pack-q1-2026.md"
require_file "docs/design-partner/mainnet-proof-and-rollback-runbook.md"
require_file "docs/design-partner/readiness-execution-checklist.md"

require_match '/api/v2' docs/design-partner/ga-prep-execution-pack-q1-2026.md "ga prep doc must define stable API version"
require_match 'X-API-Version' docs/design-partner/ga-prep-execution-pack-q1-2026.md "ga prep doc must require API version headers"
require_match 'provider_live_lane_cert_check.sh' docs/design-partner/ga-prep-execution-pack-q1-2026.md "ga prep doc must include provider cert gate"
require_match 'mainnet_ops_drill_check.sh' docs/design-partner/ga-prep-execution-pack-q1-2026.md "ga prep doc must include rollback drill gate"

if [[ "$failures" -gt 0 ]]; then
  echo "[ga-prep] completed with $failures failure(s)"
  exit 1
fi

echo "[ga-prep] running launch automation checks"
python3 scripts/check_design_partner_readiness.py --scope launch --max-review-age-days 60
bash scripts/release/provider_live_lane_cert_check.sh
bash scripts/release/mainnet_ops_drill_check.sh
python3 -m pytest -q packages/sardis-api/tests/test_middleware_security.py -k api_version_header

STRICT_MODE="${SARDIS_GA_STRICT:-0}"
ENVIRONMENT="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
if [[ "$ENVIRONMENT" == "prod" || "$ENVIRONMENT" == "production" ]]; then
  STRICT_MODE=1
fi
STRICT_ARG=""
if [[ "$STRICT_MODE" == "1" || "$STRICT_MODE" == "true" ]]; then
  STRICT_ARG="--strict"
  echo "[ga-prep] strict mode enabled"
fi

if [[ "$STRICT_MODE" == "1" || "$STRICT_MODE" == "true" ]]; then
  export SARDIS_PROVIDER_CERT_STRICT=1
fi

python3 scripts/release/generate_enterprise_ga_readiness_artifact.py $STRICT_ARG

if [[ ! -f "docs/audits/evidence/enterprise-ga-readiness-latest.json" ]]; then
  echo "[ga-prep][fail] missing enterprise GA readiness artifact"
  exit 1
fi

echo "[ga-prep] pass"

#!/usr/bin/env bash
# =============================================================================
# Sardis Mainnet Verification Script
# =============================================================================
#
# Runs post-deploy smoke tests against a Sardis API deployment.
#
# Usage:
#   ./scripts/verify-mainnet.sh                 # defaults to staging
#   ./scripts/verify-mainnet.sh production       # test production
#   ./scripts/verify-mainnet.sh staging          # test staging
#   API_URL=https://custom.url ./scripts/verify-mainnet.sh
#
# Exit codes:
#   0 — all checks passed
#   1 — one or more checks failed
#
# =============================================================================
set -euo pipefail

ENVIRONMENT="${1:-staging}"
PASS=0
FAIL=0
WARN=0

# Resolve API URL
if [[ -n "${API_URL:-}" ]]; then
  BASE_URL="$API_URL"
elif [[ "$ENVIRONMENT" == "production" ]]; then
  BASE_URL="https://api.sardis.sh"
else
  BASE_URL="https://sardis-api-staging-$(gcloud run services describe sardis-api-staging \
    --project="${GOOGLE_CLOUD_PROJECT:-sardis-staging-01}" \
    --region="${CLOUD_RUN_REGION:-us-east1}" \
    --format='value(status.url)' 2>/dev/null || echo 'unknown')"
  # Fallback: use gcloud to get full URL
  if [[ "$BASE_URL" == *"unknown" ]]; then
    BASE_URL=$(gcloud run services describe sardis-api-staging \
      --project="${GOOGLE_CLOUD_PROJECT:-sardis-staging-01}" \
      --region="${CLOUD_RUN_REGION:-us-east1}" \
      --format='value(status.url)' 2>/dev/null || echo "")
  fi
fi

if [[ -z "$BASE_URL" ]]; then
  echo "ERROR: Could not resolve API URL. Set API_URL env var or ensure gcloud is configured."
  exit 1
fi

echo "=============================================="
echo "  Sardis Mainnet Verification"
echo "=============================================="
echo "  Environment: $ENVIRONMENT"
echo "  API URL:     $BASE_URL"
echo "  Timestamp:   $(date -u +%Y-%m-%dT%H:%M:%SZ)"
echo ""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

check_pass() {
  echo "  [PASS] $1"
  PASS=$((PASS + 1))
}

check_fail() {
  echo "  [FAIL] $1"
  FAIL=$((FAIL + 1))
}

check_warn() {
  echo "  [WARN] $1"
  WARN=$((WARN + 1))
}

# ---------------------------------------------------------------------------
# 1. API Liveness
# ---------------------------------------------------------------------------
echo "--- 1. API Liveness ---"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$BASE_URL/health/live" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  check_pass "Liveness probe (/health/live) returned 200"
else
  check_fail "Liveness probe returned $HTTP_CODE (expected 200)"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$BASE_URL/ready" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  check_pass "Readiness probe (/ready) returned 200"
else
  check_fail "Readiness probe returned $HTTP_CODE (expected 200)"
fi

echo ""

# ---------------------------------------------------------------------------
# 2. Deep Health Check
# ---------------------------------------------------------------------------
echo "--- 2. Deep Health Check ---"

HEALTH_JSON=$(curl -s --connect-timeout 15 "$BASE_URL/health" 2>/dev/null || echo '{"status":"unreachable"}')
HEALTH_STATUS=$(echo "$HEALTH_JSON" | python3 -c "import json,sys; print(json.load(sys.stdin).get('status','unknown'))" 2>/dev/null || echo "parse_error")

if [[ "$HEALTH_STATUS" == "healthy" ]]; then
  check_pass "Health status: healthy"
elif [[ "$HEALTH_STATUS" == "partial" ]]; then
  check_warn "Health status: partial (non-critical failures present)"
else
  check_fail "Health status: $HEALTH_STATUS (expected healthy)"
fi

# Check individual components
for COMPONENT in database cache rpc turnkey contracts; do
  COMP_STATUS=$(echo "$HEALTH_JSON" | python3 -c "
import json, sys
h = json.load(sys.stdin)
print(h.get('components', {}).get('$COMPONENT', {}).get('status', 'missing'))
" 2>/dev/null || echo "parse_error")

  if [[ "$COMP_STATUS" == "healthy" ]]; then
    check_pass "Component $COMPONENT: $COMP_STATUS"
  elif [[ "$COMP_STATUS" == "unconfigured" && "$ENVIRONMENT" != "production" ]]; then
    check_warn "Component $COMPONENT: $COMP_STATUS (OK for non-prod)"
  else
    check_fail "Component $COMPONENT: $COMP_STATUS"
  fi
done

# Check custody posture
CUSTODY_NC=$(echo "$HEALTH_JSON" | python3 -c "
import json, sys
h = json.load(sys.stdin)
print(h.get('components', {}).get('custody', {}).get('non_custodial', False))
" 2>/dev/null || echo "False")

if [[ "$ENVIRONMENT" == "production" ]]; then
  if [[ "$CUSTODY_NC" == "True" ]]; then
    check_pass "Custody posture: non-custodial MPC"
  else
    check_fail "Custody posture: NOT non-custodial (required for production)"
  fi
else
  check_warn "Custody posture: non_custodial=$CUSTODY_NC (non-prod, skipping strict check)"
fi

# Check critical failures
CRIT_COUNT=$(echo "$HEALTH_JSON" | python3 -c "
import json, sys
h = json.load(sys.stdin)
print(len(h.get('critical_failures', [])))
" 2>/dev/null || echo "-1")

if [[ "$CRIT_COUNT" == "0" ]]; then
  check_pass "No critical failures"
else
  check_fail "$CRIT_COUNT critical failure(s) detected"
  echo "$HEALTH_JSON" | python3 -c "
import json, sys
h = json.load(sys.stdin)
for f in h.get('critical_failures', []):
    print(f'         - {f.get(\"component\")}: {f.get(\"reason_code\")} — {f.get(\"detail\")}')" 2>/dev/null || true
fi

# Execution mode
EXEC_MODE=$(echo "$HEALTH_JSON" | python3 -c "
import json, sys; print(json.load(sys.stdin).get('execution_mode', 'unknown'))
" 2>/dev/null || echo "unknown")

if [[ "$ENVIRONMENT" == "production" ]]; then
  if [[ "$EXEC_MODE" == "production_live" ]]; then
    check_pass "Execution mode: production_live"
  else
    check_fail "Execution mode: $EXEC_MODE (expected production_live)"
  fi
else
  check_pass "Execution mode: $EXEC_MODE"
fi

echo ""

# ---------------------------------------------------------------------------
# 3. API Discovery
# ---------------------------------------------------------------------------
echo "--- 3. API Discovery ---"

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$BASE_URL/" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  check_pass "Root endpoint (/) returned 200"
else
  check_fail "Root endpoint returned $HTTP_CODE"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$BASE_URL/api/v2/health" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  check_pass "API v2 health (/api/v2/health) returned 200"
else
  check_fail "API v2 health returned $HTTP_CODE"
fi

HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --connect-timeout 10 "$BASE_URL/api/v2/docs" 2>/dev/null || echo "000")
if [[ "$HTTP_CODE" == "200" ]]; then
  check_pass "OpenAPI docs (/api/v2/docs) returned 200"
else
  check_warn "OpenAPI docs returned $HTTP_CODE (may not be enabled)"
fi

echo ""

# ---------------------------------------------------------------------------
# 4. Required Environment Variables
# ---------------------------------------------------------------------------
echo "--- 4. Environment Variable Check (local) ---"

REQUIRED_VARS=(
  DATABASE_URL
  SARDIS_SECRET_KEY
  JWT_SECRET_KEY
  SARDIS_REDIS_URL
  SARDIS_BASE_RPC_URL
)

PROD_REQUIRED_VARS=(
  TURNKEY_API_PUBLIC_KEY
  TURNKEY_API_PRIVATE_KEY
  TURNKEY_ORGANIZATION_ID
  SARDIS_BASE_LEDGER_ANCHOR_ADDRESS
  SARDIS_BASE_JOB_REGISTRY_ADDRESS
  SARDIS_BASE_JOB_MANAGER_ADDRESS
)

for VAR in "${REQUIRED_VARS[@]}"; do
  if [[ -n "${!VAR:-}" ]]; then
    check_pass "$VAR is set"
  else
    if [[ "$ENVIRONMENT" == "production" ]]; then
      check_fail "$VAR is NOT set (required)"
    else
      check_warn "$VAR is not set locally (check Cloud Run config)"
    fi
  fi
done

if [[ "$ENVIRONMENT" == "production" ]]; then
  for VAR in "${PROD_REQUIRED_VARS[@]}"; do
    if [[ -n "${!VAR:-}" ]]; then
      check_pass "$VAR is set"
    else
      check_fail "$VAR is NOT set (required for production)"
    fi
  done
fi

echo ""

# ---------------------------------------------------------------------------
# 5. Contract Address Validation
# ---------------------------------------------------------------------------
echo "--- 5. Contract Address Validation ---"

# Check Tempo contracts from deployments/tempo.json
TEMPO_FILE="$(dirname "$0")/../contracts/deployments/tempo.json"
if [[ -f "$TEMPO_FILE" ]]; then
  TEMPO_STATUS=$(python3 -c "
import json
with open('$TEMPO_FILE') as f:
    d = json.load(f)
    contracts = d.get('contracts', {})
    deployed = sum(1 for c in contracts.values() if c.get('address'))
    total = len(contracts)
    print(f'{deployed}/{total}')
" 2>/dev/null || echo "error")
  check_pass "Tempo contracts deployed: $TEMPO_STATUS"
else
  check_warn "Tempo deployment file not found"
fi

# Check Base contracts
BASE_FILE="$(dirname "$0")/../contracts/deployments/base.json"
if [[ -f "$BASE_FILE" ]]; then
  BASE_PENDING=$(python3 -c "
import json
with open('$BASE_FILE') as f:
    d = json.load(f)
    contracts = d.get('contracts', {})
    pending = [name for name, c in contracts.items() if c.get('lifecycle') == 'pending_deploy' and c.get('source') == 'custom']
    if pending:
        print(', '.join(pending))
    else:
        print('none')
" 2>/dev/null || echo "error")

  if [[ "$BASE_PENDING" == "none" ]]; then
    check_pass "All Base custom contracts deployed"
  else
    if [[ "$ENVIRONMENT" == "production" ]]; then
      check_fail "Base contracts pending deployment: $BASE_PENDING"
    else
      check_warn "Base contracts pending deployment: $BASE_PENDING"
    fi
  fi
else
  check_fail "Base deployment file not found"
fi

echo ""

# ---------------------------------------------------------------------------
# 6. Database Migration Status
# ---------------------------------------------------------------------------
echo "--- 6. Database Migration Status ---"

if [[ -n "${DATABASE_URL:-}" ]]; then
  LATEST_MIGRATION=$(psql "$DATABASE_URL" -t -A -c "SELECT version FROM schema_migrations ORDER BY version DESC LIMIT 1;" 2>/dev/null || echo "error")
  if [[ "$LATEST_MIGRATION" == "089" ]]; then
    check_pass "Latest migration: $LATEST_MIGRATION (up to date)"
  elif [[ "$LATEST_MIGRATION" == "error" ]]; then
    check_fail "Could not query schema_migrations table"
  else
    check_warn "Latest migration: $LATEST_MIGRATION (expected 089)"
  fi

  MIGRATION_COUNT=$(psql "$DATABASE_URL" -t -A -c "SELECT COUNT(*) FROM schema_migrations;" 2>/dev/null || echo "error")
  if [[ "$MIGRATION_COUNT" != "error" ]]; then
    check_pass "Total migrations applied: $MIGRATION_COUNT"
  fi
else
  check_warn "DATABASE_URL not set locally, skipping migration check"
fi

echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo "=============================================="
echo "  RESULTS"
echo "=============================================="
echo "  Passed:   $PASS"
echo "  Failed:   $FAIL"
echo "  Warnings: $WARN"
echo ""

if [[ $FAIL -gt 0 ]]; then
  echo "  VERDICT: FAIL -- $FAIL check(s) failed. Fix before proceeding."
  exit 1
else
  if [[ $WARN -gt 0 ]]; then
    echo "  VERDICT: PASS (with $WARN warning(s))"
  else
    echo "  VERDICT: PASS"
  fi
  exit 0
fi

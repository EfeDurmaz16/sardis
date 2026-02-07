#!/usr/bin/env bash
set -euo pipefail

LANDING_BASE_URL="${LANDING_BASE_URL:-}"
DEMO_OPERATOR_PASSWORD="${DEMO_OPERATOR_PASSWORD:-}"

if [[ -z "${LANDING_BASE_URL}" || -z "${DEMO_OPERATOR_PASSWORD}" ]]; then
  cat <<'USAGE'
Usage:
  LANDING_BASE_URL="https://sardis.sh" \
  DEMO_OPERATOR_PASSWORD="your-shared-password" \
  bash ./scripts/check_demo_deploy_readiness.sh

Optional:
  EXPECT_DEMO_EVENTS=1   # fail if /api/demo-events is not writable
USAGE
  exit 1
fi

EXPECT_DEMO_EVENTS="${EXPECT_DEMO_EVENTS:-0}"
TMP_COOKIE="$(mktemp)"
trap 'rm -f "${TMP_COOKIE}"' EXIT

log() {
  printf '[demo-check] %s\n' "$*"
}

require_json_field() {
  local json="$1"
  local field="$2"
  if ! grep -q "\"${field}\"" <<<"${json}"; then
    log "missing field: ${field}"
    log "payload: ${json}"
    exit 1
  fi
}

log "Checking landing health: ${LANDING_BASE_URL}/demo"
curl -fsS "${LANDING_BASE_URL%/}/demo" >/dev/null

log "Checking /api/demo-auth status"
AUTH_STATUS_JSON="$(curl -fsS "${LANDING_BASE_URL%/}/api/demo-auth")"
require_json_field "${AUTH_STATUS_JSON}" "authenticated"
require_json_field "${AUTH_STATUS_JSON}" "liveConfigured"

log "Logging in operator session"
LOGIN_JSON="$(
  curl -fsS -X POST "${LANDING_BASE_URL%/}/api/demo-auth" \
    -H 'Content-Type: application/json' \
    -d "{\"password\":\"${DEMO_OPERATOR_PASSWORD}\"}" \
    -c "${TMP_COOKIE}"
)"
if ! grep -q '"authenticated":true' <<<"${LOGIN_JSON}"; then
  log "operator login failed"
  log "payload: ${LOGIN_JSON}"
  exit 1
fi

run_scenario() {
  local scenario="$1"
  log "Running live scenario: ${scenario}"
  local response
  response="$(
    curl -fsS -X POST "${LANDING_BASE_URL%/}/api/demo-proxy" \
      -H 'Content-Type: application/json' \
      -b "${TMP_COOKIE}" \
      -d "{\"action\":\"run_flow\",\"scenario\":\"${scenario}\"}"
  )"
  if ! grep -q '"ok":true' <<<"${response}"; then
    log "scenario failed: ${scenario}"
    log "payload: ${response}"
    exit 1
  fi
  if [[ "${scenario}" == "blocked" ]] && ! grep -q '"outcome":"blocked"' <<<"${response}"; then
    log "blocked scenario did not produce blocked outcome"
    log "payload: ${response}"
    exit 1
  fi
  if [[ "${scenario}" == "approved" ]] && ! grep -q '"outcome":"approved"' <<<"${response}"; then
    log "approved scenario did not produce approved outcome"
    log "payload: ${response}"
    exit 1
  fi
}

run_scenario "blocked"
run_scenario "approved"

log "Checking demo event ingestion endpoint"
EVENT_HTTP_CODE="$(
  curl -sS -o /tmp/demo-events-response.$$ -w '%{http_code}' \
    -X POST "${LANDING_BASE_URL%/}/api/demo-events" \
    -H 'Content-Type: application/json' \
    -b "${TMP_COOKIE}" \
    -d "{\"runId\":\"smoke_$(date +%s)\",\"mode\":\"live\",\"scenario\":\"approved\",\"eventType\":\"smoke_test\",\"status\":\"ok\"}"
)"
EVENT_BODY="$(cat /tmp/demo-events-response.$$)"
rm -f /tmp/demo-events-response.$$

if [[ "${EVENT_HTTP_CODE}" == "201" ]]; then
  log "demo events: writable (201)"
elif [[ "${EVENT_HTTP_CODE}" == "503" ]]; then
  if [[ "${EXPECT_DEMO_EVENTS}" == "1" ]]; then
    log "demo events expected but unavailable: ${EVENT_BODY}"
    exit 1
  fi
  log "demo events unavailable (503). continue (EXPECT_DEMO_EVENTS=0)"
else
  log "unexpected /api/demo-events status=${EVENT_HTTP_CODE}"
  log "payload: ${EVENT_BODY}"
  exit 1
fi

log "Logging out operator"
curl -fsS -X DELETE "${LANDING_BASE_URL%/}/api/demo-auth" -b "${TMP_COOKIE}" >/dev/null

log "PASS: /demo live mode readiness check completed"

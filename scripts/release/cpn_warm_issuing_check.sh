#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$ROOT_DIR"

echo "[cpn-warm] validating CPN primary rail + warm issuing posture"

failures=0
warnings=0
strict_mode=0
environment="$(echo "${SARDIS_ENVIRONMENT:-dev}" | tr '[:upper:]' '[:lower:]')"
strict_gates="$(echo "${SARDIS_STRICT_RELEASE_GATES:-0}" | tr '[:upper:]' '[:lower:]')"

if [[ "$environment" == "prod" || "$environment" == "production" ]]; then
  strict_mode=1
fi
if [[ "$strict_gates" == "1" || "$strict_gates" == "true" || "$strict_gates" == "yes" || "$strict_gates" == "on" ]]; then
  strict_mode=1
fi

warn_or_fail() {
  local message="$1"
  if [[ "$strict_mode" == "1" ]]; then
    echo "[cpn-warm][fail] $message"
    failures=$((failures + 1))
  else
    echo "[cpn-warm][warn] $message"
    warnings=$((warnings + 1))
  fi
}

normalized_bool() {
  echo "$1" | tr '[:upper:]' '[:lower:]'
}

cpn_enabled="$(normalized_bool "${SARDIS_CIRCLE_CPN__ENABLED:-${CIRCLE_CPN_ENABLED:-false}}")"
cpn_api_key="${SARDIS_CIRCLE_CPN__API_KEY:-${CIRCLE_CPN_API_KEY:-}}"

if [[ "$cpn_enabled" != "1" && "$cpn_enabled" != "true" && "$cpn_enabled" != "yes" && "$cpn_enabled" != "on" ]]; then
  warn_or_fail "CPN rail is not enabled (set SARDIS_CIRCLE_CPN__ENABLED=true)"
fi

if [[ -z "$cpn_api_key" ]]; then
  warn_or_fail "CPN API key missing (set SARDIS_CIRCLE_CPN__API_KEY)"
fi

funding_primary="$(echo "${SARDIS_FUNDING__PRIMARY_ADAPTER:-circle_cpn}" | tr '[:upper:]' '[:lower:]')"
funding_fallback="$(echo "${SARDIS_FUNDING__FALLBACK_ADAPTER:-bridge}" | tr '[:upper:]' '[:lower:]')"

if [[ "$funding_primary" != "circle_cpn" ]]; then
  warn_or_fail "Funding primary adapter should be circle_cpn (current: ${funding_primary:-unset})"
fi

if [[ "$funding_fallback" != "bridge" ]]; then
  warn_or_fail "Funding fallback adapter should be bridge (current: ${funding_fallback:-unset})"
fi

issuing_live_raw="$(normalized_bool "${SARDIS_ISSUING_LIVE_ENABLED:-}")"
if [[ "$strict_mode" == "1" ]]; then
  if [[ -n "$issuing_live_raw" && "$issuing_live_raw" != "0" && "$issuing_live_raw" != "false" && "$issuing_live_raw" != "no" && "$issuing_live_raw" != "off" ]]; then
    echo "[cpn-warm][fail] Issuing live mode must remain disabled in strict mode (SARDIS_ISSUING_LIVE_ENABLED=false)"
    failures=$((failures + 1))
  fi
fi

if [[ "$failures" -gt 0 ]]; then
  echo "[cpn-warm] completed with $failures failure(s)"
  exit 1
fi

echo "[cpn-warm] pass (warnings=$warnings strict=$strict_mode)"

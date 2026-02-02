#!/usr/bin/env bash
set -euo pipefail

# Sardis Health Monitor
# Polls /health endpoint and alerts on failures.
# Usage: HEALTH_URL=https://api.sardis.sh/health WEBHOOK_URL=https://hooks.slack.com/... ./health_monitor.sh

HEALTH_URL="${HEALTH_URL:-http://localhost:8000/health}"
WEBHOOK_URL="${WEBHOOK_URL:-}"
TIMEOUT="${HEALTH_TIMEOUT:-10}"
CRITICAL_COMPONENTS=("database" "rpc" "turnkey")
WARNING_COMPONENTS=("cache" "compliance" "contracts")

timestamp() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

send_alert() {
  local severity="$1" message="$2"
  if [[ -n "$WEBHOOK_URL" ]]; then
    local color="danger"
    [[ "$severity" == "warning" ]] && color="warning"
    local payload
    payload=$(cat <<EOF
{
  "text": "Sardis Health Alert",
  "attachments": [{
    "color": "$color",
    "title": "[$severity] Sardis Health Check",
    "text": "$message",
    "ts": $(date +%s)
  }]
}
EOF
)
    curl -s -X POST -H "Content-Type: application/json" -d "$payload" "$WEBHOOK_URL" >/dev/null 2>&1 || true
  fi
}

# Fetch health endpoint
HTTP_CODE=0
RESPONSE=""
if RESPONSE=$(curl -s -f -w "\n%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null); then
  HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
  RESPONSE=$(echo "$RESPONSE" | sed '$d')
else
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$HEALTH_URL" 2>/dev/null || echo "000")
  RESPONSE=""
fi

NOW=$(timestamp)
EXIT_CODE=0
FAILED_CRITICAL=()
FAILED_WARNING=()
COMPONENTS_JSON="{}"

if [[ -z "$RESPONSE" || "$HTTP_CODE" == "000" ]]; then
  EXIT_CODE=2
  send_alert "critical" "Health endpoint unreachable at $HEALTH_URL (HTTP $HTTP_CODE)"
  cat <<EOF
{
  "timestamp": "$NOW",
  "status": "unreachable",
  "url": "$HEALTH_URL",
  "http_code": "$HTTP_CODE",
  "components": {},
  "failed_critical": [],
  "failed_warning": [],
  "exit_code": $EXIT_CODE
}
EOF
  exit $EXIT_CODE
fi

# Parse component statuses using python if available, else basic grep
if command -v python3 &>/dev/null; then
  COMPONENTS_JSON=$(python3 -c "
import json, sys
try:
    data = json.loads(sys.argv[1])
    components = data.get('components', data.get('checks', data))
    if isinstance(components, dict):
        print(json.dumps(components))
    else:
        print('{}')
except Exception:
    print('{}')
" "$RESPONSE" 2>/dev/null || echo "{}")

  for comp in "${CRITICAL_COMPONENTS[@]}"; do
    status=$(python3 -c "
import json, sys
c = json.loads(sys.argv[1])
v = c.get('$comp', {})
if isinstance(v, dict):
    print(v.get('status', 'unknown'))
elif isinstance(v, str):
    print(v)
else:
    print('unknown')
" "$COMPONENTS_JSON" 2>/dev/null || echo "unknown")
    if [[ "$status" != "healthy" && "$status" != "ok" && "$status" != "up" ]]; then
      FAILED_CRITICAL+=("$comp:$status")
      EXIT_CODE=2
    fi
  done

  for comp in "${WARNING_COMPONENTS[@]}"; do
    status=$(python3 -c "
import json, sys
c = json.loads(sys.argv[1])
v = c.get('$comp', {})
if isinstance(v, dict):
    print(v.get('status', 'unknown'))
elif isinstance(v, str):
    print(v)
else:
    print('unknown')
" "$COMPONENTS_JSON" 2>/dev/null || echo "unknown")
    if [[ "$status" != "healthy" && "$status" != "ok" && "$status" != "up" && "$status" != "unknown" ]]; then
      FAILED_WARNING+=("$comp:$status")
      [[ $EXIT_CODE -eq 0 ]] && EXIT_CODE=1
    fi
  done
else
  # Fallback: treat non-200 as failure
  if [[ "$HTTP_CODE" != "200" ]]; then
    EXIT_CODE=2
    FAILED_CRITICAL+=("http:$HTTP_CODE")
  fi
fi

# Build alerts
if [[ ${#FAILED_CRITICAL[@]} -gt 0 ]]; then
  send_alert "critical" "Critical components unhealthy: ${FAILED_CRITICAL[*]}"
fi
if [[ ${#FAILED_WARNING[@]} -gt 0 ]]; then
  send_alert "warning" "Warning components degraded: ${FAILED_WARNING[*]}"
fi

# Determine overall status
OVERALL="healthy"
[[ ${#FAILED_WARNING[@]} -gt 0 ]] && OVERALL="degraded"
[[ ${#FAILED_CRITICAL[@]} -gt 0 ]] && OVERALL="unhealthy"

# JSON output
CRIT_JSON=$(printf '%s\n' "${FAILED_CRITICAL[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")
WARN_JSON=$(printf '%s\n' "${FAILED_WARNING[@]}" | python3 -c "import json,sys; print(json.dumps([l.strip() for l in sys.stdin if l.strip()]))" 2>/dev/null || echo "[]")

cat <<EOF
{
  "timestamp": "$NOW",
  "status": "$OVERALL",
  "url": "$HEALTH_URL",
  "http_code": "$HTTP_CODE",
  "components": $COMPONENTS_JSON,
  "failed_critical": $CRIT_JSON,
  "failed_warning": $WARN_JSON,
  "exit_code": $EXIT_CODE
}
EOF

exit $EXIT_CODE

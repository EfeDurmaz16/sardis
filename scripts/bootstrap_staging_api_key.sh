#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a staging API key from a deployed Sardis API.
#
# Required env:
#   BASE_URL=https://api-staging.example.com
#   ADMIN_PASSWORD=...
#
# Optional env:
#   ADMIN_USERNAME=admin
#   KEY_NAME="Demo Staging Key"
#   KEY_SCOPES='["admin","*"]'
#   KEY_RATE_LIMIT=200
#   KEY_EXPIRES_DAYS=30

BASE_URL="${BASE_URL:-}"
ADMIN_PASSWORD="${ADMIN_PASSWORD:-}"
ADMIN_USERNAME="${ADMIN_USERNAME:-admin}"
KEY_NAME="${KEY_NAME:-Demo Staging Key}"
KEY_SCOPES="${KEY_SCOPES:-[\"admin\",\"*\"]}"
KEY_RATE_LIMIT="${KEY_RATE_LIMIT:-200}"
KEY_EXPIRES_DAYS="${KEY_EXPIRES_DAYS:-30}"

if [[ -z "$BASE_URL" || -z "$ADMIN_PASSWORD" ]]; then
  echo "Usage:"
  echo "  BASE_URL=https://api-staging... ADMIN_PASSWORD=... bash ./scripts/bootstrap_staging_api_key.sh"
  exit 1
fi

base_trimmed="${BASE_URL%/}"

echo "[1/3] Logging in as admin..."
login_json="$(curl -sS -X POST "${base_trimmed}/api/v2/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  --data-urlencode "username=${ADMIN_USERNAME}" \
  --data-urlencode "password=${ADMIN_PASSWORD}")"

access_token="$(printf "%s" "$login_json" | python3 - <<'PY'
import json,sys
raw=sys.stdin.read().strip()
try:
    data=json.loads(raw) if raw else {}
except Exception:
    data={}
print(data.get("access_token",""))
PY
)"

if [[ -z "$access_token" ]]; then
  echo "ERROR: login failed"
  echo "Response: $login_json"
  exit 1
fi

echo "[2/3] Bootstrapping API key..."
payload="$(cat <<JSON
{
  "name": "${KEY_NAME}",
  "scopes": ${KEY_SCOPES},
  "rate_limit": ${KEY_RATE_LIMIT},
  "expires_in_days": ${KEY_EXPIRES_DAYS}
}
JSON
)"

key_json="$(curl -sS -X POST "${base_trimmed}/api/v2/auth/bootstrap-api-key" \
  -H "Authorization: Bearer ${access_token}" \
  -H "Content-Type: application/json" \
  -d "$payload")"

sardis_api_key="$(printf "%s" "$key_json" | python3 - <<'PY'
import json,sys
raw=sys.stdin.read().strip()
try:
    data=json.loads(raw) if raw else {}
except Exception:
    data={}
print(data.get("key",""))
PY
)"

if [[ -z "$sardis_api_key" ]]; then
  echo "ERROR: bootstrap-api-key failed"
  echo "Response: $key_json"
  exit 1
fi

echo "[3/3] Success"
echo ""
echo "SARDIS_API_URL=${base_trimmed}"
echo "SARDIS_API_KEY=${sardis_api_key}"
echo ""
echo "Tip: add these to landing project env vars for /demo live mode."

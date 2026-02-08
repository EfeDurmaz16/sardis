#!/usr/bin/env bash
set -euo pipefail

# Generate strong staging secrets for Sardis API.
#
# Usage:
#   bash ./scripts/generate_staging_secrets.sh
#   bash ./scripts/generate_staging_secrets.sh --write deploy/env/.env.generated.secrets

OUTPUT_FILE=""
if [[ "${1:-}" == "--write" ]]; then
  OUTPUT_FILE="${2:-}"
  if [[ -z "$OUTPUT_FILE" ]]; then
    echo "ERROR: --write requires file path"
    exit 1
  fi
fi

SARDIS_SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"

JWT_SECRET_KEY="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"

SARDIS_ADMIN_PASSWORD="$(python3 - <<'PY'
import secrets
alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*"
print("".join(secrets.choice(alphabet) for _ in range(28)))
PY
)"

payload="$(cat <<EOF
SARDIS_SECRET_KEY=${SARDIS_SECRET_KEY}
JWT_SECRET_KEY=${JWT_SECRET_KEY}
SARDIS_ADMIN_PASSWORD=${SARDIS_ADMIN_PASSWORD}
EOF
)"

if [[ -n "$OUTPUT_FILE" ]]; then
  umask 077
  printf "%s\n" "$payload" > "$OUTPUT_FILE"
  echo "Wrote secrets to: $OUTPUT_FILE"
else
  printf "%s\n" "$payload"
fi

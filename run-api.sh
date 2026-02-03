#!/bin/bash
# Sardis API Server Startup Script

cd "$(dirname "$0")"

# Set PYTHONPATH for all packages
export PYTHONPATH="./packages/sardis-api/src:./packages/sardis-core/src:./packages/sardis-wallet/src:./packages/sardis-chain/src:./packages/sardis-protocol/src:./packages/sardis-cards/src:./packages/sardis-compliance/src:./packages/sardis-ledger/src:./packages/sardis-checkout/src:$PYTHONPATH"

# Environment
export SARDIS_ENVIRONMENT="${SARDIS_ENVIRONMENT:-dev}"
export SARDIS_ENABLE_CARDS="${SARDIS_ENABLE_CARDS:-true}"

# Security: never silently default secrets outside dev.
if [[ "$SARDIS_ENVIRONMENT" == "prod" || "$SARDIS_ENVIRONMENT" == "production" || "$SARDIS_ENVIRONMENT" == "sandbox" || "$SARDIS_ENVIRONMENT" == "staging" ]]; then
  : "${JWT_SECRET_KEY:?JWT_SECRET_KEY is required for non-dev environments}"
  : "${SARDIS_ADMIN_PASSWORD:?SARDIS_ADMIN_PASSWORD is required for non-dev environments}"
else
  if [[ -z "${JWT_SECRET_KEY:-}" ]]; then
    export JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
  fi
  export SARDIS_ADMIN_PASSWORD="${SARDIS_ADMIN_PASSWORD:-demo123}"
fi

# Optional: Redis for caching (uses in-memory if not set)
# export REDIS_URL="redis://localhost:6379"

# Optional: Turnkey MPC (uses mock if not set)
# export TURNKEY_API_KEY="your-key"
# export TURNKEY_ORGANIZATION_ID="your-org"

# Optional: Lithic cards (uses mock if not set)
# export LITHIC_API_KEY="your-key"

# Optional: Database (uses in-memory if not set)
# export DATABASE_URL="postgresql://..."

echo "Starting Sardis API Server..."
echo "  - Environment: $SARDIS_ENVIRONMENT"
echo "  - Cards enabled: $SARDIS_ENABLE_CARDS"
echo "  - Admin password: $SARDIS_ADMIN_PASSWORD"
echo ""
echo "Dashboard login: admin / $SARDIS_ADMIN_PASSWORD"
echo ""

# Run with uv
uv run uvicorn sardis_api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload

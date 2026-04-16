#!/usr/bin/env bash
# =============================================================================
# Sardis Connect — Deploy Script
# =============================================================================
#
# Runs all pending migrations and verifies the deployment.
#
# Prerequisites:
#   1. DATABASE_URL set (Neon connection string)
#   2. STRIPE_API_KEY set (for Stripe Connect)
#   3. gcloud auth login (for Cloud Run redeploy)
#
# Usage:
#   export DATABASE_URL="postgresql://..."
#   ./scripts/deploy-sardis-connect.sh
#
# =============================================================================
set -euo pipefail

echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Sardis Connect — Deploy Script                ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""

# ── Step 1: Check prerequisites ──
echo "Step 1: Checking prerequisites..."

if [ -z "${DATABASE_URL:-}" ]; then
    echo "  ERROR: DATABASE_URL not set"
    echo "  Get it from Neon dashboard: https://console.neon.tech"
    echo "  export DATABASE_URL='postgresql://...'"
    exit 1
fi
echo "  DATABASE_URL: set (${#DATABASE_URL} chars)"

if [ -z "${STRIPE_API_KEY:-}" ]; then
    echo "  WARNING: STRIPE_API_KEY not set — Stripe Connect will be disabled"
else
    echo "  STRIPE_API_KEY: set"
fi

echo ""

# ── Step 2: Run migrations ──
echo "Step 2: Running migrations (102-106)..."

MIGRATIONS_DIR="$(cd "$(dirname "$0")/../packages/sardis-api/migrations" && pwd)"

for migration in 102_stripe_connect 103_checkout_mandate_bridge 104_merchant_website_lookup 105_service_directory 106_agent_registry; do
    file="$MIGRATIONS_DIR/${migration}.sql"
    if [ -f "$file" ]; then
        echo "  Applying: ${migration}.sql ..."
        psql "$DATABASE_URL" -f "$file" -q 2>&1 || echo "  WARNING: ${migration} may already be applied"
    else
        echo "  SKIP: ${migration}.sql not found"
    fi
done

echo ""

# ── Step 3: Verify tables exist ──
echo "Step 3: Verifying new tables..."

for table in stripe_connect_payouts service_directory agent_registry; do
    exists=$(psql "$DATABASE_URL" -t -A -c "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = '${table}');" 2>/dev/null || echo "false")
    if [ "$exists" = "t" ]; then
        echo "  ✓ $table"
    else
        echo "  ✗ $table — NOT FOUND"
    fi
done

# Verify columns on merchants table
for col in stripe_account_id mandate_id website; do
    exists=$(psql "$DATABASE_URL" -t -A -c "SELECT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'merchants' AND column_name = '${col}');" 2>/dev/null || echo "false")
    if [ "$exists" = "t" ]; then
        echo "  ✓ merchants.${col}"
    else
        echo "  ✗ merchants.${col} — NOT FOUND"
    fi
done

echo ""

# ── Step 4: Stripe Connect webhook setup reminder ──
echo "Step 4: Stripe Connect setup"
echo "  After deploying, configure in Stripe Dashboard:"
echo "  1. Go to: https://dashboard.stripe.com/test/webhooks"
echo "  2. Add endpoint: https://api.sardis.sh/api/v2/webhooks/stripe-connect/webhooks"
echo "  3. Select events: account.updated, payout.paid, payout.failed"
echo "  4. Check: 'Listen to events on Connected accounts'"
echo "  5. Copy webhook secret → set SARDIS_STRIPE_CONNECT_WEBHOOK_SECRET"
echo ""

# ── Step 5: Cloud Run redeploy ──
echo "Step 5: Cloud Run redeploy"
if command -v gcloud &> /dev/null; then
    echo "  To redeploy API with new env vars:"
    echo "  gcloud run services update sardis-api-staging \\"
    echo "    --region us-central1 \\"
    echo "    --update-env-vars SARDIS_STRIPE_CONNECT_WEBHOOK_SECRET=your_secret_here"
else
    echo "  gcloud not found — install Google Cloud SDK"
fi

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║           Deploy complete! Verify at:                    ║"
echo "║   https://api.sardis.sh/api/v2/docs                     ║"
echo "╚══════════════════════════════════════════════════════════╝"

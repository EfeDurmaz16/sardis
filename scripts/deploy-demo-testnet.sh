#!/usr/bin/env bash
# Deploy Sardis API staging with Base Sepolia testnet for live demo.
#
# Prerequisites:
#   1. Run: gcloud auth login
#   2. Run: chmod +x scripts/deploy-demo-testnet.sh
#   3. Run: ./scripts/deploy-demo-testnet.sh
#
# What this does:
#   - Updates Cloud Run staging env vars to base_sepolia + live chain mode
#   - Redeploys the API with testnet configuration
#   - The demo wallet is already seeded in the database
#
set -euo pipefail

PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sardis-staging-01}"
REGION="${CLOUD_RUN_REGION:-us-east1}"
SERVICE_NAME="sardis-api-staging"

echo "=== Deploying Sardis Demo (Base Sepolia Testnet) ==="
echo "  Service:  $SERVICE_NAME"
echo "  Region:   $REGION"
echo "  Chain:    base_sepolia"
echo "  Mode:     live"
echo ""

# Step 1: Update env vars for testnet demo (--update-env-vars preserves existing)
echo "[1/2] Updating environment variables..."
gcloud run services update "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars \
SARDIS_CHECKOUT_CHAIN=base_sepolia,\
SARDIS_CHAIN_MODE=live,\
SARDIS_ENVIRONMENT=sandbox

echo ""
echo "[2/2] Verifying deployment..."
SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format="value(status.url)")

echo ""
echo "=== DEPLOYMENT COMPLETE ==="
echo "  URL: $SERVICE_URL"
echo ""
echo "  Testing health endpoint..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" --max-time 10 || echo "000")
echo "  Health: HTTP $HTTP_CODE"
echo ""
echo "  Demo wallet: wallet_demo_001"
echo "  Demo agent:  agent_demo_001"
echo "  Chain:       base_sepolia (84532)"
echo "  Balance:     \$500 USDC"
echo "  Policy:      \$100/tx, \$1000 total"
echo ""
echo "  Next steps:"
echo "    1. Set Vercel env vars for landing site:"
echo "       SARDIS_API_URL=$SERVICE_URL"
echo "       SARDIS_API_KEY=sk_demo_testnet"
echo "       DEMO_OPERATOR_PASSWORD=sardis-demo-2026"
echo "       DEMO_LIVE_AGENT_ID=agent_demo_001"
echo "       DEMO_LIVE_CARD_ID=wallet_demo_001"
echo "    2. Redeploy landing: vercel --prod"
echo "    3. Go to sardis.sh/demo and test live mode"

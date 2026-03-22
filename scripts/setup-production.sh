#!/usr/bin/env bash
# =============================================================================
# Sardis Production Setup Script
# Run this after getting API keys from Resend, Polar, and Google
# =============================================================================
set -euo pipefail

echo "=== Sardis Production Setup ==="
echo ""

# ── Resend Email ──────────────────────────────────────
read -p "Resend API Key (re_...): " RESEND_KEY
if [[ -n "$RESEND_KEY" ]]; then
  echo "Setting Resend SMTP on Cloud Run (us-east1)..."
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "SMTP_HOST=smtp.resend.com,SMTP_PORT=465,SMTP_USER=resend,SMTP_PASSWORD=$RESEND_KEY,SMTP_FROM_EMAIL=Sardis <noreply@sardis.sh>" \
    --quiet
  echo "Setting Resend SMTP on Cloud Run (europe-west1)..."
  gcloud run services update sardis-api-staging --region europe-west1 --update-env-vars \
    "SMTP_HOST=smtp.resend.com,SMTP_PORT=465,SMTP_USER=resend,SMTP_PASSWORD=$RESEND_KEY,SMTP_FROM_EMAIL=Sardis <noreply@sardis.sh>" \
    --quiet
  echo "✓ Resend configured"
else
  echo "⊘ Skipped Resend"
fi
echo ""

# ── Polar Billing ─────────────────────────────────────
read -p "Polar Access Token (polar_oat_...): " POLAR_TOKEN
if [[ -n "$POLAR_TOKEN" ]]; then
  read -p "Polar Starter Product ID: " POLAR_STARTER
  read -p "Polar Growth Product ID: " POLAR_GROWTH
  read -p "Polar Webhook Secret: " POLAR_WEBHOOK
  echo "Setting Polar on Cloud Run..."
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "SARDIS_BILLING_PROVIDER=polar,POLAR_ACCESS_TOKEN=$POLAR_TOKEN,POLAR_WEBHOOK_SECRET=$POLAR_WEBHOOK,POLAR_PRODUCT_STARTER_ID=$POLAR_STARTER,POLAR_PRODUCT_GROWTH_ID=$POLAR_GROWTH" \
    --quiet
  gcloud run services update sardis-api-staging --region europe-west1 --update-env-vars \
    "SARDIS_BILLING_PROVIDER=polar,POLAR_ACCESS_TOKEN=$POLAR_TOKEN,POLAR_WEBHOOK_SECRET=$POLAR_WEBHOOK,POLAR_PRODUCT_STARTER_ID=$POLAR_STARTER,POLAR_PRODUCT_GROWTH_ID=$POLAR_GROWTH" \
    --quiet
  echo "✓ Polar configured"
else
  echo "⊘ Skipped Polar"
fi
echo ""

# ── Google OAuth ──────────────────────────────────────
read -p "Google OAuth Client ID: " GOOGLE_ID
if [[ -n "$GOOGLE_ID" ]]; then
  read -p "Google OAuth Client Secret: " GOOGLE_SECRET
  cd "$(dirname "$0")/../dashboard-next"
  echo "$GOOGLE_ID" | vercel env add GOOGLE_CLIENT_ID production 2>/dev/null || true
  echo "$GOOGLE_SECRET" | vercel env add GOOGLE_CLIENT_SECRET production 2>/dev/null || true
  # Also set on Cloud Run for the legacy auth
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "GOOGLE_CLIENT_ID=$GOOGLE_ID,GOOGLE_CLIENT_SECRET=$GOOGLE_SECRET" \
    --quiet
  echo "✓ Google OAuth configured"
else
  echo "⊘ Skipped Google OAuth"
fi
echo ""

echo "=== Setup Complete ==="
echo ""
echo "Next steps:"
echo "  1. Redeploy API:  ./scripts/deploy-cloudrun.sh"
echo "  2. Redeploy dashboard:  cd dashboard-next && vercel --prod --yes"
echo "  3. Test email:  curl -X POST https://api.sardis.sh/api/v2/auth/forgot-password -H 'Content-Type: application/json' -d '{\"email\":\"your@email.com\"}'"
echo "  4. Test billing: Go to app.sardis.sh → Billing → Upgrade"

#!/usr/bin/env bash
# Deploy Sardis API to Cloud Run.
#
# Usage:
#   ./scripts/deploy-cloudrun.sh              # default: sardis-api-staging
#   ./scripts/deploy-cloudrun.sh production   # sardis-api (production)
#
# Prerequisites:
#   - gcloud CLI authenticated
#   - Docker or Cloud Build configured
set -euo pipefail

ENVIRONMENT="${1:-staging}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sardis-staging}"
REGION="${CLOUD_RUN_REGION:-us-central1}"

if [[ "$ENVIRONMENT" == "production" ]]; then
  SERVICE_NAME="sardis-api"
  IMAGE_TAG="prod-$(git rev-parse --short HEAD)"
else
  SERVICE_NAME="sardis-api-staging"
  IMAGE_TAG="staging-$(git rev-parse --short HEAD)"
fi

IMAGE_URI="gcr.io/${PROJECT_ID}/${SERVICE_NAME}:${IMAGE_TAG}"

echo "=== Deploying Sardis API ==="
echo "  Environment: $ENVIRONMENT"
echo "  Service:     $SERVICE_NAME"
echo "  Image:       $IMAGE_URI"
echo "  Region:      $REGION"
echo ""

# Build
echo "Building Docker image..."
gcloud builds submit \
  --project "$PROJECT_ID" \
  --tag "$IMAGE_URI" \
  --timeout=600s \
  .

# Deploy (preserves existing env vars)
echo "Deploying to Cloud Run..."
gcloud run deploy "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --image "$IMAGE_URI" \
  --platform managed \
  --no-traffic 2>/dev/null || true

# Route traffic
gcloud run services update-traffic "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --to-latest

echo ""
echo "=== Deploy complete ==="
gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format="value(status.url)"

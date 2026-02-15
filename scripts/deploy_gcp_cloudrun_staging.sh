#!/usr/bin/env bash
set -euo pipefail

# Sardis API staging deploy to Google Cloud Run.
#
# Required env:
#   PROJECT_ID
#
# Optional env (defaults shown):
#   REGION=us-east1
#   SERVICE_NAME=sardis-api-staging
#   AR_REPO=sardis-images
#   IMAGE_NAME=sardis-api
#   IMAGE_TAG=<git short sha or timestamp>
#   ENV_VARS_FILE=deploy/gcp/staging/env.cloudrun.staging.yaml
#   ALLOW_UNAUTH=true
#   CPU=1
#   MEMORY=1Gi
#   MIN_INSTANCES=0
#   MAX_INSTANCES=5
#   CONCURRENCY=80
#   TIMEOUT=300
#
# Usage:
#   PROJECT_ID=my-gcp-project bash ./scripts/deploy_gcp_cloudrun_staging.sh

PROJECT_ID="${PROJECT_ID:-}"
REGION="${REGION:-us-east1}"
SERVICE_NAME="${SERVICE_NAME:-sardis-api-staging}"
AR_REPO="${AR_REPO:-sardis-images}"
IMAGE_NAME="${IMAGE_NAME:-sardis-api}"
ENV_VARS_FILE="${ENV_VARS_FILE:-deploy/gcp/staging/env.cloudrun.staging.yaml}"
ALLOW_UNAUTH="${ALLOW_UNAUTH:-true}"
CPU="${CPU:-1}"
MEMORY="${MEMORY:-1Gi}"
MIN_INSTANCES="${MIN_INSTANCES:-0}"
MAX_INSTANCES="${MAX_INSTANCES:-5}"
CONCURRENCY="${CONCURRENCY:-80}"
TIMEOUT="${TIMEOUT:-300}"

if [[ -z "${IMAGE_TAG:-}" ]]; then
  if command -v git >/dev/null 2>&1 && git rev-parse --short HEAD >/dev/null 2>&1; then
    IMAGE_TAG="$(git rev-parse --short HEAD)"
  else
    IMAGE_TAG="$(date +%Y%m%d%H%M%S)"
  fi
fi

fail() {
  echo "[FAIL] $*" >&2
  exit 1
}

log() {
  echo "[INFO] $*"
}

for bin in gcloud curl; do
  command -v "$bin" >/dev/null 2>&1 || fail "Missing required command: $bin"
done

[[ -z "$PROJECT_ID" ]] && fail "PROJECT_ID is required"
[[ -f "$ENV_VARS_FILE" ]] || fail "ENV_VARS_FILE not found: $ENV_VARS_FILE"

if grep -q "REPLACE_ME" "$ENV_VARS_FILE"; then
  fail "ENV_VARS_FILE still contains REPLACE_ME values: $ENV_VARS_FILE"
fi

IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${AR_REPO}/${IMAGE_NAME}:${IMAGE_TAG}"

log "Using project: ${PROJECT_ID}"
log "Using region: ${REGION}"
log "Service: ${SERVICE_NAME}"
log "Image: ${IMAGE_URI}"
log "Env file: ${ENV_VARS_FILE}"

log "Setting gcloud project"
gcloud config set project "$PROJECT_ID" >/dev/null

log "Enabling required APIs"
gcloud services enable \
  run.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  --project "$PROJECT_ID" >/dev/null

if ! gcloud artifacts repositories describe "$AR_REPO" --location "$REGION" --project "$PROJECT_ID" >/dev/null 2>&1; then
  log "Creating Artifact Registry repo: ${AR_REPO}"
  gcloud artifacts repositories create "$AR_REPO" \
    --repository-format=docker \
    --location="$REGION" \
    --description="Sardis API container images" \
    --project "$PROJECT_ID" >/dev/null
else
  log "Artifact Registry repo already exists: ${AR_REPO}"
fi

log "Building and pushing image via Cloud Build"
gcloud builds submit --tag "$IMAGE_URI" --project "$PROJECT_ID" .

DEPLOY_FLAGS=(
  --project "$PROJECT_ID"
  --region "$REGION"
  --image "$IMAGE_URI"
  --platform managed
  --execution-environment gen2
  --port 8000
  --cpu "$CPU"
  --memory "$MEMORY"
  --min-instances "$MIN_INSTANCES"
  --max-instances "$MAX_INSTANCES"
  --concurrency "$CONCURRENCY"
  --timeout "$TIMEOUT"
  --env-vars-file "$ENV_VARS_FILE"
)

if [[ "$ALLOW_UNAUTH" == "true" ]]; then
  DEPLOY_FLAGS+=(--allow-unauthenticated)
else
  DEPLOY_FLAGS+=(--no-allow-unauthenticated)
fi

log "Deploying Cloud Run service"
gcloud run deploy "$SERVICE_NAME" "${DEPLOY_FLAGS[@]}"

SERVICE_URL="$(gcloud run services describe "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --format='value(status.url)')"

[[ -z "$SERVICE_URL" ]] && fail "Could not resolve service URL after deploy"

log "Updating SARDIS_API_BASE_URL to deployed URL"
gcloud run services update "$SERVICE_NAME" \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --update-env-vars "SARDIS_API_BASE_URL=${SERVICE_URL}" >/dev/null

log "Waiting for health endpoint"
ok=false
for i in $(seq 1 30); do
  code="$(curl -sS -o /dev/null -w "%{http_code}" "${SERVICE_URL}/health" || true)"
  if [[ "$code" == "200" ]]; then
    ok=true
    break
  fi
  sleep 2
done

if [[ "$ok" != "true" ]]; then
  fail "Health check failed: ${SERVICE_URL}/health did not return 200"
fi

echo
echo "=============================================================="
echo "Sardis API staging deployed successfully"
echo "SERVICE_URL=${SERVICE_URL}"
echo "=============================================================="
echo
echo "Next:"
echo "1) Bootstrap demo API key:"
echo "   BASE_URL=\"${SERVICE_URL}\" ADMIN_PASSWORD=\"<SARDIS_ADMIN_PASSWORD>\" bash ./scripts/bootstrap_staging_api_key.sh"
echo "2) Set landing vars:"
echo "   SARDIS_API_URL=${SERVICE_URL}"
echo "   SARDIS_API_KEY=<bootstrap output>"
echo "   DEMO_OPERATOR_PASSWORD=<shared password>"

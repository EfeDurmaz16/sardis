#!/usr/bin/env bash
# Set up Cloud Monitoring alerting policies for Sardis API on Cloud Run.
#
# Usage:
#   ./scripts/setup-monitoring.sh                 # default: staging
#   ./scripts/setup-monitoring.sh production      # production service
#
# Prerequisites:
#   - gcloud CLI authenticated with Monitoring Admin role
#   - Cloud Run service already deployed
#
# Optional:
#   NOTIFICATION_CHANNEL_ID — gcloud notification channel ID (Slack/PagerDuty/email)
set -euo pipefail

ENVIRONMENT="${1:-staging}"
PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-sardis-staging-01}"

if [[ "$ENVIRONMENT" == "production" ]]; then
  SERVICE_NAME="sardis-api"
else
  SERVICE_NAME="sardis-api-staging"
fi

NOTIFICATION_CHANNEL="${NOTIFICATION_CHANNEL_ID:-}"
NOTIFICATION_FLAG=""
if [[ -n "$NOTIFICATION_CHANNEL" ]]; then
  NOTIFICATION_FLAG="--notification-channels=$NOTIFICATION_CHANNEL"
fi

echo "=== Setting up monitoring for $SERVICE_NAME ==="
echo "  Project: $PROJECT_ID"
echo ""

# 1. Error Rate > 5% over 5 minutes
echo "Creating alert: High Error Rate..."
gcloud alpha monitoring policies create \
  --project="$PROJECT_ID" \
  --display-name="[Sardis] High Error Rate - $SERVICE_NAME" \
  --condition-display-name="Error rate > 5%" \
  --condition-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class!=\"2xx\"" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT \
  --combiner=OR \
  $NOTIFICATION_FLAG \
  2>/dev/null && echo "  Created." || echo "  Already exists or failed."

# 2. Latency P95 > 2s over 5 minutes
echo "Creating alert: High Latency..."
gcloud alpha monitoring policies create \
  --project="$PROJECT_ID" \
  --display-name="[Sardis] High Latency P95 - $SERVICE_NAME" \
  --condition-display-name="P95 latency > 2s" \
  --condition-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/request_latencies\"" \
  --condition-threshold-value=2000 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT \
  --combiner=OR \
  $NOTIFICATION_FLAG \
  2>/dev/null && echo "  Created." || echo "  Already exists or failed."

# 3. Memory Usage > 80%
echo "Creating alert: High Memory Usage..."
gcloud alpha monitoring policies create \
  --project="$PROJECT_ID" \
  --display-name="[Sardis] High Memory Usage - $SERVICE_NAME" \
  --condition-display-name="Memory > 80%" \
  --condition-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/container/memory/utilizations\"" \
  --condition-threshold-value=0.8 \
  --condition-threshold-duration=300s \
  --condition-threshold-comparison=COMPARISON_GT \
  --combiner=OR \
  $NOTIFICATION_FLAG \
  2>/dev/null && echo "  Created." || echo "  Already exists or failed."

# 4. Instance count drops to 0 (service down)
echo "Creating alert: No Running Instances..."
gcloud alpha monitoring policies create \
  --project="$PROJECT_ID" \
  --display-name="[Sardis] No Instances - $SERVICE_NAME" \
  --condition-display-name="Instance count = 0" \
  --condition-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"$SERVICE_NAME\" AND metric.type=\"run.googleapis.com/container/instance_count\"" \
  --condition-threshold-value=1 \
  --condition-threshold-duration=60s \
  --condition-threshold-comparison=COMPARISON_LT \
  --combiner=OR \
  $NOTIFICATION_FLAG \
  2>/dev/null && echo "  Created." || echo "  Already exists or failed."

echo ""
echo "=== Monitoring setup complete ==="
echo "View alerts: https://console.cloud.google.com/monitoring/alerting?project=$PROJECT_ID"

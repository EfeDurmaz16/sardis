# Sardis API Deployment Plan - Google Cloud Run

This guide deploys the Sardis API to Cloud Run for staging/testnet demos.

## 1) Prerequisites

Install and login:

```bash
gcloud auth login
gcloud auth application-default login
```

Required resources:

1. GCP Project ID
2. Neon Postgres `DATABASE_URL`
3. Upstash/Redis `SARDIS_REDIS_URL`

## 2) Prepare env file

Copy template:

```bash
cp deploy/gcp/staging/env.cloudrun.staging.yaml deploy/gcp/staging/env.cloudrun.staging.local.yaml
```

Generate secrets:

```bash
bash ./scripts/generate_staging_secrets.sh --write deploy/env/.env.generated.secrets
```

Then update `deploy/gcp/staging/env.cloudrun.staging.local.yaml` with:

- `SARDIS_SECRET_KEY`
- `JWT_SECRET_KEY`
- `SARDIS_ADMIN_PASSWORD`
- `DATABASE_URL`
- `SARDIS_REDIS_URL`

## 3) Deploy

```bash
PROJECT_ID="<your-gcp-project-id>" \
REGION="europe-west1" \
SERVICE_NAME="sardis-api-staging" \
ENV_VARS_FILE="deploy/gcp/staging/env.cloudrun.staging.local.yaml" \
bash ./scripts/deploy_gcp_cloudrun_staging.sh
```

The script will:

1. Enable required Google APIs
2. Create Artifact Registry repo if missing
3. Build and push container image
4. Deploy Cloud Run service
5. Check `/health`
6. Print the final `SERVICE_URL`

## 4) Bootstrap demo API key

```bash
BASE_URL="<SERVICE_URL_FROM_DEPLOY>" \
ADMIN_PASSWORD="<SARDIS_ADMIN_PASSWORD>" \
bash ./scripts/bootstrap_staging_api_key.sh
```

Use output in landing:

- `SARDIS_API_URL=<service-url>`
- `SARDIS_API_KEY=<generated-key>`
- `DEMO_OPERATOR_PASSWORD=<shared-password>`

## 5) Optional cost/UX tuning

Default config uses `MIN_INSTANCES=0` (lowest cost, possible cold starts).

For smoother demo UX:

```bash
MIN_INSTANCES=1 \
PROJECT_ID="<your-gcp-project-id>" \
ENV_VARS_FILE="deploy/gcp/staging/env.cloudrun.staging.local.yaml" \
bash ./scripts/deploy_gcp_cloudrun_staging.sh
```

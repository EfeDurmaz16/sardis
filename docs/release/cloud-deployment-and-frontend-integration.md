# Sardis Cloud Deployment + Frontend Integration (Staging)

This runbook covers end-to-end setup for:

1. Sardis API deployment (`Cloud Run` recommended, `AWS App Runner` alternative)
2. Landing/demo frontend integration (`/demo` live mode via server-side proxy)

## 1) What you need

Required:

- `DATABASE_URL` (Neon Postgres recommended)
- `SARDIS_REDIS_URL` (Upstash Redis recommended)
- `SARDIS_SECRET_KEY`
- `JWT_SECRET_KEY`
- `SARDIS_ADMIN_PASSWORD`

For landing live demo:

- `SARDIS_API_URL` (deployed API URL)
- `SARDIS_API_KEY` (bootstrap-generated API key)
- `DEMO_OPERATOR_PASSWORD` (shared operator password)

## 2) Recommended path: Google Cloud Run

Prepare env:

```bash
cp deploy/gcp/staging/env.cloudrun.staging.yaml deploy/gcp/staging/env.cloudrun.staging.local.yaml
bash ./scripts/generate_staging_secrets.sh --write deploy/env/.env.generated.secrets
```

Fill `deploy/gcp/staging/env.cloudrun.staging.local.yaml` with:

- `SARDIS_SECRET_KEY`
- `JWT_SECRET_KEY`
- `SARDIS_ADMIN_PASSWORD`
- `DATABASE_URL`
- `SARDIS_REDIS_URL`

Deploy:

```bash
PROJECT_ID="<gcp-project-id>" \
REGION="europe-west1" \
SERVICE_NAME="sardis-api-staging" \
ENV_VARS_FILE="deploy/gcp/staging/env.cloudrun.staging.local.yaml" \
bash ./scripts/deploy_gcp_cloudrun_staging.sh
```

## 3) AWS alternative: App Runner

Prepare env:

```bash
cp deploy/aws/staging/env.apprunner.staging.json deploy/aws/staging/env.apprunner.staging.local.json
```

Fill `deploy/aws/staging/env.apprunner.staging.local.json` placeholders.

Deploy:

```bash
AWS_REGION="eu-central-1" \
AWS_ACCOUNT_ID="<aws-account-id>" \
SERVICE_NAME="sardis-api-staging" \
ENV_JSON_FILE="deploy/aws/staging/env.apprunner.staging.local.json" \
bash ./scripts/deploy_aws_apprunner_staging.sh
```

## 4) Bootstrap API key (required for /demo live)

```bash
BASE_URL="https://<deployed-api-domain>" \
ADMIN_PASSWORD="<SARDIS_ADMIN_PASSWORD>" \
bash ./scripts/bootstrap_staging_api_key.sh
```

Save output key as `SARDIS_API_KEY`.

## 5) Connect landing frontend (Vercel project env)

Set in landing deployment environment:

```bash
SARDIS_API_URL=https://<deployed-api-domain>
SARDIS_API_KEY=<bootstrap-output-key>
DEMO_OPERATOR_PASSWORD=<shared-password>
```

Optional (better live demo scenario data):

```bash
DEMO_LIVE_AGENT_ID=agent_demo_01
DEMO_LIVE_CARD_ID=card_demo_01
```

## 6) Live demo validation

1. Open `/demo`
2. Switch to `Live (Private)`
3. Enter `DEMO_OPERATOR_PASSWORD`
4. Run:
   - `Run blocked path`
   - `Run approved path`
5. Verify transaction history is visible and persists after refresh

## 7) Cold-start and UX note

- `min instances = 0` minimizes cost but may cold-start.
- For investor/design-partner demos, set at least one warm instance:
  - Cloud Run: `MIN_INSTANCES=1`
  - App Runner: use auto scaling config with low min capacity.

## 8) Source files

- GCP script: `scripts/deploy_gcp_cloudrun_staging.sh`
- AWS script: `scripts/deploy_aws_apprunner_staging.sh`
- GCP env template: `deploy/gcp/staging/env.cloudrun.staging.yaml`
- AWS env template: `deploy/aws/staging/env.apprunner.staging.json`
- Key bootstrap: `scripts/bootstrap_staging_api_key.sh`

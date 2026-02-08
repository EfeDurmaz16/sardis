# Sardis API Deployment Plan (Free-Tier First)

## Goal

Deploy a stable **staging/testnet API** for `/demo` private live mode and design-partner trials, with minimal cost.

## Recommended stack

1. API runtime: Render Web Service (free plan) using repo `Dockerfile`
2. PostgreSQL: Neon (free tier)
3. Redis: Upstash Redis (free tier)
4. Landing/demo frontend: Vercel (already in place)

This keeps setup simple and avoids paying for always-on compute at day 1.

## Phase 0 - Prepare credentials

You need to provide these values (cannot be auto-filled by repo code):

- `DATABASE_URL` (Neon)
- `SARDIS_REDIS_URL` or `UPSTASH_REDIS_URL`
- `SARDIS_ADMIN_PASSWORD`
- `SARDIS_SECRET_KEY` (>= 32 chars)
- `JWT_SECRET_KEY` (>= 32 chars)

You can auto-generate the 3 secrets above with:

```bash
bash ./scripts/generate_staging_secrets.sh --write deploy/env/.env.generated.secrets
```

Optional providers for later:

- `TURNKEY_*`, `LITHIC_*`, `PERSONA_*`, `ELLIPTIC_*`, `ONRAMPER_*`

## Phase 1 - Create staging env file

Start from:

```bash
cp deploy/env/.env.api.staging.example .env.api.staging.local
```

Fill placeholders with your real values.

## Phase 2 - Provision Render service

Use blueprint:

```bash
deploy/render/staging/render.yaml
```

Set required secrets in Render dashboard (Environment section).

## Phase 3 - Database migration

After Render service and Neon are connected:

```bash
DATABASE_URL="<your-neon-url>" ./scripts/run_migrations.sh --dry-run
DATABASE_URL="<your-neon-url>" ./scripts/run_migrations.sh
```

## Phase 4 - Health checks

Replace `<BASE_URL>` with your deployed API URL:

```bash
curl -sS <BASE_URL>/health
curl -sS <BASE_URL>/api/v2/health
```

Expected: HTTP 200 for both.

## Phase 5 - Bootstrap API key for demo

Run:

```bash
BASE_URL="<BASE_URL>" \
ADMIN_PASSWORD="<SARDIS_ADMIN_PASSWORD>" \
bash ./scripts/bootstrap_staging_api_key.sh
```

This will print:

- `SARDIS_API_KEY`
- key metadata

Then set in Vercel (landing project):

- `SARDIS_API_URL=<BASE_URL>`
- `SARDIS_API_KEY=<generated key>`
- `DEMO_OPERATOR_PASSWORD=<shared demo unlock password>`

## Phase 6 - Demo smoke test

```bash
LANDING_BASE_URL="https://sardis.sh" \
DEMO_OPERATOR_PASSWORD="<shared-password>" \
bash ./scripts/check_demo_deploy_readiness.sh
```

## Go/No-Go checklist

Go only if all are true:

1. Migrations applied successfully
2. `/health` and `/api/v2/health` are green
3. Admin login works
4. API key bootstrap works
5. `/demo` live mode unlock works
6. Blocked + approved live flows both return deterministic results

## Notes on free-tier behavior

- Expect cold starts after inactivity.
- Acceptable for early design-partner staging if communicated.
- Upgrade to paid always-on compute before investor live demos and time-sensitive partner calls.

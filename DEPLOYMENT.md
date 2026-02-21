# Sardis API Deployment Guide

This guide covers deploying the Sardis FastAPI backend to various platforms.

## Files Created

- **Dockerfile**: Multi-stage Docker build with uv package manager
- **.dockerignore**: Excludes unnecessary files from Docker build
- **docker-compose.yml**: Local development environment with PostgreSQL and Redis
- **render.yaml**: Render.com deployment configuration
- **deploy/gcp/staging/env.cloudrun.staging.yaml**: Google Cloud Run staging configuration

## Local Development with Docker

### Prerequisites
- Docker and Docker Compose installed
- `.env` file with required secrets

### Quick Start

```bash
# Start all services (API, PostgreSQL, Redis)
docker-compose up -d

# View logs
docker-compose logs -f api

# Stop services
docker-compose down

# Rebuild after code changes
docker-compose up -d --build
```

The API will be available at `http://localhost:8000`
- Health check: `http://localhost:8000/health`
- API docs: `http://localhost:8000/api/v2/docs`

## Render.com Deployment

### Setup

1. Push code to GitHub repository
2. Create a new Render account or login
3. Import the repository in Render dashboard
4. Render will auto-detect `render.yaml`

### Required Secrets

Set these in the Render dashboard (Environment > Secret Files):

**Core:**
- `SARDIS_SECRET_KEY`
- `JWT_SECRET_KEY`
- `SARDIS_ADMIN_PASSWORD`

**MPC/Custody:**
- `TURNKEY_API_KEY`
- `TURNKEY_API_PRIVATE_KEY`
- `TURNKEY_ORGANIZATION_ID`

**Payment Providers:**
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`

**Compliance:**
- `PERSONA_API_KEY`
- `PERSONA_TEMPLATE_ID`
- `PERSONA_WEBHOOK_SECRET`
- `ELLIPTIC_API_KEY`
- `ELLIPTIC_API_SECRET`

**Virtual Cards:**
- `LITHIC_API_KEY`
- `LITHIC_WEBHOOK_SECRET`

**Fiat Ramp:**
- `BRIDGE_API_KEY`
- `BRIDGE_API_SECRET`
- `ONRAMPER_API_KEY`

**RPC Endpoints:**
- `BASE_RPC_URL`
- `POLYGON_RPC_URL`
- `ETHEREUM_RPC_URL`
- `ARBITRUM_RPC_URL`
- `OPTIMISM_RPC_URL`

**Monitoring (Optional):**
- `SENTRY_DSN`

### Database

Render will automatically provision:
- PostgreSQL database (`sardis-postgres`)
- Redis instance (`sardis-redis`)

Database URLs are automatically injected via `fromDatabase` configuration.

## Google Cloud Run Deployment

### Prerequisites
- Google Cloud SDK installed
- Project created in GCP
- Cloud Run API enabled

### Deploy to Staging

```bash
# Build and push Docker image
gcloud builds submit --tag gcr.io/[PROJECT-ID]/sardis-api

# Deploy to Cloud Run
gcloud run deploy sardis-api \
  --image gcr.io/[PROJECT-ID]/sardis-api \
  --platform managed \
  --region us-central1 \
  --env-vars-file deploy/gcp/staging/env.cloudrun.staging.yaml \
  --allow-unauthenticated \
  --port 8000
```

### Update Environment Variables

Edit `deploy/gcp/staging/env.cloudrun.staging.yaml` and replace:
- `SARDIS_SECRET_KEY: "REPLACE_ME"`
- `JWT_SECRET_KEY: "REPLACE_ME"`
- `SARDIS_ADMIN_PASSWORD: "REPLACE_ME"`
- `DATABASE_URL: "REPLACE_ME"`
- `SARDIS_REDIS_URL: "REPLACE_ME"`

## Railway Deployment

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login
railway login

# Initialize project
railway init

# Deploy
railway up
```

Set environment variables in Railway dashboard.

## Manual Deployment

### Build Docker Image

```bash
docker build -t sardis-api .
```

### Run Container

```bash
docker run -d \
  -p 8000:8000 \
  --env-file .env \
  --name sardis-api \
  sardis-api
```

## Health Checks

All platforms should configure health checks:
- **Path**: `/health`
- **Interval**: 30s
- **Timeout**: 10s
- **Start period**: 40s
- **Retries**: 3

The health endpoint returns:
- `200 OK`: Service healthy
- `503 Service Unavailable`: Service degraded or shutting down

## Environment Variables

### Required

| Variable | Description |
|----------|-------------|
| `SARDIS_SECRET_KEY` | Secret key for API security |
| `JWT_SECRET_KEY` | JWT signing key |
| `DATABASE_URL` | PostgreSQL connection string |
| `SARDIS_REDIS_URL` | Redis connection string |

### Recommended

| Variable | Description | Default |
|----------|-------------|---------|
| `SARDIS_ENVIRONMENT` | Environment (dev/staging/production) | `dev` |
| `SARDIS_CHAIN_MODE` | Chain execution mode (simulated/live) | `simulated` |
| `SARDIS_TAP_ENFORCEMENT` | TAP protocol enforcement | `disabled` |
| `PORT` | HTTP port (some platforms set this) | `8000` |

## Monitoring

### Health Endpoint

```bash
curl https://your-domain.com/health
```

Returns detailed component status:
- Database connectivity
- Redis cache
- Chain executor
- External services (Stripe, Turnkey, etc.)

### Logs

All platforms provide log aggregation:
- **Render**: Dashboard > Logs
- **Cloud Run**: Cloud Logging
- **Railway**: Dashboard > Logs

## Troubleshooting

### Container Won't Start

1. Check logs: `docker-compose logs api`
2. Verify environment variables are set
3. Ensure DATABASE_URL and REDIS_URL are accessible

### Health Check Failing

1. Check `/health` endpoint manually
2. Verify database connectivity
3. Check Redis connectivity
4. Review component status in health response

### Database Connection Issues

1. Verify DATABASE_URL format: `postgresql://user:pass@host:port/db`
2. Check network connectivity
3. Verify database credentials

## Production Checklist

- [ ] Set all required secrets
- [ ] Configure managed PostgreSQL database
- [ ] Configure managed Redis instance
- [ ] Set `SARDIS_ENVIRONMENT=production`
- [ ] Set `SARDIS_CHAIN_MODE=live`
- [ ] Enable `SARDIS_TAP_ENFORCEMENT=enabled`
- [ ] Configure Turnkey MPC credentials
- [ ] Set up Sentry monitoring
- [ ] Configure RPC endpoints for all chains
- [ ] Set up webhook secrets
- [ ] Test health endpoint
- [ ] Verify CORS origins
- [ ] Enable database backups
- [ ] Configure auto-scaling rules

## Support

- Documentation: https://sardis.sh/docs
- API Docs: https://your-domain.com/api/v2/docs
- GitHub: https://github.com/sardis-pay/sardis

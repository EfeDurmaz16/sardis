# Sardis Deployment Pipeline — Design Document

**Date:** 2026-03-22
**Author:** Efe + Claude

## Goal

Establish a reliable, repeatable deployment pipeline with two environments (staging + production) where staging is the gate to production. Every change goes staging → verify → production. Main system never breaks.

## Current State

### What Already Exists

| Component | Staging | Production | Method |
|-----------|---------|------------|--------|
| **API** | `sardis-api-staging` (Cloud Run, us-east1) | `sardis-api` (Cloud Run) | `scripts/deploy-cloudrun.sh [staging\|production]` |
| **Dashboard** | `dashboard-staging.sardis.sh` | `app.sardis.sh` | Vercel auto-deploy on `dashboard/**` changes |
| **Landing** | `staging.sardis.sh` | `sardis.sh` | Vercel auto-deploy on `landing/**` changes |
| **Database** | `STAGING_DATABASE_URL` (Neon) | `PRODUCTION_DATABASE_URL` (Neon) | Alembic migrations |
| **CI** | GitHub Actions on PR + main push | Same | Ruff + pytest + webhook conformance + gas ceiling |
| **Manual Deploy** | `deploy.yml` workflow_dispatch | Same | Staging or production dropdown |
| **Contracts** | Base Sepolia (deployed) | Base mainnet (script ready) | `scripts/deploy-mainnet-contracts.sh` |
| **Docker** | Multi-stage Python 3.14, gunicorn+uvicorn | Same | `Dockerfile` |
| **Health** | `GET /api/v2/health` | Same | HEALTHCHECK in Docker + post-deploy curl |

### What's Missing

1. **Env vars not set for new features** — faucet, public signup, chain routing, new endpoints
2. **No faucet wallet** — need funded wallet on Base Sepolia
3. **No clear deployment runbook** — scattered scripts, no single source of truth
4. **Dashboard staging API proxy wrong** — points to `api.sardis.sh` (production), should point to staging
5. **No pre-deploy smoke test** — health check only, no functional verification
6. **Migrations not in deploy script** — Cloud Run script doesn't run migrations

---

## Architecture

### Two Environments

```
┌──────────────────────────────────────────────────────────────┐
│                        STAGING                                │
│                                                               │
│  API:       sardis-api-staging (Cloud Run, us-east1)         │
│  URL:       api-staging.sardis.sh                             │
│  Dashboard: dashboard-staging.sardis.sh (Vercel)             │
│  Landing:   staging.sardis.sh (Vercel)                       │
│  Database:  Neon staging (STAGING_DATABASE_URL)               │
│  Chain:     Base Sepolia (84532)                              │
│  Mode:      SARDIS_CHAIN_MODE=live, SARDIS_ENVIRONMENT=staging│
│  MPC:       Turnkey (same org, testnet wallets)               │
│  Faucet:    Enabled (SARDIS_FAUCET_PRIVATE_KEY set)          │
│  Signup:    Public (SARDIS_ALLOW_PUBLIC_SIGNUP=1)             │
│                                                               │
│  Purpose: Test everything here first. External testers        │
│           use this with sk_test_ keys.                        │
└─────────────────────────┬─────────────────────────────────────┘
                          │ Verify → Promote
┌─────────────────────────▼─────────────────────────────────────┐
│                       PRODUCTION                               │
│                                                                │
│  API:       sardis-api (Cloud Run, us-east1)                  │
│  URL:       api.sardis.sh                                      │
│  Dashboard: app.sardis.sh (Vercel)                             │
│  Landing:   sardis.sh (Vercel)                                 │
│  Database:  Neon production (PRODUCTION_DATABASE_URL)           │
│  Chain:     Tempo Mainnet (4217) for sk_live_ keys             │
│             Base Sepolia (84532) for sk_test_ keys             │
│  Mode:      SARDIS_CHAIN_MODE=live, SARDIS_ENVIRONMENT=prod    │
│  MPC:       Turnkey (same org, real wallets)                   │
│  Faucet:    Enabled for sk_test_ only                          │
│  Signup:    Public (SARDIS_ALLOW_PUBLIC_SIGNUP=1)              │
│                                                                │
│  Purpose: Stable, customer-facing. Pilot partners here         │
│           with sk_live_ keys (admin-assigned).                 │
└────────────────────────────────────────────────────────────────┘
```

### Deployment Flow

```
Developer                  Staging                    Production
    │                         │                           │
    ├── git push main ───────→│                           │
    │                         │                           │
    ├── GitHub Actions CI ───→│ (auto: lint + test)       │
    │                         │                           │
    ├── Manual: deploy.yml ──→│ staging deploy            │
    │   (workflow_dispatch)   │ 1. DB migrations          │
    │                         │ 2. Cloud Run deploy       │
    │                         │ 3. Vercel deploy          │
    │                         │ 4. Health check           │
    │                         │ 5. Smoke test             │
    │                         │                           │
    ├── Verify staging ──────→│ (manual or automated)     │
    │   - API endpoints work  │                           │
    │   - Dashboard loads     │                           │
    │   - Full flow test      │                           │
    │                         │                           │
    ├── Manual: deploy.yml ──→│──────────────────────────→│ production deploy
    │   (production)          │                           │ 1. DB migrations
    │                         │                           │ 2. Cloud Run deploy
    │                         │                           │ 3. Vercel deploy
    │                         │                           │ 4. Health check
    │                         │                           │ 5. Smoke test
    │                         │                           │
    └─────────────────────────┴───────────────────────────┘
```

### Rollback Strategy

```
# Cloud Run: instant rollback to previous revision
gcloud run services update-traffic sardis-api-staging \
  --to-revisions=PREVIOUS_REVISION=100 \
  --region=us-east1

# Vercel: instant rollback via dashboard or CLI
vercel rollback

# Database: migrations are forward-only (no down migrations)
# → If migration is bad, write a new migration to fix it
```

---

## Environment Variables — Complete Reference

### Staging-Specific (set on Cloud Run + GitHub Secrets)

```bash
# ── Identity ──
SARDIS_ENVIRONMENT=staging
SARDIS_CHAIN_MODE=live
SARDIS_DEFAULT_CHAIN=base_sepolia

# ── Database ──
DATABASE_URL=${STAGING_DATABASE_URL}    # Neon staging

# ── Auth ──
JWT_SECRET_KEY=<staging-specific-hex-64>
SARDIS_SECRET_KEY=<staging-specific-urlsafe-32>
SARDIS_ADMIN_PASSWORD=<staging-admin-pass>
SARDIS_ALLOW_PUBLIC_SIGNUP=1

# ── MPC Wallet (Turnkey — same org for both envs) ──
SARDIS_MPC__NAME=turnkey
TURNKEY_ORGANIZATION_ID=<your-turnkey-org>
TURNKEY_API_PUBLIC_KEY=<your-turnkey-public-key>
TURNKEY_API_PRIVATE_KEY=<your-turnkey-private-key>

# ── Chain RPCs ──
SARDIS_BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/<ALCHEMY_KEY>
SARDIS_TEMPO_RPC_URL=https://rpc.tempo.xyz

# ── Faucet ──
SARDIS_FAUCET_PRIVATE_KEY=<faucet-wallet-pk>  # Pre-funded with Base Sepolia ETH + USDC

# ── Redis (Upstash) ──
SARDIS_REDIS_URL=<upstash-staging-url>

# ── CORS ──
SARDIS_ALLOWED_ORIGINS=https://dashboard-staging.sardis.sh,https://staging.sardis.sh,http://localhost:5173

# ── Bridge (optional) ──
RELAY_API_KEY=<optional>
```

### Production-Specific (set on Cloud Run + GitHub Secrets)

```bash
# ── Identity ──
SARDIS_ENVIRONMENT=prod
SARDIS_CHAIN_MODE=live
SARDIS_DEFAULT_CHAIN=base_sepolia  # Default for sk_test_ keys
# sk_live_ keys auto-route to tempo via middleware

# ── Database ──
DATABASE_URL=${PRODUCTION_DATABASE_URL}   # Neon production

# ── Auth ──
JWT_SECRET_KEY=<production-specific-hex-64>      # DIFFERENT from staging
SARDIS_SECRET_KEY=<production-specific-urlsafe-32>
SARDIS_ADMIN_PASSWORD=<production-admin-pass>
SARDIS_ALLOW_PUBLIC_SIGNUP=1

# ── MPC Wallet (same Turnkey org) ──
SARDIS_MPC__NAME=turnkey
TURNKEY_ORGANIZATION_ID=<same-org>
TURNKEY_API_PUBLIC_KEY=<same-key>
TURNKEY_API_PRIVATE_KEY=<same-key>

# ── Chain RPCs ──
SARDIS_BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/<ALCHEMY_KEY>
SARDIS_TEMPO_RPC_URL=https://rpc.tempo.xyz

# ── Faucet (same wallet works for both envs — Base Sepolia only) ──
SARDIS_FAUCET_PRIVATE_KEY=<faucet-wallet-pk>

# ── Redis (Upstash) ──
SARDIS_REDIS_URL=<upstash-production-url>

# ── CORS ──
SARDIS_ALLOWED_ORIGINS=https://app.sardis.sh,https://sardis.sh,https://checkout.sardis.sh

# ── Monitoring ──
SENTRY_DSN=<sentry-dsn>
POSTHOG_API_KEY=<posthog-key>
```

### Shared (same value in both environments)

```bash
# Turnkey MPC — same org, wallets are environment-agnostic
TURNKEY_ORGANIZATION_ID=<same>
TURNKEY_API_PUBLIC_KEY=<same>
TURNKEY_API_PRIVATE_KEY=<same>

# Alchemy — same key works for all chains
SARDIS_BASE_SEPOLIA_RPC_URL=<same>

# Faucet — same wallet, only dispenses on Base Sepolia
SARDIS_FAUCET_PRIVATE_KEY=<same>
```

### Dashboard Env Vars (Vercel)

```bash
# Staging (dashboard-staging.sardis.sh)
VITE_API_URL=https://api-staging.sardis.sh

# Production (app.sardis.sh)
VITE_API_URL=https://api.sardis.sh
```

---

## Faucet Wallet Setup

### One-Time Setup

```bash
# 1. Generate a new wallet (or use existing testnet wallet)
python -c "from eth_account import Account; a = Account.create(); print(f'Address: {a.address}\nPrivate Key: {a.key.hex()}')"

# 2. Save the private key as SARDIS_FAUCET_PRIVATE_KEY

# 3. Fund the wallet:
#    a. Get Base Sepolia ETH: https://www.alchemy.com/faucets/base-sepolia
#       (0.1 ETH per request, enough for ~1000 faucet drips)
#    b. Get test USDC: https://faucet.circle.com (select Base Sepolia)
#       (Get multiple times — need ~10,000 USDC for demo period)

# 4. Verify funding:
#    https://sepolia.basescan.org/address/<FAUCET_ADDRESS>
```

### Faucet Economics

```
Per drip:         100 USDC
Gas per drip:     ~0.00001 ETH (~$0.0003)
Rate limit:       1 drip per org per 24h
Fund requirement: 10,000 USDC + 0.1 ETH (covers ~100 unique testers)
Refill:           Circle faucet (free, unlimited)
```

---

## DNS Mapping

| Subdomain | Target | Purpose |
|-----------|--------|---------|
| `api.sardis.sh` | Cloud Run `sardis-api` | Production API |
| `api-staging.sardis.sh` | Cloud Run `sardis-api-staging` | Staging API |
| `app.sardis.sh` | Vercel dashboard (prod) | Production dashboard |
| `dashboard-staging.sardis.sh` | Vercel dashboard (staging) | Staging dashboard |
| `sardis.sh` | Vercel landing (prod) | Production landing |
| `staging.sardis.sh` | Vercel landing (staging) | Staging landing |
| `checkout.sardis.sh` | Vercel checkout (prod) | Checkout UI |
| `guard.sardis.sh` | Cloud Run `sardis-guard` | Guard Intelligence (hackathon) |
| `guard-dashboard.sardis.sh` | Vercel guard-dashboard | Guard UI (hackathon) |

---

## Deploy Script Enhancements

### Current Gaps

1. `deploy-cloudrun.sh` doesn't run DB migrations
2. No post-deploy smoke test (only health check)
3. No staged rollout (goes 100% immediately)
4. Missing new env vars (faucet, signup, chain routing)

### Enhanced Deploy Script

```bash
# scripts/deploy.sh — unified deploy script
#
# Usage:
#   ./scripts/deploy.sh staging          # Deploy all to staging
#   ./scripts/deploy.sh production       # Deploy all to production
#   ./scripts/deploy.sh staging api      # Deploy only API to staging
#   ./scripts/deploy.sh staging dashboard # Deploy only dashboard
#
# Flow:
#   1. Validate env vars
#   2. Run DB migrations
#   3. Build + deploy API (Cloud Run)
#   4. Build + deploy Dashboard (Vercel)
#   5. Health check
#   6. Smoke test (signup → faucet → create mandate)
#   7. Report
```

### Smoke Test Script

```bash
# scripts/smoke-test.sh
#
# Runs after every deploy to verify full flow:
#
# 1. Health check:    GET /api/v2/health → 200
# 2. Signup:          POST /api/v2/auth/signup → 201 + sk_test_ key
# 3. Environment:     GET /api/v2/auth/environment → base_sepolia
# 4. Faucet:          POST /api/v2/faucet/drip → 200
# 5. Create mandate:  POST /api/v2/spending-mandates → 201
# 6. Create agent:    POST /api/v2/agents → 201
# 7. Cleanup test org
#
# Exit 0 = all passed, Exit 1 = failure (blocks production promote)
```

---

## GitHub Actions Enhancements

### Updated deploy.yml Flow

```
workflow_dispatch (staging or production)
    │
    ├── validate (existing: webhook conformance, CI check)
    │
    ├── deploy-api-{env}
    │   ├── Run DB migrations (alembic upgrade head)
    │   ├── Build Docker image (gcloud builds submit)
    │   ├── Deploy to Cloud Run (with new env vars)
    │   ├── Health check (GET /health → 200)
    │   └── Smoke test (signup → faucet → mandate flow)
    │
    ├── deploy-dashboard-{env}
    │   ├── Build with correct VITE_API_URL
    │   └── Deploy to Vercel
    │
    └── deploy-landing-{env}
        ├── Build
        └── Deploy to Vercel
```

### New Env Vars to Add to deploy-cloudrun.sh

```bash
# Add to the env var loop in deploy-cloudrun.sh:
SARDIS_FAUCET_PRIVATE_KEY
SARDIS_ALLOW_PUBLIC_SIGNUP
SARDIS_DEFAULT_CHAIN
RELAY_API_KEY
```

---

## Dashboard Vercel Configuration

### Staging Fix

Current `dashboard/vercel.json` proxies `/api/*` to `https://api.sardis.sh` (production). This needs to be environment-aware.

**Solution:** Use `VITE_API_URL` env var (already supported in client.ts). The Vercel proxy rewrite should be removed in favor of direct API calls with CORS.

```json
// dashboard/vercel.json (updated)
{
  "installCommand": "npm install --legacy-peer-deps",
  "buildCommand": "npx vite build",
  "outputDirectory": "dist",
  "rewrites": [
    { "source": "/(.*)", "destination": "/index.html" }
  ]
}
```

Dashboard `client.ts` already reads `VITE_API_URL` — just needs the Vercel project env var set correctly per environment.

---

## Implementation Checklist

### Phase A: Env Vars + Faucet Setup (30 min)

- [ ] Generate faucet wallet (address + private key)
- [ ] Fund faucet: Base Sepolia ETH (Alchemy faucet)
- [ ] Fund faucet: Test USDC (Circle faucet, multiple times)
- [ ] Generate staging JWT_SECRET_KEY
- [ ] Generate staging SARDIS_SECRET_KEY
- [ ] Set staging admin password

### Phase B: Staging Deploy (30 min)

- [ ] Set env vars on Cloud Run staging
- [ ] Run DB migrations (074, 075, 076)
- [ ] Deploy API to Cloud Run staging
- [ ] Deploy dashboard to Vercel staging (with VITE_API_URL=api-staging)
- [ ] Health check: `curl https://api-staging.sardis.sh/api/v2/health`
- [ ] Smoke test: signup → faucet → mandate → agent → payment

### Phase C: Production Deploy (30 min)

- [ ] Verify staging works end-to-end
- [ ] Set env vars on Cloud Run production
- [ ] Run DB migrations on production
- [ ] Deploy API to Cloud Run production
- [ ] Deploy dashboard to Vercel production
- [ ] Health check + smoke test on production
- [ ] Verify: new user signup returns wallet + next_steps

### Phase D: Deploy Scripts (1h)

- [ ] Create `scripts/deploy.sh` (unified deploy)
- [ ] Create `scripts/smoke-test.sh` (post-deploy verification)
- [ ] Update `deploy-cloudrun.sh` with new env vars
- [ ] Fix dashboard vercel.json (remove API proxy rewrite)
- [ ] Update GitHub Actions deploy.yml with smoke test step

---

## Security Considerations

1. **JWT_SECRET_KEY must differ between staging and production** — prevents staging tokens working on production
2. **SARDIS_FAUCET_PRIVATE_KEY** — only holds testnet USDC, no real value at risk
3. **Turnkey keys are shared** — same MPC org for both envs. Wallets are chain-scoped, so staging creates on Base Sepolia, production creates on Tempo
4. **sk_live_ keys are admin-assigned only** — no self-service access to mainnet
5. **Public signup** is gated by `SARDIS_ALLOW_PUBLIC_SIGNUP` — can be disabled per environment
6. **CORS origins** are environment-specific — staging dashboard can't call production API

## Monitoring

### Staging
- Health endpoint: `GET https://api-staging.sardis.sh/api/v2/health`
- Cloud Run console: GCP → Cloud Run → sardis-api-staging → Logs
- No Sentry/PostHog (keep noise-free)

### Production
- Health endpoint: `GET https://api.sardis.sh/api/v2/health`
- Sentry for error tracking (SENTRY_DSN)
- PostHog for usage analytics (POSTHOG_API_KEY)
- Cloud Run console: GCP → Cloud Run → sardis-api → Logs + Metrics

---

## Timeline

| Phase | Effort | When |
|-------|--------|------|
| A. Env vars + faucet | 30 min | Now |
| B. Staging deploy | 30 min | After A |
| C. Production deploy | 30 min | After B verified |
| D. Deploy scripts | 1h | After C |

**Total: ~2.5 hours to fully deployed on both environments.**

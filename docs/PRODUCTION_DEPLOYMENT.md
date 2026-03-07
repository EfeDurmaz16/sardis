# Sardis Production Deployment Guide

Complete guide for deploying Sardis to production (Base mainnet). Every required credential, service, and configuration step is documented with instructions on how to obtain each.

---

## Table of Contents

1. [Pre-Deployment Checklist](#pre-deployment-checklist)
2. [Infrastructure Services](#infrastructure-services)
3. [Environment Variables Reference](#environment-variables-reference)
4. [Smart Contract Deployment](#smart-contract-deployment)
5. [Cloud Run Deployment](#cloud-run-deployment)
6. [Go CLI Distribution](#go-cli-distribution)
7. [Post-Deployment Verification](#post-deployment-verification)

---

## Pre-Deployment Checklist

- [ ] GCP project created and billing enabled
- [ ] PostgreSQL database provisioned (Neon)
- [ ] Redis provisioned (Upstash)
- [ ] Domain DNS configured (`sardis.sh`, `checkout.sardis.sh`)
- [ ] All CRITICAL env vars set (see table below)
- [ ] Smart contracts deployed and verified
- [ ] Migrations run against production database
- [ ] Kill switch tested (activate/deactivate cycle)
- [ ] Health endpoint returns all-green

---

## Infrastructure Services

### 1. Google Cloud Platform (GCP)

**What:** Cloud Run hosting, Cloud Build, Container Registry

**How to set up:**
1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create project (e.g., `sardis-production`)
3. Enable APIs: Cloud Run, Cloud Build, Container Registry
4. Install `gcloud` CLI: `brew install google-cloud-sdk`
5. Authenticate: `gcloud auth login && gcloud config set project sardis-production`

**Env vars produced:**
- `GOOGLE_CLOUD_PROJECT` = your project ID
- `CLOUD_RUN_REGION` = `us-central1` (recommended)

---

### 2. Neon PostgreSQL

**What:** Serverless PostgreSQL database (50+ tables)

**How to set up:**
1. Sign up at [neon.tech](https://neon.tech)
2. Create a project → create a database `sardis`
3. Copy the connection string from the dashboard

**Env vars produced:**
- `DATABASE_URL` = `postgresql://user:pass@ep-xxx.us-east-2.aws.neon.tech/sardis?sslmode=require`

**Post-setup:** Run all migrations:
```bash
for f in packages/sardis-api/migrations/*.sql; do
  psql "$DATABASE_URL" -f "$f"
done
```

---

### 3. Upstash Redis

**What:** Serverless Redis for kill switch, TAP nonce cache, rate limiting, transaction cap tracking

**How to set up:**
1. Sign up at [upstash.com](https://upstash.com)
2. Create a Redis database (region: `us-east-1` for lowest latency to Cloud Run)
3. Copy the REST URL from the dashboard

**Env vars produced:**
- `UPSTASH_REDIS_URL` = `rediss://default:xxx@us1-xxx.upstash.io:6379`

> Alternatively set `SARDIS_REDIS_URL` or `REDIS_URL`. The platform checks all three in order.

---

### 4. Alchemy (Blockchain RPC)

**What:** Reliable RPC endpoints for Base mainnet and other chains

**How to set up:**
1. Sign up at [alchemy.com](https://www.alchemy.com)
2. Create an app for each chain you need (Base mainnet is required)
3. Copy the API key from the dashboard

**Env vars produced:**
- `SARDIS_BASE_RPC_URL` = `https://base-mainnet.g.alchemy.com/v2/YOUR_KEY`
- `SARDIS_ETHEREUM_RPC_URL` = `https://eth-mainnet.g.alchemy.com/v2/YOUR_KEY` (optional)
- `SARDIS_POLYGON_RPC_URL` = `https://polygon-mainnet.g.alchemy.com/v2/YOUR_KEY` (optional)
- `SARDIS_ARBITRUM_RPC_URL` = `https://arb-mainnet.g.alchemy.com/v2/YOUR_KEY` (optional)
- `SARDIS_OPTIMISM_RPC_URL` = `https://opt-mainnet.g.alchemy.com/v2/YOUR_KEY` (optional)

> Pattern: `SARDIS_{CHAIN}_RPC_URL` where CHAIN is the uppercase chain name.

---

### 5. Turnkey (MPC Wallet Custody)

**What:** Non-custodial MPC key management — creates and signs with agent wallets

**How to set up:**
1. Sign up at [turnkey.com](https://www.turnkey.com)
2. Create an organization
3. Go to Settings → API Keys → Create a new API key pair
4. Download the private key file (P-256 ECDSA)

**Env vars produced:**
- `TURNKEY_API_PUBLIC_KEY` = the public key from your API key pair
- `TURNKEY_API_PRIVATE_KEY` = the private key (PEM format, store securely)
- `TURNKEY_ORGANIZATION_ID` = your org ID from the dashboard
- `SARDIS_MPC__NAME` = `turnkey`

> Set `SARDIS_MPC__NAME=turnkey` to use Turnkey. Default is `simulated` (dev only).

---

### 6. Stripe Issuing (Virtual Cards)

**What:** Issue virtual debit cards funded from agent wallets

**How to set up:**
1. Sign up at [stripe.com](https://stripe.com)
2. Apply for Stripe Issuing access (requires business verification)
3. Once approved, go to Developers → API Keys
4. Copy the secret key

**Env vars produced:**
- `STRIPE_SECRET_KEY` = `sk_live_...`

> Cards are optional for MVP. The platform runs fine without this key.

---

### 7. iDenfy (KYC Verification)

**What:** Identity verification for agents and users ($0.55/verification)

**How to set up:**
1. Sign up at [idenfy.com](https://www.idenfy.com)
2. Complete business verification
3. Go to API Settings → copy API key and secret
4. Set up webhook endpoint: `https://your-domain/api/v2/compliance/idenfy/webhook`

**Env vars produced:**
- `IDENFY_API_KEY` = your API key
- `IDENFY_API_SECRET` = your API secret
- `IDENFY_WEBHOOK_SECRET` = your webhook signing secret
- `SARDIS_KYC_PRIMARY_PROVIDER` = `idenfy`

> Alternative: Persona (`PERSONA_API_KEY`, `PERSONA_TEMPLATE_ID`, `PERSONA_WEBHOOK_SECRET`)

---

### 8. Elliptic (AML/Sanctions Screening)

**What:** Blockchain address sanctions screening and risk scoring

**How to set up:**
1. Sign up at [elliptic.co](https://www.elliptic.co)
2. Request API access (enterprise sales process)
3. Once approved, get API key and secret from dashboard

**Env vars produced:**
- `ELLIPTIC_API_KEY` = your API key
- `ELLIPTIC_API_SECRET` = your API secret

> Alternative: Scorechain (`SCORECHAIN_API_KEY`) or Circle Compliance (`CIRCLE_API_KEY`)

---

### 9. Coinbase Onramp (Fiat-to-Crypto)

**What:** Allow users to buy USDC with fiat directly in checkout flow

**How to set up:**
1. Go to [Coinbase Developer Platform](https://portal.cdp.coinbase.com)
2. Create a project → create API key
3. Download the private key

**Env vars produced:**
- `COINBASE_CDP_API_KEY_NAME` = your API key name
- `COINBASE_CDP_API_KEY_PRIVATE_KEY` = private key content

---

### 10. Google OAuth (User Login)

**What:** "Sign in with Google" for the dashboard and CLI

**How to set up:**
1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials
2. Create OAuth 2.0 Client ID (Web application)
3. Add authorized redirect URIs:
   - `https://your-api-domain/api/v2/auth/google/callback`
   - `http://localhost:8000/api/v2/auth/google/callback` (dev)

**Env vars produced:**
- `GOOGLE_CLIENT_ID` = `xxxx.apps.googleusercontent.com`
- `GOOGLE_CLIENT_SECRET` = your client secret

---

### 11. Sentry (Error Tracking) — Optional

**What:** Error monitoring and performance tracking

**How to set up:**
1. Sign up at [sentry.io](https://sentry.io)
2. Create a Python project
3. Copy the DSN

**Env vars produced:**
- `SENTRY_DSN` = `https://xxx@xxx.ingest.sentry.io/xxx`
- `SENTRY_ENVIRONMENT` = `production`

---

### 12. PostHog (Analytics) — Optional

**What:** Product analytics and event tracking

**How to set up:**
1. Sign up at [posthog.com](https://posthog.com)
2. Create project → copy API key

**Env vars produced:**
- `POSTHOG_API_KEY` = your project API key

---

### 13. BaseScan (Contract Verification) — Optional

**What:** Verify deployed smart contracts on BaseScan for transparency

**How to set up:**
1. Sign up at [basescan.org](https://basescan.org)
2. Go to API Keys → Create new key

**Env vars produced:**
- `BASESCAN_API_KEY` = your API key (used during contract deployment only)

---

## Environment Variables Reference

### CRITICAL — Platform Will Not Start Without These

| Variable | Example | Source |
|----------|---------|--------|
| `DATABASE_URL` | `postgresql://user:pass@host/sardis?sslmode=require` | Neon dashboard |
| `SARDIS_ENVIRONMENT` | `production` | Set manually |
| `JWT_SECRET_KEY` | 64-char hex string | `python3 -c 'import secrets; print(secrets.token_hex(32))'` |
| `SARDIS_ADMIN_PASSWORD` | strong random password | Generate yourself (legacy, being deprecated) |
| `UPSTASH_REDIS_URL` | `rediss://default:xxx@host:6379` | Upstash dashboard |
| `SARDIS_BASE_RPC_URL` | `https://base-mainnet.g.alchemy.com/v2/KEY` | Alchemy dashboard |

### REQUIRED — Payments Will Not Work Without These

| Variable | Example | Source |
|----------|---------|--------|
| `TURNKEY_API_PUBLIC_KEY` | P-256 public key | Turnkey dashboard |
| `TURNKEY_API_PRIVATE_KEY` | P-256 private key (PEM) | Turnkey dashboard |
| `TURNKEY_ORGANIZATION_ID` | `org_xxx` | Turnkey dashboard |
| `SARDIS_MPC__NAME` | `turnkey` | Set manually |
| `SARDIS_TREASURY_ADDRESS` | `0x...` | Your treasury wallet address |

### RECOMMENDED — Important for Production Hardening

| Variable | Default | Purpose |
|----------|---------|---------|
| `SARDIS_GLOBAL_DAILY_CAP` | `1000000` | Platform-wide daily spend limit (USD) |
| `SARDIS_DEFAULT_ORG_DAILY_CAP` | `100000` | Per-org daily cap (USD) |
| `SARDIS_DEFAULT_AGENT_TX_CAP` | `10000` | Per-agent per-tx cap (USD) |
| `SARDIS_PLATFORM_FEE_BPS` | `50` | Platform fee in basis points (50 = 0.5%) |
| `SARDIS_FEE_MIN_AMOUNT` | `0.01` | Minimum fee amount in token units |
| `SARDIS_RECEIPT_HMAC_KEY` | random | HMAC key for execution receipt signing |
| `LOG_LEVEL` | `INFO` | Logging level |

### SMART CONTRACTS — Set After Deployment

| Variable | Purpose |
|----------|---------|
| `SARDIS_BASE_LEDGER_ANCHOR_ADDRESS` | SardisLedgerAnchor contract on Base mainnet |
| `SARDIS_BASE_REFUND_PROTOCOL_ADDRESS` | RefundProtocol (escrow) contract on Base mainnet |
| `SARDIS_BASE_SEPOLIA_REFUND_PROTOCOL_ADDRESS` | RefundProtocol on Base Sepolia (testnet) |

### COMPLIANCE — Required for Regulated Operations

| Variable | Purpose | Source |
|----------|---------|--------|
| `IDENFY_API_KEY` | KYC verification | iDenfy dashboard |
| `IDENFY_API_SECRET` | KYC verification | iDenfy dashboard |
| `IDENFY_WEBHOOK_SECRET` | Webhook signature verification | iDenfy dashboard |
| `SARDIS_KYC_PRIMARY_PROVIDER` | `idenfy` or `persona` | Set manually |
| `ELLIPTIC_API_KEY` | Sanctions screening | Elliptic dashboard |
| `ELLIPTIC_API_SECRET` | Sanctions screening | Elliptic dashboard |

### CHECKOUT — Required for "Pay with Sardis"

| Variable | Default | Purpose |
|----------|---------|---------|
| `SARDIS_CHECKOUT_CHAIN` | `base` | Chain for checkout payments (`base` for mainnet) |
| `STRIPE_SECRET_KEY` | — | Stripe Issuing (virtual cards, optional) |

### AUTHENTICATION — User Login

| Variable | Purpose | Source |
|----------|---------|--------|
| `GOOGLE_CLIENT_ID` | Google OAuth | GCP Console |
| `GOOGLE_CLIENT_SECRET` | Google OAuth | GCP Console |

### OPTIONAL — Nice to Have

| Variable | Default | Purpose |
|----------|---------|---------|
| `SENTRY_DSN` | — | Error tracking |
| `POSTHOG_API_KEY` | — | Product analytics |
| `SARDIS_ENABLE_SCHEDULER` | `false` | Background job scheduler |
| `SARDIS_ENABLE_DEPOSIT_MONITOR` | `false` | On-chain deposit monitoring |
| `SARDIS_ENABLE_SIDE_EFFECT_WORKER` | `false` | Side-effect processing worker |
| `SARDIS_TAP_ENFORCEMENT` | `warn` | TAP protocol enforcement (`strict`/`warn`/`off`) |
| `SARDIS_TAP_JWKS_URL` | — | JWKS endpoint for TAP verification |
| `SARDIS_KYA_ENFORCEMENT_ENABLED` | `false` | Know-Your-Agent enforcement |
| `SARDIS_PUBLIC_METRICS` | `false` | Expose metrics endpoint publicly |
| `SARDIS_STRICT_CONFIG` | `true` in prod | Fail on config validation errors |

### ALTERNATIVE SIGNERS — If Not Using Turnkey

| Variable | Purpose |
|----------|---------|
| `SARDIS_EOA_PRIVATE_KEY` | Raw private key (EOA signer, dev/testing) |
| `SARDIS_EOA_ADDRESS` | EOA address |
| `FIREBLOCKS_API_KEY` | Fireblocks MPC |
| `FIREBLOCKS_API_SECRET` | Fireblocks MPC |
| `SARDIS_CIRCLE_WALLET_API_KEY` | Circle Programmable Wallets |
| `SARDIS_CIRCLE_ENTITY_SECRET` | Circle entity secret |
| `SARDIS_CIRCLE_LIVE_SIGNER_ENABLED` | Enable live Circle signing |
| `SARDIS_CIRCLE_DEFAULT_WALLET_ID` | Default Circle wallet |
| `SARDIS_CIRCLE_DEFAULT_ADDRESS` | Default Circle address |
| `LIT_PROTOCOL_API_KEY` | Lit Protocol MPC |
| `COINBASE_CDP_API_KEY_NAME` | Coinbase CDP |
| `COINBASE_CDP_API_KEY_PRIVATE_KEY` | Coinbase CDP |

---

## Smart Contract Deployment

### Prerequisites

1. **Foundry** installed: `curl -L https://foundry.paradigm.xyz | bash && foundryup`
2. **Deployer wallet** with ~0.001 ETH on Base mainnet
   - Create a fresh wallet for deployment (don't use your main wallet)
   - Fund via bridge from Ethereum or buy ETH on Base
3. **Alchemy Base RPC URL** (from step 4 above)
4. **BaseScan API key** (optional, for verification)

### Deploy

```bash
# Set required env vars
export PRIVATE_KEY="0x..."                    # deployer wallet private key
export SARDIS_ADDRESS="0x..."                 # Sardis platform address (becomes escrow arbiter)
export BASE_RPC_URL="https://base-mainnet.g.alchemy.com/v2/YOUR_KEY"
export BASESCAN_API_KEY="YOUR_KEY"            # optional

# Run deployment
./scripts/deploy-mainnet-contracts.sh
```

### What Gets Deployed

| Contract | Purpose | Pre-deployed? |
|----------|---------|---------------|
| **SardisLedgerAnchor** | On-chain audit trail anchoring | No — deploy |
| **RefundProtocol** | Circle's audited escrow (Apache 2.0) | No — deploy |
| Zodiac Roles | Policy module | Yes: `0x9646fDAD06d3e24444381f44362a3B0eB343D337` |
| Circle Paymaster | USDC gas sponsorship | Yes: `0x0578cFB241215b77442a541325d6A4E6dFE700Ec` |
| Safe ProxyFactory | Smart account deployment | Yes: `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` |

### After Deployment

1. Copy deployed contract addresses from the deployment log
2. Update `contracts/deployments/base.json`
3. Set Cloud Run env vars:
```bash
gcloud run services update sardis-api \
  --region us-central1 \
  --update-env-vars \
    SARDIS_BASE_LEDGER_ANCHOR_ADDRESS=0x...,\
    SARDIS_BASE_REFUND_PROTOCOL_ADDRESS=0x...
```

---

## Cloud Run Deployment

### First-Time Setup

```bash
# 1. Authenticate
gcloud auth login
gcloud config set project sardis-production

# 2. Set all env vars (do this ONCE via console or CLI)
gcloud run services update sardis-api \
  --region us-central1 \
  --update-env-vars \
    SARDIS_ENVIRONMENT=production,\
    DATABASE_URL="postgresql://...",\
    UPSTASH_REDIS_URL="rediss://...",\
    JWT_SECRET_KEY="$(python3 -c 'import secrets; print(secrets.token_hex(32))')",\
    SARDIS_ADMIN_PASSWORD="$(python3 -c 'import secrets; print(secrets.token_hex(16))')",\
    SARDIS_BASE_RPC_URL="https://base-mainnet.g.alchemy.com/v2/...",\
    TURNKEY_API_PUBLIC_KEY="...",\
    TURNKEY_API_PRIVATE_KEY="...",\
    TURNKEY_ORGANIZATION_ID="...",\
    SARDIS_MPC__NAME=turnkey,\
    SARDIS_TREASURY_ADDRESS="0x...",\
    SARDIS_GLOBAL_DAILY_CAP=1000000,\
    SARDIS_DEFAULT_ORG_DAILY_CAP=100000,\
    SARDIS_DEFAULT_AGENT_TX_CAP=10000
```

> **WARNING:** Always use `--update-env-vars`, NEVER `--set-env-vars`. The latter wipes all existing vars.

### Deploy New Version

```bash
# Uses deploy-cloudrun.sh which handles build + deploy
./scripts/deploy-cloudrun.sh production
```

### Custom Domain

```bash
gcloud run domain-mappings create \
  --service sardis-api \
  --domain api.sardis.sh \
  --region us-central1
```

---

## Go CLI Distribution

### Install via Go

```bash
go install github.com/EfeDurmaz16/sardis/packages/sardis-cli-go@latest
```

### Install via Shell Script (macOS/Linux)

```bash
curl -sSL https://sardis.sh/install.sh | sh
```

### Install via Homebrew (macOS)

```bash
brew tap EfeDurmaz16/tap
brew install sardis
```

### Build from Source

```bash
cd packages/sardis-cli-go
make build      # → bin/sardis
make install    # → $GOPATH/bin/sardis
```

### Configure After Install

```bash
sardis login                          # Interactive login
sardis --api-url https://api.sardis.sh status   # Check connection
sardis dashboard                      # Launch TUI
```

---

## Post-Deployment Verification

### 1. Health Check

```bash
curl https://api.sardis.sh/health | jq .
```

Expected: `status: "healthy"`, all components green, kill switch `"clear"`.

### 2. Kill Switch Test

```bash
# Activate
sardis kill-switch activate --scope global --reason "deployment_test"

# Verify payments blocked
curl -X POST https://api.sardis.sh/api/v2/payments/send \
  -H "X-API-Key: ..." -H "Content-Type: application/json" \
  -d '{"amount": "1.00", "currency": "USDC", "to": "0x..."}' \
  # Should return 503

# Deactivate
sardis kill-switch deactivate --scope global
```

### 3. Database Connectivity

```bash
curl https://api.sardis.sh/health | jq '.components.database'
# Should show: {"status": "healthy", "latency_ms": <number>}
```

### 4. Redis Connectivity

```bash
curl https://api.sardis.sh/health | jq '.components.redis'
# Should show: {"status": "healthy", "latency_ms": <number>}
```

### 5. Contract Verification

```bash
# Check on BaseScan
open "https://basescan.org/address/<LEDGER_ANCHOR_ADDRESS>"
open "https://basescan.org/address/<REFUND_PROTOCOL_ADDRESS>"
```

### 6. End-to-End Payment Test

```bash
# Create agent
sardis agents create --name "test-agent" --type autonomous

# Create wallet
sardis wallets create --agent-id <agent_id> --chain base

# Small test payment (use testnet first!)
sardis pay <agent_id> <recipient> 0.01 --currency USDC --chain base
```

---

## Cost Estimates (Monthly)

| Service | Plan | Est. Cost |
|---------|------|-----------|
| GCP Cloud Run | Pay-per-use | $10-50 |
| Neon PostgreSQL | Free → Pro | $0-19 |
| Upstash Redis | Free → Pro | $0-10 |
| Alchemy | Free → Growth | $0-49 |
| Turnkey | Contact sales | Varies |
| iDenfy | $0.55/verification | Pay-per-use |
| Elliptic | Enterprise | Contact sales |
| Sentry | Free → Team | $0-26 |
| **Total (MVP)** | | **~$50-150/mo** |

---

## Security Reminders

1. **Never commit `.env` files** — use Cloud Run env vars or GCP Secret Manager
2. **Rotate `JWT_SECRET_KEY`** periodically — all active sessions will be invalidated
3. **Use separate deployer wallets** — never deploy contracts with treasury keys
4. **Enable kill switch monitoring** — set up alerts for `kill_switch.activated` events
5. **Transaction caps are your safety net** — start conservative, increase as needed
6. **Redis is required in production** — in-memory fallbacks are dev-only
7. **Run migrations before deploying** — new code may depend on new tables
8. **Test on Base Sepolia first** — set `SARDIS_CHECKOUT_CHAIN=base_sepolia` for staging

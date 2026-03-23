# Sardis Launch Checklist — Deadline: Tuesday March 25, 2026

> Owner: Efe Baran Durmaz
> Last updated: 2026-03-23

---

## PRIORITY 1: Auth & Email (15 min)

- [ ] Resend hesap ac → [resend.com](https://resend.com)
- [ ] sardis.sh domain ekle → DNS records al
- [ ] DKIM TXT record ekle: `vercel dns add sardis.sh resend._domainkey TXT "RESEND_VALUE"`
- [ ] API key al (`re_...`)
- [ ] `./scripts/setup-production.sh` → Resend key yapistir
- [ ] Test: `app.sardis.sh/forgot-password` → email geldi mi?

## PRIORITY 2: Billing (10 min)

- [ ] Polar.sh hesap ac → org `sardislabs` olustur → [polar.sh](https://polar.sh)
- [ ] 2 product olustur: Starter $49/mo, Growth $249/mo
- [ ] Organization Access Token al (`polar_oat_...`)
- [ ] Webhook URL set et: `api.sardis.sh/api/v2/billing/polar-webhook`
- [ ] `./scripts/setup-production.sh` → Polar credentials yapistir
- [ ] Test: `app.sardis.sh` → Billing → Upgrade

## PRIORITY 3: Turnkey MPC Fix (kritik — walletlar bu olmadan calismaz)

- [ ] Turnkey dashboard'a gir → [turnkey.com](https://turnkey.com)
- [ ] Organization ID kontrol et
- [ ] Yeni API key olustur (eski 400 veriyor)
- [ ] Cloud Run'a set et:
  ```bash
  gcloud run services update sardis-api-staging --region us-east1 \
    --update-env-vars "TURNKEY_API_PUBLIC_KEY=NEW,TURNKEY_API_PRIVATE_KEY=NEW"
  gcloud run services update sardis-api-staging --region europe-west1 \
    --update-env-vars "TURNKEY_API_PUBLIC_KEY=NEW,TURNKEY_API_PRIVATE_KEY=NEW"
  ```
- [ ] Test: wallet olustur → `addresses` bos olmamali
  ```bash
  curl -X POST api.sardis.sh/api/v2/wallets \
    -H "X-API-Key: YOUR_KEY" -H "Content-Type: application/json" \
    -d '{"agent_id":"AGENT_ID","chain":"base_sepolia"}'
  ```

## PRIORITY 4: E2E KYC Gate Test (Turnkey fix'ten sonra)

- [x] Didit webhook URL set: `api.sardis.sh/api/v2/kyc/webhook`
- [ ] Yeni hesap ac → signup → `sk_test_` key al
- [ ] Agent olustur → wallet olustur → faucet'ten USDC al
- [ ] Go Live → KYC tamamla → `sk_live_` key al
- [ ] `sk_live_` key ile Tempo mainnet'te islem yap

## PRIORITY 5: Optional

- [ ] Google OAuth client olustur → `./scripts/setup-production.sh`
- [ ] Passkey aktiflestir:
  ```bash
  cd dashboard-next
  npm install @simplewebauthn/server @simplewebauthn/browser
  # auth.ts'deki TODO'lari uncomment et
  ```
- [ ] YC review credentials test et:
  ```
  Email:    yc-review@sardis.sh
  Password: SardisYC2026!
  ```

---

## Already Done (no action needed)

- [x] Next.js 14 dashboard (123 pages) — sardis.sh / app.sardis.sh / dashboard.sardis.sh
- [x] better-auth + Neon PostgreSQL (ba_ tables)
- [x] Didit KYC provider (webhook test passed, 200 OK)
- [x] Monokrom grayscale theme (Linear/Vercel inspired)
- [x] driver.js product tour (6 steps)
- [x] PostHog analytics (key set)
- [x] 4 domain consolidation
- [x] 50+ bug fixes, 50 atomic commits
- [x] SPF DNS updated for Resend
- [x] Polar adapter fixed (checkout endpoint + webhook header)
- [x] ERC-8004 deployed on Tempo mainnet
- [x] 77 DB migrations applied
- [x] Setup script: `scripts/setup-production.sh`
- [x] Operational reference: `OPERATIONAL_CHECKLIST.md`

---

## PRIORITY 6: OSS Tool Activation (enable when ready)

All tools are installed and opt-in. Enable via env vars:

- [ ] **OpenTelemetry** — trace payment pipeline
  ```bash
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "SARDIS_OTEL_ENABLED=1,OTEL_EXPORTER_OTLP_ENDPOINT=https://YOUR_GRAFANA_OTLP,OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic ..."
  ```
  Sign up for Grafana Cloud free tier (50GB logs): grafana.com

- [ ] **Langfuse** — trace agent reasoning → payment decisions
  ```bash
  # Option A: Langfuse Cloud (free tier)
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "SARDIS_LANGFUSE_ENABLED=1,LANGFUSE_PUBLIC_KEY=pk_...,LANGFUSE_SECRET_KEY=sk_..."
  # Option B: Self-host (Docker + existing Postgres/Redis)
  docker run -d -p 3100:3000 langfuse/langfuse:latest
  ```

- [ ] **Convoy** — enterprise webhook delivery
  ```bash
  # Deploy Convoy
  docker run -d -p 5005:5005 frain-dev/convoy:latest
  # Set env vars
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "CONVOY_API_URL=https://convoy.sardis.sh,CONVOY_API_KEY=...,CONVOY_PROJECT_ID=..."
  ```

- [ ] **Infisical** — centralized secrets (when team grows)
  ```bash
  gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
    "SARDIS_INFISICAL_ENABLED=1,INFISICAL_CLIENT_ID=...,INFISICAL_CLIENT_SECRET=...,INFISICAL_PROJECT_ID=..."
  ```

- [ ] **Apache Superset** — internal BI dashboards
  ```bash
  docker run -d -p 8088:8088 apache/superset:latest
  # Connect to Neon PostgreSQL, see docs/integrations/superset-setup.md
  ```

- [ ] **k6 load test** — run before investor meetings
  ```bash
  brew install k6  # or download from k6.io
  K6_API_KEY=sk_test_... k6 run tests/load/payment-flow.js
  ```

---

## Architecture

```
sardis.sh / app.sardis.sh / dashboard.sardis.sh
  → Vercel (Next.js 14 dashboard-next/)
  → / = landing, /login = auth, /overview = dashboard, /docs = docs

api.sardis.sh
  → Cloud Run (FastAPI, 47+ routers, 7/7 health)

Neon PostgreSQL → 77 migrations, ba_ tables for better-auth
Didit → KYC (500 free/mo)
Turnkey → TEE wallet signing (needs fix)
PostHog → Analytics (project 352257)
```

---

## Key Research Findings

- **Turnkey**: TEE-based (not MPC), supports ALL EVM chains including Tempo. $0.01/sig on Pro.
- **Tempo**: EURC supported, built-in FX DEX, CCTP planned, ERC-8004 deployed
- **Circle Nanopayments**: Testnet, $0.000001 minimum, gas-free — watch for mainnet
- **Privy**: Stripe-owned, has Tempo MPP blog post — potential future alternative
- **Protocol compat**: AP2, TAP, ACP, A2A, MCP, MPP all work with Tempo

# Investor Demo Operator Kit (Private)

This file contains the operational content removed from the public `/demo` page.

## 1) Core Environment Variables

Use this minimum set for the private live mode on `/demo`:

| Env Var | Example | Purpose |
|---|---|---|
| `SARDIS_API_URL` | `https://api-staging.sardis.sh` | Base URL of Sardis API (staging/sandbox) |
| `SARDIS_API_KEY` | `sk_live_xxx...` | Server-side API key used by `/api/demo-proxy` |
| `DEMO_OPERATOR_PASSWORD` | `SardisDemo2026!` | Shared operator password for live mode unlock |

Optional for richer live flow:

| Env Var | Purpose |
|---|---|
| `DEMO_LIVE_AGENT_ID` | Agent used by `/api/v2/policies/check` |
| `DEMO_LIVE_CARD_ID` | Card used by `/api/v2/cards/{id}/simulate-purchase` |
| `DATABASE_URL` | Neon Postgres connection for demo event logging |

## 2) Recording Artifacts

### 2.1 Investor flow runner

```bash
python3 scripts/investor_demo_flow.py \
  --base-url "$SARDIS_API_URL" \
  --admin-email "$ADMIN_EMAIL" \
  --admin-password "$ADMIN_PASSWORD" \
  --hybrid-live
```

### 2.2 MCP bootstrap with payment identity

```bash
npx @sardis/mcp-server init \
  --mode live \
  --api-url "$SARDIS_API_URL" \
  --api-key "$SARDIS_API_KEY" \
  --payment-identity "<spi_...>"
```

### 2.3 Voiceover script

- `docs/release/investor-demo-voiceover-script.md`

## 3) Output Artifacts After Running

- `artifacts/investor-demo/investor-demo-<run-id>.json`
- `artifacts/investor-demo/investor-demo-<run-id>.md`

## 4) How To Create The 3 Required Variables

1. `SARDIS_API_URL`
   Use your staging API deployment URL. Confirm `GET ${SARDIS_API_URL}/health` or `/api/v2/metrics/health` returns 200.

2. `SARDIS_API_KEY`
   Create from Sardis API key endpoint using admin auth:
   - `POST /api/v2/api-keys` with scopes that include policy/cards endpoints.
   - Store only in server env (Vercel/hosting secrets), never in browser code.

3. `DEMO_OPERATOR_PASSWORD`
   Generate a strong shared password:
   - `openssl rand -base64 24`
   - store in hosting secret manager
   - share with internal team only (not investors)

# @sardis/mpp-proxy

**Make your API earn money from AI agents in 5 minutes.**

A payment-gating reverse proxy that adds [MPP](https://mpp.dev) (Machine Payments Protocol) to any API — no code changes required. Built as a Cloudflare Worker with Sardis policy enforcement and audit trail.

```
                  ┌──────────────────────────────────────────┐
                  │            Sardis MPP Proxy              │
  AI Agent        │                                          │        Your API
  ─────────►  402 │  1. Is route protected?                  │  ──────────►
              ◄── │  2. Return 402 + payment challenge       │
                  │  3. Verify payment credential (mppx)     │
  Payment ───►    │  4. Check Sardis policy (mandate/budget) │
                  │  5. Forward to origin API                │  ──────────►
              ◄── │  6. Return response + Payment-Receipt    │  ◄──────────
                  │  7. Log to Sardis audit trail             │
                  └──────────────────────────────────────────┘
```

## Quick Start

### 1. Install

```bash
npx sardis proxy init --origin https://api.example.com
cd my-paid-api
npm install
```

### 2. Configure secrets

```bash
# Generate an MPP secret key
wrangler secret put MPP_SECRET_KEY

# Set your recipient wallet address
wrangler secret put PAY_TO

# (Optional) Enable Sardis policy enforcement
wrangler secret put SARDIS_API_KEY
```

### 3. Deploy

```bash
npm run deploy
```

Your API is now payment-gated. AI agents will receive a `402 Payment Required` response with a payment challenge, pay via Tempo, and get access.

## How It Works

1. **Request arrives** at your proxy Worker
2. **Route check** — is this path in the `protectedRoutes` config?
3. **No payment?** Return `HTTP 402` with `WWW-Authenticate: Payment` header containing the price, recipient address, and accepted payment methods
4. **Payment received?** The `mppx` SDK verifies the `Authorization: Payment` credential on-chain
5. **Sardis policy** — before forwarding, check the agent's spending mandate, budget limits, and vendor allowlist via the Sardis API
6. **Forward** the request to your origin API and return the response with a `Payment-Receipt` header
7. **Audit** — fire-and-forget log to the Sardis audit trail for compliance and analytics

## Configuration

### Protected Routes

Set per-route pricing via the `PROTECTED_ROUTES` environment variable (JSON array):

```json
[
  { "path": "/v1/data/*", "priceUsd": "0.01", "description": "Data query" },
  { "path": "/v1/compute/*", "priceUsd": "0.10", "description": "Compute job" },
  { "path": "/v1/models/train", "priceUsd": "1.00", "description": "Model training" }
]
```

Or in `wrangler.toml`:

```toml
[vars]
ORIGIN_URL = "https://api.example.com"
PROTECTED_ROUTES = '[{"path":"/v1/data/*","priceUsd":"0.01","description":"Data query"}]'
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `MPP_SECRET_KEY` | Yes | HMAC key for MPP payment verification |
| `PAY_TO` | Yes | Recipient wallet address (`0x...`) |
| `SARDIS_API_KEY` | No | Sardis API key for policy + audit |
| `ORIGIN_URL` | No | Origin API URL (or use service binding) |
| `SARDIS_API_URL` | No | Sardis API base URL (default: `https://api.sardis.sh`) |
| `PAYMENT_CURRENCY` | No | USDC contract address (default: Tempo mainnet USDC) |
| `PROTECTED_ROUTES` | No | JSON array of route configs (default: `/*` at $0.01) |
| `PAYMENT_METHODS` | No | JSON array of methods (default: `["tempo"]`) |

### Service Binding (Worker-to-Worker)

Instead of proxying to an external URL, you can bind directly to another Cloudflare Worker:

```toml
[[services]]
binding = "ORIGIN_SERVICE"
service = "your-api-worker"
```

## Sardis Policy Integration

When `SARDIS_API_KEY` is configured, every payment is checked against the agent's Sardis spending mandate before being accepted:

- **Budget limits** — reject if the agent has exceeded their spending cap
- **Vendor allowlist** — reject if the origin API is not on the allowed vendor list
- **Rate limiting** — enforce per-agent payment rate limits
- **Audit trail** — every payment (accepted or rejected) is logged

This prevents financial hallucinations at the infrastructure layer: an AI agent cannot overspend even if it tries.

## Built-in Endpoints

| Endpoint | Auth | Description |
|----------|------|-------------|
| `/__mpp/health` | Public | Health check (returns `{ status: "ok" }`) |
| `/__mpp/config` | Public | Proxy configuration (secrets redacted) |

## CLI Commands

```bash
# Scaffold a new proxy project
sardis proxy init --origin https://api.example.com

# Deploy to Cloudflare Workers
sardis proxy deploy
```

## MCP Tools

The Sardis MCP server includes tools for calling MPP-enabled APIs:

```
sardis_call_paid_api   — Call any MPP API with automatic 402 payment handling
sardis_preview_paid_api — Preview the cost of an MPP API call without paying
```

## Testing

```bash
# Health check
curl https://your-proxy.workers.dev/__mpp/health

# Trigger a 402 challenge
curl -i https://your-proxy.workers.dev/v1/data/test

# Pay with the Tempo CLI
npx mppx https://your-proxy.workers.dev/v1/data/test
```

## Development

```bash
# Install dependencies
npm install

# Local development
npm run dev

# Run tests
npm test

# Type check
npm run typecheck
```

## License

MIT

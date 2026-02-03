# Secret Management Guide

## Environment Variables

### Required for Production

| Variable | Service | Description |
|----------|---------|-------------|
| `DATABASE_URL` | Neon PostgreSQL | Connection string (`postgresql://user:pass@host/db?sslmode=require`) |
| `SARDIS_API_KEY` | Internal | API key for authentication (hashed with SHA-256) |
| `TURNKEY_API_KEY` | Turnkey | MPC custody API key |
| `TURNKEY_API_PRIVATE_KEY` | Turnkey | P-256 private key for request signing (PEM or hex) |
| `TURNKEY_ORGANIZATION_ID` | Turnkey | Organization identifier |

### Optional Services

| Variable | Service | Description |
|----------|---------|-------------|
| `PERSONA_API_KEY` | Persona | KYC verification |
| `PERSONA_TEMPLATE_ID` | Persona | Inquiry template ID |
| `PERSONA_WEBHOOK_SECRET` | Persona | Webhook signature verification |
| `ELLIPTIC_API_KEY` | Elliptic | AML/sanctions screening |
| `ELLIPTIC_API_SECRET` | Elliptic | API secret for HMAC auth |
| `LITHIC_API_KEY` | Lithic | Virtual card issuance |
| `STRIPE_SECRET_KEY` | Stripe | Payment processing |
| `SENTRY_DSN` | Sentry | Error monitoring |
| `UPSTASH_REDIS_URL` | Upstash | Redis cache URL |
| `SARDIS_REDIS_URL` | Redis | Alternative Redis URL |

### Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `SARDIS_ENVIRONMENT` | `dev` | Environment (`dev`, `staging`, `production`) |
| `LOG_LEVEL` | `INFO` | Logging level |
| `VITE_API_URL` | (empty) | Dashboard API base URL |
| `VITE_USE_V2_API` | `false` | Use V2 API endpoints |

## Vercel Deployment

### Setting Environment Variables

1. Go to your Vercel project **Settings > Environment Variables**
2. Add each variable for the appropriate environment (Production / Preview / Development)
3. For sensitive values, enable encryption (on by default)

### Recommended Setup

**Production only** (don't expose in Preview):
- `DATABASE_URL`
- `TURNKEY_API_KEY`, `TURNKEY_API_PRIVATE_KEY`, `TURNKEY_ORGANIZATION_ID`
- `STRIPE_SECRET_KEY`
- `PERSONA_API_KEY`
- `ELLIPTIC_API_KEY`, `ELLIPTIC_API_SECRET`
- `LITHIC_API_KEY`

**All environments:**
- `SENTRY_DSN` (different DSNs per environment recommended)
- `SARDIS_ENVIRONMENT` (set to `production`, `staging`, or `dev`)
- `LOG_LEVEL`

### Vercel CLI

```bash
# Set a production secret
vercel env add TURNKEY_API_KEY production

# Pull env vars for local development
vercel env pull .env.local
```

## Secret Rotation

### Turnkey API Keys
1. Generate new API key pair in the Turnkey dashboard
2. Update `TURNKEY_API_KEY` and `TURNKEY_API_PRIVATE_KEY` in Vercel
3. Redeploy the API service
4. Revoke the old key pair in Turnkey dashboard

### Database Credentials
1. In the Neon console, create a new role or reset the password
2. Update `DATABASE_URL` in Vercel
3. Redeploy. Existing connections will be terminated on next pool refresh

### Stripe Keys
1. Roll the key in Stripe Dashboard > Developers > API keys
2. Update `STRIPE_SECRET_KEY` in Vercel
3. Redeploy — old key is immediately invalidated

### Persona / Elliptic / Lithic
1. Generate new API key in respective provider dashboard
2. Update the corresponding env var in Vercel
3. Redeploy
4. Revoke old key in provider dashboard

### SARDIS_API_KEY (internal)
1. Generate a new key: `python -c "import secrets; print('sk_live_' + secrets.token_hex(32))"`
2. Update in Vercel and distribute to API consumers
3. Old keys are invalidated by hash comparison

## Development vs Production

### Local Development
Use `.env.local` (git-ignored) for local secrets:

```bash
# .env.local
DATABASE_URL=postgresql://localhost/sardis_dev
SARDIS_ENVIRONMENT=dev
SARDIS_API_KEY=sk_test_dev_key
```

### Production Checklist
- [ ] All secrets set in Vercel as encrypted environment variables
- [ ] `SARDIS_ENVIRONMENT=production`
- [ ] Neon `DATABASE_URL` uses SSL (`?sslmode=require`)
- [ ] Sentry DSN configured for production project
- [ ] Turnkey keys are production (not sandbox)
- [ ] Stripe key is `sk_live_` (not `sk_test_`)
- [ ] Persona environment set to `production`
- [ ] Lithic API key is production

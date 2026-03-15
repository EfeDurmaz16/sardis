# Sardis Go-Live Operational Checklist

**Created:** March 16, 2026
**Owner:** Efe Baran Durmaz
**Status:** Pre-launch

All code work is complete (34 atomic commits across 3 sessions). These are the operational tasks only Efe can do.

---

## CRITICAL — Before Go-Live

### Infrastructure & Deployment
- [ ] **Fund deployer wallet** — Need ~$5-10 in ETH on Base mainnet for contract deployment gas
- [ ] **Deploy smart contracts to Base mainnet** — Run `./scripts/deploy-mainnet-contracts.sh` (needs: PRIVATE_KEY, SARDIS_ADDRESS, BASE_RPC_URL)
- [ ] **Verify contracts on BaseScan** — After deployment, verify source code on basescan.org
- [ ] **Set production env vars on Cloud Run** — Use `gcloud run services update sardis-api-staging --update-env-vars` (NEVER `--set-env-vars`):
  - `JWT_SECRET_KEY` — Generate: `python -c "import secrets; print(secrets.token_hex(32))"`
  - `SARDIS_ENVIRONMENT=production`
  - `SARDIS_ALLOW_PUBLIC_SIGNUP=true` (set this LAST — it's the go-live switch)
  - `SARDIS_BILLING_BILLING_ENABLED=true`
  - `SARDIS_PLATFORM_FEE_BPS=50`
  - `SARDIS_TREASURY_ADDRESS=0x...` (your fee collection wallet on Base)
  - `SARDIS_FEE_MIN_AMOUNT=1.00`
  - All Stripe vars (see Billing section below)
  - All SMTP vars (see Email section below)
  - `POSTHOG_API_KEY` (from PostHog dashboard)
- [ ] **Run database migrations** — `alembic upgrade head` (new migrations: 070_password_reset.sql)
- [ ] **Verify health check** — `curl https://api.sardis.sh/health` returns all components healthy
- [ ] **Push code to GitHub** — `git push` (34 commits pending)

### Billing & Revenue
- [ ] **Create Stripe account** (personal initially, transfer to corp later)
- [ ] **Create Stripe products + prices:**
  - Product: "Sardis Starter" → Price: $49/mo recurring
  - Product: "Sardis Growth" → Price: $249/mo recurring
- [ ] **Get Stripe env vars:**
  - `SARDIS_BILLING_STRIPE_SECRET_KEY` (sk_live_...)
  - `SARDIS_BILLING_STRIPE_PRICE_STARTER` (price_...)
  - `SARDIS_BILLING_STRIPE_PRICE_GROWTH` (price_...)
- [ ] **Register Stripe billing webhook:**
  - URL: `https://api.sardis.sh/api/v2/billing/webhook`
  - Events: `checkout.session.completed`, `customer.subscription.updated`, `customer.subscription.deleted`, `invoice.payment_failed`
  - Get: `SARDIS_BILLING_STRIPE_WEBHOOK_SECRET` (whsec_...)
- [ ] **Configure Stripe Billing Portal branding** (logo, colors, return URL)

### Email (Required for Password Reset)
- [ ] **Set up SMTP** — Options: Resend, SendGrid, AWS SES, Postmark
  - `SMTP_HOST` (e.g., smtp.resend.com)
  - `SMTP_PORT` (587 for STARTTLS, 465 for SSL)
  - `SMTP_USER`
  - `SMTP_PASSWORD`
  - `SMTP_FROM_EMAIL` (noreply@sardis.sh)
- [ ] **Configure DNS** — SPF, DKIM, DMARC records for sardis.sh domain
- [ ] **Test password reset email** — Register account, trigger forgot-password, verify email arrives

### Analytics
- [ ] **Create PostHog account** (free tier) → get `POSTHOG_API_KEY`

---

## HIGH PRIORITY — Within First Week

### Legal & Corporate
- [ ] **Start Stripe Atlas incorporation** — Delaware C-corp, $500, takes 1-2 weeks
  - 10M authorized shares, $0.0001 par value
  - File 83(b) election within 30 days of incorporation
- [ ] **Open Mercury/Brex bank account** — After incorporation completes
- [ ] **Set up cap table** — Carta or Pulley (free tier)

### Outreach & Partnerships
- [ ] **Send design partner LOI emails** — Helicone, AutoGPT, OpenClaw, Activepieces
  - Template: "Free usage for 6 months, dedicated support, co-marketing. We ask: signed LOI, integration commitment, logo permission."
- [ ] **Formalize advisory relationships** — Email Coinbase, Stripe, Circle, Base, Lightspark, Solana, Bridge contacts
  - Ask: "Would you be comfortable being listed as an advisor on our website?"
  - If formal: 0.1-0.25% equity vesting over 2 years
- [ ] **Create Discord server** — Channels: #general, #support, #developers, #announcements, #feedback
  - Framework channels: #langchain, #crewai, #openai-agents, #vercel-ai
  - Post invite link in docs, dashboard footer, SDK README

### Testing & Verification
- [ ] **Test full signup flow on production** — sardis.sh → signup → API key → dashboard → first simulated payment
- [ ] **Test billing upgrade flow** — Free → Starter via Stripe Checkout → verify plan change in DB
- [ ] **Test password reset flow** — Forgot password → email → reset → login with new password
- [ ] **Test account deletion flow** — DELETE /auth/account → verify cascade deletion
- [ ] **Verify fee collection** — Execute a real Base mainnet payment → check treasury address received fee

---

## MEDIUM PRIORITY — Within 30 Days

### Compliance & Security
- [ ] **Sign up for Vanta or Drata** — SOC 2 automation ($10K/yr). Start evidence collection.
- [ ] **Write formal security policies** — Using Vanta templates: Information Security, Acceptable Use, Data Classification, Access Control
- [ ] **Schedule penetration test** — External pentest, target Q2 2026. Budget: $5-15K.
- [ ] **Set up backup restore testing** — Document Neon PITR procedure, test quarterly
- [ ] **Define RTO/RPO targets** — Recommend: RTO 4 hours, RPO 1 hour

### Go-to-Market
- [ ] **Record demo video** — 2-3 min: signup → create agent → set policy → payment → audit trail
- [ ] **Product Hunt launch prep** — Maker profile, screenshots, tagline, schedule launch day
- [ ] **Publish first 3 blog posts:**
  1. "Why AI Agents Need Spending Policies"
  2. "How to Add Payments to Your LangChain Agent in 5 Minutes"
  3. "Sardis vs. Hardcoding API Keys: A Security Comparison"
- [ ] **Submit to framework marketplaces** — LangChain Hub, CrewAI tools, Composio directory, AutoGPT plugins

### Product Improvements (Post-Launch Code Work)
- [ ] **Implement SSO/SAML** — Required for enterprise sales (python-saml or OneLogin)
- [ ] **Add team member invite + role management** — Multi-user enterprise access
- [ ] **Add RPC failover** — Secondary RPC endpoint per chain for reliability
- [ ] **Set up log aggregation** — Cloud Logging with 30-day retention
- [ ] **Add canary deployments** — Route 10% traffic to new revision, auto-rollback on errors

---

## LONGER TERM — Within 60-90 Days

### Enterprise Readiness
- [ ] **SOC 2 Type II observation period begins** — 3-month window
- [ ] **Implement SCIM provisioning** — For large org directory sync
- [ ] **Add automated secret rotation** — JWT key, API keys, DB credentials
- [ ] **Create operational runbooks** — On-call escalation, high-load mitigation
- [ ] **Distribute background job scheduler** — DB-backed locks for multi-instance cron

### Fundraising
- [ ] **Pitch deck finalized** — 13 slides per the fundraising analysis
- [ ] **Data room on Docsend** — Corporate docs, financial model, traction metrics, security overview
- [ ] **Financial model** — 24-month projection in Google Sheets
- [ ] **Begin investor outreach** — Warm intros via advisors to Tier 1 funds

---

## REFERENCE: Key Env Vars Needed

```bash
# Auth
JWT_SECRET_KEY=<generate-with-secrets.token_hex(32)>
SARDIS_ENVIRONMENT=production

# Billing
SARDIS_BILLING_BILLING_ENABLED=true
SARDIS_BILLING_STRIPE_SECRET_KEY=<from-stripe>
SARDIS_BILLING_STRIPE_WEBHOOK_SECRET=<from-stripe>
SARDIS_BILLING_STRIPE_PRICE_STARTER=<price_id>
SARDIS_BILLING_STRIPE_PRICE_GROWTH=<price_id>

# Fees
SARDIS_PLATFORM_FEE_BPS=50
SARDIS_TREASURY_ADDRESS=<your-base-mainnet-wallet>
SARDIS_FEE_MIN_AMOUNT=1.00

# Email (for password reset)
SMTP_HOST=<smtp-provider>
SMTP_PORT=587
SMTP_USER=<smtp-user>
SMTP_PASSWORD=<smtp-password>
SMTP_FROM_EMAIL=noreply@sardis.sh

# Analytics
POSTHOG_API_KEY=<from-posthog>

# Signup (set this LAST)
SARDIS_ALLOW_PUBLIC_SIGNUP=true
```

---

*This checklist was generated from the comprehensive go-live audit and 34 code commits across 3 development sessions. All code work referenced above is complete and pushed to `main`.*

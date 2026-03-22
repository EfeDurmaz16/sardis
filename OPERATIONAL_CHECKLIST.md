# Sardis Production Operational Checklist

> Updated: 2026-03-23 | Owner: Efe Baran Durmaz | Status: **LIVE**

## What's Done (No Action Needed)

- [x] Next.js 14 Dashboard deployed (sardis.sh / app.sardis.sh / dashboard.sardis.sh)
- [x] FastAPI Backend on Cloud Run (api.sardis.sh, 7/7 health checks)
- [x] 77 DB migrations applied to Neon PostgreSQL
- [x] Public signup enabled, sk_test_ keys generated
- [x] Didit KYC provider wired (API key + webhook secret on Cloud Run)
- [x] PostHog analytics key set on Vercel
- [x] better-auth configured with Neon PostgreSQL (ba_ prefixed tables)
- [x] JWKS dual validation on FastAPI (HS256 + EdDSA)
- [x] Monokrom grayscale theme applied
- [x] Driver.js product tour (6 steps)
- [x] All 4 domains consolidated to single Next.js app
- [x] Sidebar reorganized (Core/Policies/Security/Settings)
- [x] Mock data removed from all pages
- [x] Login persistence (localStorage + 7-day cookie)

---

## What YOU Need To Do

### 1. Resend Email Setup (15 min)

```
1. Go to resend.com → Sign up
2. Domains → Add sardis.sh
3. Add DNS records Resend provides:
   - SPF: TXT → v=spf1 include:resend.dev ~all
   - DKIM: TXT → (Resend provides value)
   - DMARC: TXT → v=DMARC1; p=none;
4. Wait for verification (1-5 min)
5. API Keys → Create → Copy key
6. Run:
   gcloud run services update sardis-api-staging --region us-east1 --update-env-vars \
     "SMTP_HOST=smtp.resend.com,SMTP_PORT=465,SMTP_USER=resend,SMTP_PASSWORD=re_YOUR_KEY,SMTP_FROM_EMAIL=noreply@sardis.sh"
   gcloud run services update sardis-api-staging --region europe-west1 --update-env-vars \
     "SMTP_HOST=smtp.resend.com,SMTP_PORT=465,SMTP_USER=resend,SMTP_PASSWORD=re_YOUR_KEY,SMTP_FROM_EMAIL=noreply@sardis.sh"
7. Test: app.sardis.sh/forgot-password → enter email → check inbox
```

### 2. Didit Webhook URL (2 min)

```
1. didit.me → Console → API & Webhooks
2. Set webhook URL: https://api.sardis.sh/api/v2/kyc/webhook
3. Done — secret already set on Cloud Run
```

### 3. Polar.sh Billing (10 min)

```
1. polar.sh → Create org "sardislabs"
2. Create products:
   - Starter: $49/month
   - Growth: $249/month
3. URLs already in billing page:
   - polar.sh/sardislabs/subscribe?tier=starter
   - polar.sh/sardislabs/subscribe?tier=growth
```

### 4. Google OAuth (Optional, 10 min)

```
1. Google Cloud Console → Credentials → Create OAuth Client
2. Redirect URI: https://sardis.sh/api/auth/callback/google
3. Set on Vercel:
   echo "CLIENT_ID" | vercel env add GOOGLE_CLIENT_ID production --cwd dashboard-next
   echo "SECRET" | vercel env add GOOGLE_CLIENT_SECRET production --cwd dashboard-next
4. Redeploy: cd dashboard-next && vercel --prod --yes
```

---

## YC Review Credentials

```
Dashboard:  https://app.sardis.sh/login
Email:      yc-review@sardis.sh
Password:   SardisYC2026!
API Key:    (see conversation history or create new via dashboard)
```

---

## Architecture

```
sardis.sh ──────────┐
www.sardis.sh ──────┤
app.sardis.sh ──────┼──→ Vercel (Next.js 14)
dashboard.sardis.sh ┘      / = landing, /login = auth, /overview = dashboard

api.sardis.sh ──────────→ Cloud Run (FastAPI, 47+ routers)
```

## Monitoring

| Service | URL |
|---------|-----|
| Health | `curl https://api.sardis.sh/health` |
| PostHog | us.posthog.com (project 352257) |
| Logs | `gcloud logging read "resource.labels.service_name=sardis-api-staging" --limit=20` |
| DB | console.neon.tech |
| KYC | didit.me dashboard |
| Deploys | `vercel ls --cwd dashboard-next` |

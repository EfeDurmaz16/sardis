# Dual-Track Deployment: Staging (Public) + Production (Design Partners)

**Strategy:** Public sandbox for developers to explore. Private production for vetted design partners with real money.

---

## Track 1: Staging (Public Sandbox)

**Who:** Anyone who visits sardis.sh and signs up.
**What:** Testnet environment, no real money, free tier only.

### Cloud Run Env Vars (sardis-api-staging)
```bash
gcloud run services update sardis-api-staging --update-env-vars \
  SARDIS_ENVIRONMENT=staging,\
  SARDIS_ALLOW_PUBLIC_SIGNUP=true,\
  SARDIS_CHECKOUT_CHAIN=base_sepolia,\
  SARDIS_BILLING_BILLING_ENABLED=false
```

### What Users Get
- `sk_test_` API keys on signup
- Sandbox wallets on Base Sepolia
- Full API access (simulation + testnet)
- Dashboard, docs, playground, MCP server
- No real money moves, no billing
- Testnet faucet for USDC

### What You Do
- Nothing. Fully self-serve. Monitor signups passively.

---

## Track 2: Production (Design Partners Only)

**Who:** 3-5 vetted design partners with signed LOIs.
**What:** Mainnet environment, real USDC, real fees.

### Cloud Run Env Vars (sardis-api — separate service or same with feature flag)
```bash
# Option A: Same service, partner accounts created manually in prod DB
# Option B: Separate Cloud Run service for production

# Required env vars for production:
SARDIS_ENVIRONMENT=production
SARDIS_ALLOW_PUBLIC_SIGNUP=false          # Partners onboarded manually
SARDIS_CHECKOUT_CHAIN=base
JWT_SECRET_KEY=<generate-unique-for-prod>
SARDIS_PLATFORM_FEE_BPS=50
SARDIS_TREASURY_ADDRESS=<your-base-mainnet-wallet>
SARDIS_FEE_MIN_AMOUNT=1.00
SARDIS_BILLING_BILLING_ENABLED=true
SARDIS_BILLING_PROVIDER=polar             # Or stripe after incorporation
```

### Design Partner Onboarding Runbook

**Step 1: Sign LOI** (before any technical work)
- Use the LOI template from `docs/sales/outreach-emails-top5.md`
- Get: signed LOI, logo permission, integration commitment
- Give: 6 months free Growth tier, priority support, co-marketing

**Step 2: Create Account** (manual — ~5 minutes)
```sql
-- Connect to production Neon DB
-- Create user
INSERT INTO users (id, email, password_hash, display_name, email_verified, created_at, updated_at)
VALUES (
  'usr_' || substr(md5(random()::text), 1, 16),
  'partner@company.com',
  '<argon2-hash-of-temp-password>',
  'Partner Name',
  TRUE,
  now(),
  now()
);

-- Create org
INSERT INTO user_org_memberships (user_id, org_id, role, created_at)
VALUES ('<user_id>', 'org_' || substr(md5(random()::text), 1, 16), 'owner', now());

-- Create API key (you'll generate this programmatically)
-- Use the auth service: POST /api/v2/auth/register with their email
-- Or use the CLI: sardis admin create-user --email partner@company.com
```

**Simpler approach:** Temporarily set `SARDIS_ALLOW_PUBLIC_SIGNUP=true` on production, have the partner register normally, then set it back to `false`. This gives them a proper account + API key through the normal flow.

**Step 3: Create Spending Mandate**
```bash
curl -X POST https://api.sardis.sh/api/v2/spending-mandates \
  -H "Authorization: Bearer <partner-api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "purpose_scope": "Design partner pilot — <company> integration",
    "amount_per_tx": 500,
    "amount_monthly": 5000,
    "amount_total": 25000,
    "approval_mode": "threshold",
    "approval_threshold": 1000,
    "allowed_rails": ["card", "usdc", "bank"]
  }'
```

**Step 4: Set Plan to Growth (comped)**
```sql
INSERT INTO billing_subscriptions (org_id, plan, status, created_at, updated_at)
VALUES ('<org_id>', 'growth', 'active', now(), now())
ON CONFLICT (org_id) DO UPDATE SET plan = 'growth', status = 'active', updated_at = now();
```

**Step 5: Share with Partner**
- Their API key (shown once at registration)
- Dashboard URL: dashboard.sardis.sh
- Quickstart: sardis.sh/docs/get-api-key
- Direct support channel: Telegram or Slack DM with you

**Step 6: Monitor**
- Check their transaction volume weekly
- Review policy violations and mandate usage
- Collect feedback every 2 weeks (15-min call or async)

---

## Design Partner Terms

| Benefit | Details | Duration |
|---------|---------|----------|
| Free usage | Growth tier ($249/mo value) | 6 months |
| Priority support | Direct channel with founder | Duration of pilot |
| Co-marketing | Joint blog post / case study | After first month |
| Custom features | Priority on feature requests | Duration of pilot |
| Transaction fees | 0% during pilot (waive platform fee) | 3 months, then 0.75% |

### What You Ask in Return
- Signed LOI (non-binding letter of interest)
- Permission to use their logo as "design partner"
- Monthly feedback call (15 min)
- Integration within 30 days of onboarding
- Reference call for 1 investor if asked

---

## Pricing Strategy

| Tier | Audience | Price | Billing | Status |
|------|----------|-------|---------|--------|
| Free | Public sandbox | $0 | None | Live on staging |
| Starter | Self-serve post-GA | $49/mo | Polar.sh | After GA |
| Growth | Design partners | $0 comped | Manual DB entry | Now |
| Enterprise | Future | Custom | Direct invoice | Later |

### When to Start Charging
- Design partners: after 6-month pilot ends
- Self-serve: after 3+ partners are active and product is stable
- Transaction fees: after 3-month grace period for partners

---

## Transition to GA

When you're ready for general availability:

1. Merge staging and production into one service
2. Set `SARDIS_ALLOW_PUBLIC_SIGNUP=true` on production
3. Enable Polar.sh billing for self-serve tiers
4. Keep design partners on comped Growth tier
5. Announce on Product Hunt, Twitter, Discord
6. Start collecting transaction fees (0.75% Growth tier)

**GA criteria:**
- [ ] 3+ design partners actively transacting
- [ ] 0 critical bugs in 2 weeks
- [ ] Password reset emails working
- [ ] Billing (Polar.sh or Stripe) collecting payments
- [ ] At least 1 case study / testimonial

---

## Capital Strategy Note

Pre-PMF round (HustleFund $150K + angels, or Gate.io $500K):
- Use to fund: incorporation, infrastructure, first hire
- Timeline: close within 30 days of first LOI
- Narrative: "3 design partners signed, first revenue imminent, need capital to serve demand"
- After PMF: seed/Series A with paying customers and metrics

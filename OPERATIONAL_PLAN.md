# Sardis Operational Plan

**Created:** January 25, 2026
**Owner:** Efe Baran Durmaz

This document outlines the operational tasks that require manual execution. Tasks are prioritized by urgency and impact.

---

## 🔴 P0: THIS WEEK (Critical Blockers)

### 1. Publish Python SDK to PyPI
**Time:** 1-2 hours
**Prerequisites:** PyPI account, API token

```bash
# Steps:
cd packages/sardis-sdk-python

# 1. Create PyPI account at https://pypi.org/account/register/
# 2. Generate API token at https://pypi.org/manage/account/token/
# 3. Configure credentials
pip install twine build
python -m build

# 4. Upload to PyPI
twine upload dist/*
```

**Verification:** `pip install sardis-sdk` should work

---

### 2. Publish TypeScript SDK to npm
**Time:** 1-2 hours
**Prerequisites:** npm account

```bash
# Steps:
cd packages/sardis-sdk-ts

# 1. Create npm account at https://www.npmjs.com/signup
# 2. Login: npm login
# 3. Build and publish
npm run build
npm publish --access public
```

**Verification:** `npm install @sardis/sdk` should work

---

### 3. Create 1-Minute Demo Video
**Time:** 2-4 hours
**Prerequisites:** Screen recorder, Remotion setup (provided)

**Option A: Use Remotion (Recommended)**
```bash
cd demo-video
npm install
npm start  # Opens Remotion Studio
# Preview and render
npm run build  # Outputs to out/sardis-demo.mp4
```

**Option B: Screen Record**
1. Open Claude Desktop with Sardis MCP configured
2. Record yourself demonstrating a payment flow
3. Keep under 60 seconds
4. Upload to YouTube as "Unlisted"

**Content:** Follow `demo-video/VIDEO_PLAN.md`

---

### 4. Set Up Basic Analytics
**Time:** 2-4 hours

**Option A: PostHog (Recommended - Free)**
1. Sign up at https://posthog.com
2. Get API key from Project Settings
3. Set environment variable: `POSTHOG_API_KEY=phk_...`

**Option B: Self-Hosted Redis**
1. Deploy Redis instance (Upstash, Railway, etc.)
2. Set environment variable: `REDIS_URL=redis://...`
3. Set: `ANALYTICS_BACKEND=redis`

The analytics module is already implemented at `packages/sardis-core/src/sardis_v2_core/analytics.py`

---

### 5. Test Base Mainnet Deployment
**Time:** 4-8 hours
**Prerequisites:** Base mainnet ETH for gas (~$20), Private key

```bash
# Steps:
cd contracts

# 1. Get Base mainnet ETH
# - Bridge from Ethereum via https://bridge.base.org
# - Or buy on exchange and withdraw to Base

# 2. Set environment variables
export PRIVATE_KEY="your_deployer_private_key"
export BASE_RPC_URL="https://mainnet.base.org"

# 3. Deploy with small test (use minimal gas)
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
  --rpc-url $BASE_RPC_URL \
  --broadcast \
  --verify

# 4. Test with $1 transaction before announcing
```

**⚠️ START SMALL:** Deploy and test with $1-10 before full production

---

## 🟡 P1: NEXT 2 WEEKS (Critical Path)

### 6. Engage Security Audit Firm
**Time:** 1-2 weeks for engagement
**Budget:** $50,000 - $150,000

**Recommended Firms:**
1. **Trail of Bits** - https://www.trailofbits.com
2. **OpenZeppelin** - https://www.openzeppelin.com/security-audits
3. **Consensys Diligence** - https://consensys.io/diligence
4. **Halborn** - https://halborn.com (faster, lower cost)

**Scope:**
- Smart contracts (Solidity)
- Backend API (Python/FastAPI)
- MPC integration review
- Policy engine logic

**Action Items:**
1. Request quotes from 2-3 firms
2. Provide codebase access
3. Define scope and timeline
4. Sign engagement letter

---

### 7. Set Up Production Monitoring
**Time:** 4-8 hours

**Recommended Stack:**
1. **Sentry** (Error Tracking) - https://sentry.io
   - Add to Python: `pip install sentry-sdk`
   - Add to TypeScript: `npm install @sentry/node`

2. **DataDog** or **Grafana Cloud** (APM)
   - Metrics, traces, logs
   - Alert on error rates, latency

3. **PagerDuty** (Alerts)
   - Critical alerts → phone call
   - Warning alerts → Slack

**Environment Variables:**
```bash
SENTRY_DSN=https://xxx@sentry.io/xxx
DATADOG_API_KEY=xxx
```

---

### 8. Create Pitch Deck
**Time:** 4-8 hours
**Format:** 13-14 slides

**Slide Structure:**
1. Title + Tagline
2. Problem: Financial Hallucination
3. Solution: Sardis Payment OS
4. Demo/Screenshots
5. How It Works
6. Market Size ($30T by 2035)
7. Business Model (0.2% transaction fee)
8. Traction (stats from dashboard)
9. Competition + Differentiation
10. Go-To-Market (MCP → SDK → Enterprise)
11. Team (Founder background)
12. Financials (projections)
13. Ask ($2M seed)
14. Appendix

**Tools:** Figma, Google Slides, or Pitch.com

---

### 9. Prepare Market Research
**Time:** 2-4 hours

**TAM/SAM/SOM:**
- **TAM:** $30 trillion (AI agent spending by 2035 - Gartner)
- **SAM:** $100 billion (Developer-controlled agent transactions)
- **SOM:** $1 billion (First 3 years, 1% of SAM)

**Sources:**
- Gartner AI predictions
- McKinsey autonomous agent reports
- Stripe/Adyen market sizing

---

### 10. Collect User Testimonials
**Time:** 1-2 weeks
**Goal:** 3-5 testimonials

**Target Users:**
- MCP server early adopters
- AI agent developers
- Crypto payment users

**Ask:**
- 2-3 sentences about their experience
- Permission to use name/company
- Optional: short video testimonial

**Outreach Template:**
```
Subject: Quick favor - Sardis testimonial?

Hi [Name],

I noticed you've been using Sardis MCP for [use case]. Would you mind sharing a quick 2-3 sentence testimonial about your experience?

Happy to return the favor in any way I can.

Thanks!
Efe
```

---

## 🟢 P2: NEXT MONTH (Important)

### 11. Secure Pilot Customers (3+)
**Time:** 2-4 weeks
**Goal:** 3 LOIs or active pilots

**Target Segments:**
1. AI agent startups (LangChain users, CrewAI users)
2. Crypto-native companies needing agent payments
3. Enterprise innovation teams

**Outreach Channels:**
- Twitter/X DMs to AI founders
- LinkedIn outreach
- YC founder network
- Discord communities (LangChain, CrewAI)

---

### 12. Prepare Due Diligence Materials
**Time:** 1-2 weeks

**Checklist:**
- [ ] Cap table (spreadsheet)
- [ ] Incorporation documents (Delaware C-Corp recommended)
- [ ] IP assignment agreements
- [ ] Any existing contracts
- [ ] Bank statements
- [ ] Financial projections (3-year model)

**Legal:** Consider using Clerky or Stripe Atlas for incorporation

---

### 13. Secure Legal Opinion
**Time:** 2-4 weeks
**Budget:** $10,000 - $30,000

**Purpose:** Confirm non-custodial status for regulatory clarity

**Recommended Firms:**
1. **Anderson Kill** (Crypto specialty)
2. **Fenwick & West** (Startup + Crypto)
3. **Cooley** (YC-friendly)

**Request:** Written opinion on:
- Non-custodial architecture compliance
- Money transmission licensing requirements
- State-by-state analysis (if needed)

---

### 14. Build Partnership Pipeline
**Time:** Ongoing

**Priority Partnerships:**
1. **LangChain** - Integration showcase
2. **CrewAI** - Multi-agent framework
3. **Anthropic** - MCP featured integration
4. **OpenAI** - Function calling showcase
5. **Vercel** - AI SDK integration

**Approach:**
- DevRel outreach
- Integration documentation
- Co-marketing opportunities

---

## 📊 Metrics to Track

| Metric | Target (Month 1) | Target (Month 3) |
|--------|------------------|------------------|
| Wallets Created | 100 | 1,000 |
| Transaction Volume | $10,000 | $100,000 |
| SDK Downloads | 500 | 5,000 |
| MCP Installations | 50 | 500 |
| Active Developers | 10 | 100 |
| GitHub Stars | 100 | 500 |

---

## 💰 Budget Summary

| Category | Amount | Notes |
|----------|--------|-------|
| Security Audit | $50k-150k | One-time |
| Legal/Compliance | $20k-50k | One-time |
| Infrastructure | $2k/mo | Cloud + Services |
| Third-Party APIs | $5k/mo | Turnkey, Lithic, etc. |
| Marketing | $5k/mo | Content, events |
| **Total (3 months)** | **$100k-250k** | Before fundraise |

---

## 📞 Key Contacts

| Service | Contact | Purpose |
|---------|---------|---------|
| Turnkey | sales@turnkey.com | Production keys |
| Lithic | partnerships@lithic.com | Card program |
| Bridge | developers@bridge.xyz | Fiat rails |
| Persona | sales@withpersona.com | KYC |
| Elliptic | contact@elliptic.co | AML |

---

## ✅ Completion Checklist

**P0 (This Week):**
- [ ] Python SDK published to PyPI
- [ ] TypeScript SDK published to npm
- [ ] Demo video created and uploaded
- [ ] Analytics configured
- [ ] Base mainnet test deployment

**P1 (2 Weeks):**
- [ ] Security audit engaged
- [ ] Monitoring set up
- [ ] Pitch deck complete
- [ ] Market research documented
- [ ] First testimonials collected

**P2 (1 Month):**
- [ ] 3+ pilot customers signed
- [ ] DD materials ready
- [ ] Legal opinion obtained
- [ ] Partnership discussions started

---

*Last Updated: January 25, 2026*

# Metrics Dashboard Spec

Updated: 2026-03-24

## Dashboard Structure: 3 Tabs

### Tab 1: Overview (Executive Summary)

| Metric | Source | Refresh | Display |
|--------|--------|---------|---------|
| Total signups (cumulative) | PostgreSQL: users table | Real-time | Counter + daily sparkline |
| Active users (7d) | PostgreSQL: API key last-used | Daily | Counter + trend |
| Total payments processed | PostgreSQL: payments table | Real-time | Counter + daily chart |
| Total volume (USD) | PostgreSQL: payments.amount | Real-time | Counter |
| MRR | Polar.sh / Stripe API | Daily | Counter + growth % |
| SDK installs (cumulative) | PyPI + npm API | Daily | Counter (currently 50K) |
| Conversion: signup -> first payment | Computed | Daily | Percentage + trend |
| API uptime (30d) | Health check | 5-min | Percentage |

### Tab 2: Wedge Metrics

#### Wedge A: Secure AI Payments

| Metric | Target (30d) | Target (90d) |
|--------|-------------|-------------|
| Signups mentioning "policy" or "mandate" | 20 | 100 |
| Mandates created | 50 | 500 |
| Policy-blocked payments | 100 | 1,000 |
| Paying customers on Growth+ tier | 1 | 10 |
| MRR from Wedge A | $199 | $2,000 |
| NPS from Wedge A customers | > 40 | > 50 |

#### Wedge B: Automated API Payments

| Metric | Target (30d) | Target (90d) |
|--------|-------------|-------------|
| x402-enabled API endpoints registered | 5 | 50 |
| MPP auto-payments processed | 100 | 5,000 |
| Unique agents paying via x402 | 10 | 200 |
| API providers earning revenue | 2 | 20 |
| Transaction volume through x402 | $1,000 | $50,000 |
| Facilitator fee revenue (0.5%) | $5 | $250 |

#### Wedge C: US-EU Cross-Border

| Metric | Target (30d) | Target (90d) |
|--------|-------------|-------------|
| FX swaps executed | 10 | 200 |
| Cross-border volume (USD) | $5,000 | $200,000 |
| Unique treasuries using FX | 1 | 10 |
| Average swap size | $500 | $1,000 |
| FX fee revenue (5-15 bps) | $5 | $200 |

### Tab 3: Funnel

Visit sardis.sh (PostHog)
  -> Signup (5% target) (PostgreSQL)
  -> API Key Created (60% of signups) (PostgreSQL)
  -> First Mandate Created (40% of key holders) (PostgreSQL)
  -> First Payment (50% of mandate creators) (PostgreSQL)
  -> Second Payment / Activation (20% of first payers) (PostgreSQL)
  -> Paid Plan (10% of activated) (Polar.sh/Stripe)
  -> Retained Month 2+ (80% monthly) (Stripe)

#### Funnel Alerts

| Alert | Trigger | Action |
|-------|---------|--------|
| Signup spike | > 50 signups/day | Post on Twitter, send founder email |
| Activation drop | < 30% mandate creation rate | Review onboarding UX |
| Payment failure spike | > 10% failure rate | Page founder, check chain/RPC |
| Churn signal | No payment in 7 days | Re-engagement email |
| Revenue milestone | First paying customer | Celebrate publicly |

## Data Source Mapping

| Source | Connection | Metrics |
|--------|-----------|---------|
| PostgreSQL (Neon) | Direct query via API routes | Users, mandates, payments, agents |
| PostHog | JS snippet on sardis.sh + dashboard | Page views, funnels, feature usage |
| Polar.sh / Stripe | API polling (daily) | MRR, subscriptions, churn |
| PyPI API | Daily cron | Python SDK installs |
| npm API | Daily cron | TypeScript SDK installs |
| GitHub API | Daily cron | Stars, forks, issues |
| Uptime monitor | 5-min health check | API availability |

## Implementation Priority

1. Week 1: Overview tab (counters only, no charts) — 2h
2. Week 2: Funnel tab (PostHog events + Neon queries) — 3h
3. Week 3: Wedge tabs (per-wedge breakdowns) — 2h
4. Week 4: Alerts (email/Slack on thresholds) — 1h

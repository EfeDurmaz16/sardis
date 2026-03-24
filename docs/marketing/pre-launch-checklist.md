# Pre-Launch GTM Checklist

Updated: 2026-03-24 | Items ordered by dependency.

## Tier 1 — Blockers (cannot launch without these)

| # | Item | Status | Effort | Notes |
|---|------|--------|--------|-------|
| 1.1 | Mainnet contracts deployed (Base) | PENDING | 2h | SardisLedgerAnchor + RefundProtocol + ERC-8183. Needs deployer wallet with ~$2-5 ETH. |
| 1.2 | sardis.pay() Phase 1 on mainnet | PENDING | 3h | Single-chain, single-token, explicit config. Thin facade over PaymentOrchestrator. |
| 1.3 | One complete happy-path demo | PENDING | 2h | signup -> API key -> mandate -> sardis.pay() -> tx on Base mainnet -> receipt. Screen-recorded, under 3 min. |
| 1.4 | Pricing page on sardis.sh | PENDING | 2h | 5 tiers: Free / Developer $29 / Growth $199 / Business $499 / Enterprise. Link to billing. |
| 1.5 | Terms of Service + Privacy Policy | PENDING | 1h | Standard SaaS templates at sardis.sh/terms and sardis.sh/privacy. |
| 1.6 | Landing page hero updated | PENDING | 2h | Replace testnet messaging. Hero: "AI agents pay any API." + live trace visual. |
| 1.7 | Docs quickstart updated for mainnet | PENDING | 1h | sardis.sh/docs/quickstart must show mainnet flow, not testnet. |
| 1.8 | Waitlist -> signup conversion path | PENDING | 1h | Early-access email with signup link + API key for existing waitlist subscribers. |

## Tier 2 — Should-haves (launch is weaker without these)

| # | Item | Status | Effort | Notes |
|---|------|--------|--------|-------|
| 2.1 | sardis demo CLI | PENDING | 2h | One-command sandbox. Creates temp API key, deploys testnet wallet, 3 sample mandates. |
| 2.2 | 3 blog posts queued | PENDING | 3h | (1) Policy wallets (2) sardis.pay() tutorial (3) NLP mandates technical deep-dive |
| 2.3 | OG image + social cards | PENDING | 1h | 1200x630 OG image. Twitter card meta tags. |
| 2.4 | Product Hunt assets | PENDING | 2h | 5 gallery images, logo (240x240), GIF demo, maker profile. |
| 2.5 | Notification webhooks working | PENDING | 1h | payment.completed, payment.blocked events. Slack incoming webhook format. |
| 2.6 | Status page | PENDING | 30m | status.sardis.sh — API, dashboard, chain connectivity. |

## Tier 3 — Nice-to-haves (within 2 weeks post-launch)

| # | Item | Status | Effort | Notes |
|---|------|--------|--------|-------|
| 3.1 | API playground in dashboard | - | 2h | Interactive sardis.pay() tester with sandbox credentials. |
| 3.2 | Spend widget npm package | - | 2h | Embeddable React component showing agent spend + policy status. |
| 3.3 | Customer onboarding flow (6 screens) | - | 3h | Guided signup -> KYB -> terms -> API key -> mandate -> first payment. |
| 3.4 | Referral/invite system | - | 2h | "Invite a developer, both get 30 days Growth free." |

Total pre-launch effort: ~20 hours (Tier 1 + Tier 2).

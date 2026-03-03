# Jesse Pollak + Base Launch Plan

## Jesse Follow-Up Email (Send after Base mainnet deploy)

Jesse,

You asked how you can help. Three things:

1. **Grant signal.** We applied for a Builder Grant. Your nod would make a difference.
2. **One warm intro.** To whoever runs the AI agents vertical at Coinbase Ventures, or an investor you think fits.
3. **A cofounder lead.** I'm a solo founder, 5 months in, 25K downloads, Helicone (YC W23) as design partner. If you know a strong technical cofounder who's excited about agent payments infra, I'd love the connection.

We're live on Base with Circle Paymaster + CCTP V2. Integrating OnchainKit + Base Pay next so every AI agent becomes a Base customer.

cal.com/sardis/15min if you have 15 min.

Efe

## Timing
- Send on Tuesday morning PST 8-9am (Istanbul 19:00)
- Must deploy to Base mainnet FIRST so "live on Base" is true

## Base Grant Application

### Form Fields
- Project Name: Sardis
- Project URL: sardis.sh
- Live on Base? Yes - live on Base mainnet (after deploy)

### Why Grant (150 words)
Sardis is the payment infrastructure layer for AI agents on Base. We give autonomous agents non-custodial MPC wallets with natural language spending policies, so they can transact in USDC safely and compliantly. 25,000+ SDK downloads, 9 framework integrations, and Helicone (YC W23) is lined up as a design partner.

We bring more users onchain by enabling every AI agent to become an economic actor on Base. Each Sardis-powered agent creates a Base wallet, generates USDC transaction volume, and pays gas through Circle Paymaster. As the agent economy scales, so does Base usage.

Our integration is deep: Circle Paymaster for gasless USDC, CCTP V2 for cross-chain inflows, Safe Smart Accounts, and EAS attestations. We plan to integrate OnchainKit, Base Account, and Base Pay so agents can pay at any Shopify merchant through Base.

Solo founder, 5 months, zero marketing. Everything is open and verifiable.

### 1-min Demo Video Content
1. pip install sardis (5s)
2. 5 lines of code: wallet + policy (15s)
3. USDC payment on Base (15s)
4. Dashboard transaction view (10s)
5. MCP server: "pay $5 to vendor.eth on Base" (15s)

## Jesse Meeting Agenda (15 min)

| Min | Topic |
|-----|-------|
| 0-2 | Intro: "Sardis = policy firewall for agent payments on Base" |
| 2-5 | Live demo: 5 lines, Base USDC payment, policy reject |
| 5-8 | OnchainKit + Base Account + Base Pay integration plan |
| 8-10 | Traction: 25K downloads, Helicone, zero marketing |
| 10-13 | Ask: Grant signal, Coinbase Ventures intro, cofounder lead |
| 13-15 | Next steps |

## Other Investor Emails
See: docs/marketing/investor-outreach-emails.md
- QuantumLight Capital (info@quantumlightcapital.com)
- Elephant VC (jason@elephantvc.com)
- Spark Capital (contactus@sparkcapital.com)

## Base Mainnet Deploy Steps
1. forge script contracts deploy to Base mainnet (~0.01 ETH gas)
2. Set SARDIS_CHAIN_MODE=live
3. Configure SARDIS_BASE_RPC_URL (Alchemy)
4. E2E test on mainnet
5. Update contract addresses in config

## Technical Integrations Planned
1. OnchainKit - SDK components
2. Base Account - passkey auth for operators
3. Base Pay - agent payments at Shopify merchants
4. Mini App - Sardis dashboard in Base App

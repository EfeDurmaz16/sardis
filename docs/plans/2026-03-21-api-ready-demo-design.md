# Sardis API-Ready Demo Platform — Design Document

**Date:** 2026-03-21
**Deadline:** 2026-03-27 (Thursday)
**Author:** Efe + Claude

## Goal

Make Sardis fully demo-ready: a person signs up, gets an API key, creates a wallet, funds it, sets a spending mandate, and executes payments — all through the API. Dashboard visualizes everything in real-time.

## Architecture

### Dual Environment (API Key Routing)

| Key Prefix | Environment | Chain | Use Case |
|------------|-------------|-------|----------|
| `sk_test_` | Testnet | Base Sepolia (84532) | Anyone who signs up |
| `sk_live_` | Mainnet | Tempo (4217) | Pilot partners, admin-assigned |

**Routing:** Middleware reads API key prefix → sets `chain` context for the request. DB `api_keys` table gets `environment` field (`test` or `live`).

### Signup Flow

1. `POST /api/v2/auth/signup` → creates user + org
2. Auto-generates `sk_test_...` API key
3. Auto-creates Base Sepolia wallet via Turnkey MPC
4. Returns `{ api_key, wallet_id, wallet_address, next_steps }`

### Partner Onboarding

Admin endpoint: `POST /api/v2/admin/promote-to-live`
- Creates `sk_live_...` key for the org
- Creates Tempo mainnet wallet
- Only accessible with admin credentials

## API Endpoints (New/Modified)

### 1. Signup Enhancement
**Modify:** `POST /api/v2/auth/signup`
- Auto-create `sk_test_` API key
- Auto-create Base Sepolia wallet (Turnkey MPC)
- Add `next_steps` to response

### 2. Faucet
**New:** `POST /api/v2/faucet/drip`
- Test environment only (`sk_test_` keys)
- Transfers 100 test USDC to caller's wallet
- Rate limit: 1x per day per org
- Sources from pre-funded faucet wallet (Circle faucet → our hot wallet → user)

### 3. Chain Routing Middleware
**New middleware** in auth pipeline:
- `sk_test_` → `request.state.chain = "base_sepolia"`
- `sk_live_` → `request.state.chain = "tempo"`
- Endpoints use `request.state.chain` as default

### 4. Dashboard Metrics
**New:** `GET /api/v2/dashboard/metrics`
- Returns: balance, 24h volume, tx count, agent count, policy pass rate, active sessions
- Single call for overview page

### 5. SSE Event Stream
**New:** `GET /api/v2/events/stream`
- Server-Sent Events for real-time updates
- Events: payment.completed, payment.blocked, session.created, session.closed, mandate.created
- Filtered by org_id (auth required)

### 6. Admin Promote
**New:** `POST /api/v2/admin/promote-to-live`
- Admin-only endpoint
- Creates `sk_live_` key + Tempo wallet for target org

### 7. next_steps in Responses
**Modify:** All major POST endpoints
- Signup → "Fund wallet via faucet" / "Create spending mandate"
- Faucet drip → "Create spending mandate" / "Create agent"
- Create mandate → "Create agent" / "Create MPP session"
- Create agent → "Create MPP session" / "Execute payment"
- Create session → "Execute payment"
- Execute payment → "Check audit trail" / "Close session"

### 8. Environment Badge
**New:** `GET /api/v2/environment`
- Returns current environment info for the API key
- `{ environment: "test", chain: "base_sepolia", chain_id: 84532 }`

## Dashboard Changes

### Design System Overhaul
- **Colors:** Zinc monochrome palette (from design-system-preview.html)
- **Typography:** Space Grotesk (headings/body) + JetBrains Mono (data/code)
- **Icons:** Phosphor Regular (replace Lucide)
- **Borders:** `rgba(255,255,255,0.06/0.08/0.12/0.20)`
- **Shadows:** Subtle, no gradients
- **Components:** Buttons, badges, cards, tables per design system

### Pages to Wire

| Page | API Endpoint | Priority |
|------|-------------|----------|
| Overview (Dashboard.tsx) | `GET /dashboard/metrics` | P1 |
| Transactions | `GET /ledger/entries` | P1 |
| Wallets | `GET /wallets` + `GET /wallets/{id}/balance` | P1 |
| Agents | `GET /agents` | P2 |
| Mandates | `GET /spending-mandates` | P2 |
| LiveEvents | `GET /events/stream` (SSE) | P2 |
| MPP Sessions (new) | `GET /mpp/sessions` | P2 |
| API Keys | `GET /api-keys` | P3 |
| Settings | existing | P3 |

### New UI Elements
- **Environment badge** in header: "TESTNET" (amber) or "MAINNET" (green)
- **Faucet button** in wallet page (testnet only): "Get 100 test USDC"
- **Onboarding checklist** for first-time users (dismiss-able)

## Environment Setup

### Required Env Vars (API)
```bash
# Database
DATABASE_URL=postgresql://...

# Auth
JWT_SECRET_KEY=<random-hex-64>

# MPC Wallet (Turnkey)
TURNKEY_ORGANIZATION_ID=...
TURNKEY_API_PUBLIC_KEY=...
TURNKEY_API_PRIVATE_KEY=...

# Chain
SARDIS_CHAIN_MODE=live
SARDIS_DEFAULT_CHAIN=base_sepolia
SARDIS_BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/KEY

# Faucet
SARDIS_FAUCET_PRIVATE_KEY=<faucet-wallet-private-key>
SARDIS_FAUCET_DAILY_LIMIT=100
```

### Required Env Vars (Dashboard)
```bash
VITE_API_URL=https://api.sardis.sh
VITE_CHAIN=base_sepolia
```

### Testnet Setup Steps
1. Alchemy API key (free tier)
2. Turnkey org + API key + wallet
3. Fund faucet wallet: Base Sepolia ETH (Alchemy faucet) + USDC (Circle faucet)
4. Deploy API to Cloud Run
5. Deploy dashboard to Vercel

## Token Addresses

| Chain | Token | Address |
|-------|-------|---------|
| Base Sepolia | USDC | `0x036CbD53842c5426634e7929541eC2318f3dCF7e` |
| Base Sepolia | ETH (gas) | native |
| Tempo Mainnet | USDC.e | `0x20C000000000000000000000b9537d11c60E8b50` |
| Tempo Mainnet | pathUSD | `0x20c0000000000000000000000000000000000000` |

## Safe Infrastructure (Pre-deployed)

| Contract | Address (all EVM chains) |
|----------|------------------------|
| SafeProxyFactory | `0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2` |
| Safe Singleton v1.4.1 | `0x41675C099F32341bf84BFc5382aF534df5C7461a` |
| Safe4337Module | `0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226` |
| EntryPoint v0.7 | `0x0000000071727De22E5E9d8BAf0edAc6f37da032` |
| Zodiac Roles | `0x9646fDAD06d3e24444381f44362a3B0eB343D337` |

## Success Criteria

1. A new user can signup and get `sk_test_` key in one call
2. User can fund wallet via faucet in one call
3. User can create mandate → agent → session → payment in 4 calls
4. Blocked payment returns clear policy violation message
5. Dashboard shows real-time metrics and transaction feed
6. Pilot partner on Tempo mainnet can execute real USDC payment
7. Full audit trail with merkle proofs visible in dashboard

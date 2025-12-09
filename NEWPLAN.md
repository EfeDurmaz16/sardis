

# Sardis Project — Comprehensive Technical Analysis

## Executive Summary

Sardis is an **agent-first stablecoin payment rail** designed to enable AI agents to execute programmable payments using stablecoins (USDC, USDT, PYUSD, EURC) across multiple chains (Base, Ethereum, Polygon, Solana). The project implements the **AP2 (Agent Payment Protocol)** and **TAP (Trust Anchor Protocol)** standards for mandate-based, cryptographically-signed payment flows.

---

# 1. Project Understanding

## 1.1 What Sardis Currently Does

Sardis provides:

1. **Mandate-Based Payment Execution** — AP2 protocol implementation where payments flow through Intent → Cart → Payment mandate chains, each cryptographically signed
2. **Agent Wallet Management** — Multi-token wallets with programmable spending limits (per-tx, daily, weekly, monthly, total)
3. **Policy Enforcement** — Merchant allowlists/denylists, category-based rules, trust levels
4. **Compliance Engine** — Token allowlisting, amount limits, GENIUS Act-aligned hooks
5. **Ledger System** — Append-only transaction records with audit anchors and Merkle proofs
6. **Multi-Chain Routing** — Support for Base, Ethereum, Polygon (Solana planned)
7. **SDKs** — Python and TypeScript clients for agent integration

## 1.2 Intended vs. Actual Architecture

### Intended Architecture (from README/docs)

```
TAP Identity Providers (Turnkey/Fireblocks MPC)
         ↓
AP2 Agents → sardis-protocol (Mandate verify) → sardis-wallet (policies)
         ↓
    sardis-api (FastAPI gateway)
         ↓
    sardis-chain (Tx executor & routing)
         ↓
    sardis-ledger + sardis-compliance
         ↓
    External monitors / issuers
```

### Actual Implemented Architecture

| Component | Status | Notes |
|-----------|--------|-------|
| [sardis-core](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-core:0:0-0:0) (V2) | ✅ Implemented | Clean domain models, spending policies, mandates |
| [sardis-api](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-api:0:0-0:0) (V2) | ✅ Implemented | FastAPI with AP2 endpoints |
| [sardis-protocol](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-protocol:0:0-0:0) | ✅ Implemented | Mandate verification, replay cache, archive |
| [sardis-wallet](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-wallet:0:0-0:0) | ⚠️ Partial | Policy validation exists, no MPC integration |
| [sardis-chain](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-chain:0:0-0:0) | ⚠️ Stub | Simulated execution only, no real chain calls |
| [sardis-ledger](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-ledger:0:0-0:0) | ✅ Implemented | SQLite-based, append-only |
| [sardis-compliance](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-compliance:0:0-0:0) | ⚠️ Basic | Simple rule provider, no external vendor hooks |
| [legacy/sardis_core](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/legacy/sardis_core:0:0-0:0) | ✅ Full | Complete V1 implementation with PostgreSQL |
| Smart Contracts | ✅ Written | Foundry-based, not deployed |
| Dashboard | ✅ Implemented | React + Vite + TailwindCSS |

## 1.3 Inconsistencies and Missing Pieces

### Critical Gaps

| Issue | Severity | Location |
|-------|----------|----------|
| **Simulated blockchain execution** | 🔴 Critical | `sardis-chain/executor.py` returns fake tx hashes |
| **No MPC wallet integration** | 🔴 Critical | Turnkey/Fireblocks not wired |
| **Dual codebase confusion** | 🟡 High | V1 ([legacy/sardis_core](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/legacy/sardis_core:0:0-0:0)) vs V2 (`sardis-*` packages) |
| **No conversation memory** | 🟡 High | AI agents are stateless |
| **Webhooks not delivering** | 🟡 High | Event system defined but not connected |
| **Auth not enforced everywhere** | 🟡 High | API keys exist but inconsistent enforcement |
| **SQLite in V2, PostgreSQL in V1** | 🟡 Medium | Data layer fragmentation |
| **Smart contracts not deployed** | 🟡 Medium | Foundry contracts exist but TBD addresses |

### Outdated/Dead Code

- [legacy/sardis_core/](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/legacy/sardis_core:0:0-0:0) contains 80+ files that duplicate V2 functionality
- [sardis_core/](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis_core:0:0-0:0) symlink at root creates import confusion
- Multiple [__pycache__](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/tests/__pycache__:0:0-0:0) directories indicate mixed Python environments

## 1.4 Core Concepts Summary

### Agent Wallets
```python
@dataclass/sardis_v2_core/wallets.py
class Wallet:
    wallet_id: str
    agent_id: str
    balance: Decimal
    token_balances: dict[str, TokenBalance]  # Multi-token
    limit_per_tx: Decimal
    limit_total: Decimal
    spent_total: Decimal
    virtual_card: Optional[VirtualCard]
```

### Spending Limits
```python
@dataclass/sardis_v2_core/spending_policy.py
class SpendingPolicy:
    trust_level: TrustLevel  # LOW/MEDIUM/HIGH/UNLIMITED
    limit_per_tx: Decimal
    daily_limit: TimeWindowLimit
    weekly_limit: TimeWindowLimit
    monthly_limit: TimeWindowLimit
    merchant_rules: list[MerchantRule]
    allowed_scopes: list[SpendingScope]  # RETAIL/DIGITAL/AGENT_TO_AGENT/etc.
```

### Preloaded Balances
- Wallets are funded from system treasury (`wallet_system_treasury`)
- Multi-token support via `token_balances` dict
- Balance checks occur before policy validation

### Stablecoin Rails
- Supported: USDC, USDT, PYUSD, EURC
- Chains: Base, Ethereum, Polygon (Solana planned)
- Settlement modes: `internal_ledger_only`, `chain_write_per_tx`, `batched_chain_settlement`

### Agent-to-Agent Transactions
- `SpendingScope.AGENT_TO_AGENT` scope
- Escrow contract ([SardisEscrow.sol](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/contracts/src/SardisEscrow.sol:0:0-0:0)) for trustless A2A
- Milestone-based payments with dispute resolution

### Programmable Rules
- [MerchantRule](cci:2://file:///Users/efebarandurmaz/Desktop/sardis/sardis-core/src/sardis_v2_core/spending_policy.py:67:0-91:20) with allow/deny types
- Category-based filtering
- Per-merchant transaction caps
- Expiring rules

### API Flows
1. **V2 AP2 Flow**: `POST /api/v2/ap2/payments/execute` with Intent+Cart+Payment bundle
2. **V2 Mandate Flow**: `POST /api/v2/mandates/execute` with single mandate
3. **V1 Legacy Flow**: `POST /api/v1/payments` with agent_id + amount

---

# 2. Deployment Feasibility on Vercel

## 2.1 Vercel Serverless Compatibility Analysis

| Aspect | Compatible | Blocker Details |
|--------|------------|-----------------|
| **FastAPI** | ✅ Yes | Works with `@vercel/python` runtime |
| **Request/Response** | ✅ Yes | Standard HTTP, no streaming |
| **SQLite** | ⚠️ Partial | Read-only in serverless; ephemeral writes |
| **PostgreSQL** | ✅ Yes | External DB (Neon, Supabase, RDS) |
| **Long-running processes** | ❌ No | 10s default, 60s max on Pro |
| **WebSockets** | ❌ No | Not supported |
| **Background jobs** | ❌ No | No cron/queue support |
| **Stateful logic** | ⚠️ Partial | In-memory caches reset per invocation |
| **Blockchain calls** | ⚠️ Risky | RPC calls may timeout |

## 2.2 Specific Blockers

### 1. Long-Running Blockchain Operations
```python
# sardis-chain/executor.py - Current stub
async def dispatch_payment(self, mandate: PaymentMandate) -> ChainReceipt:
    # Real implementation would:
    # 1. Build transaction
    # 2. Sign with MPC
    # 3. Broadcast
    # 4. Wait for confirmation (10-60s)
    pass
```
**Impact**: Real chain execution exceeds Vercel's 60s limit.

### 2. In-Memory State
```python
# legacy/sardis_core/services/payment_service.py
self._idempotency_cache: dict[str, tuple[PaymentResult, datetime]] = {}
self._holds: dict[str, PaymentHold] = {}
self._refunds: dict[str, list[Decimal]] = {}
```
**Impact**: State lost between invocations.

### 3. SQLite Write Operations
```python
# sardis-protocol/storage.py
self._conn = sqlite3.connect(path, check_same_thread=False)
```
**Impact**: Vercel's read-only filesystem breaks SQLite writes.

### 4. Webhook Delivery
```python
# Async webhook emission in payment_service.py
loop.create_task(self._webhook_manager.emit(event))
```
**Impact**: Background tasks killed when function returns.

## 2.3 Recommended Deployment Structure

### Option A: Vercel + Secondary Backend (Recommended)

```
┌─────────────────────────────────────────────────────────────────┐
│                         VERCEL                                   │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  sardis-api (FastAPI)                                        ││
│  │  - Mandate verification                                      ││
│  │  - Policy validation                                         ││
│  │  - Compliance checks                                         ││
│  │  - Queue job dispatch                                        ││
│  └─────────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  dashboard (React/Vite)                                      ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │ PostgreSQL   │  │ Redis/Upstash│  │ Queue        │          │
│  │ (Neon/Supabase)│ │ (Cache+Pub) │  │ (Inngest/QStash)│       │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    CLOUD RUN / FLY.IO                            │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  Chain Executor Worker                                       ││
│  │  - MPC signing (Turnkey/Fireblocks)                         ││
│  │  - Transaction broadcast                                     ││
│  │  - Confirmation polling                                      ││
│  │  - Webhook delivery                                          ││
│  └─────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────┘
```

### Option B: Full Cloud Run / Fly.io

If real-time blockchain execution is required, deploy everything on:
- **Cloud Run** (GCP) — Auto-scaling, up to 60min timeout
- **Fly.io** — Edge deployment, persistent processes

## 2.4 Final Recommended Hosting Architecture

| Component | Platform | Rationale |
|-----------|----------|-----------|
| **API Gateway** | Vercel Serverless | Fast cold starts, edge caching |
| **Dashboard** | Vercel Static | CDN, instant deploys |
| **Chain Executor** | Cloud Run | Long-running, auto-scale

I'll continue the comprehensive analysis from where it was cut off.

---

# 2. Deployment Feasibility on Vercel (Continued)

## 2.4 Final Recommended Hosting Architecture

| Component | Platform | Rationale |
|-----------|----------|-----------|
| **API Gateway** | Vercel Serverless | Fast cold starts, edge caching, <10s operations |
| **Dashboard** | Vercel Static | CDN, instant deploys |
| **Chain Executor** | Cloud Run / Fly.io | Long-running processes, MPC signing |
| **Webhook Worker** | Cloud Run / Inngest | Reliable delivery with retries |
| **Database** | Neon PostgreSQL | Serverless-compatible, branching |
| **Cache** | Upstash Redis | Serverless Redis, rate limiting |
| **Queue** | Inngest / QStash | Serverless job queue |

### Vercel Configuration

```json
// vercel.json
{
  "functions": {
    "api/**/*.py": {
      "runtime": "@vercel/python@3.12",
      "maxDuration": 60
    }
  },
  "rewrites": [
    { "source": "/api/v2/:path*", "destination": "/api/main.py" }
  ]
}
```

---

# 3. Security and Compliance Review

## 3.1 Wallet Logic Security

### Current Implementation Analysis

| Area | Status | Risk Level | Finding |
|------|--------|------------|---------|
| **Balance checks** | ✅ Good | Low | Checked before transfer in [can_spend()](cci:1://file:///Users/efebarandurmaz/Desktop/sardis/sardis-core/src/sardis_v2_core/wallets.py:90:4-105:25) |
| **Limit enforcement** | ✅ Good | Low | Multi-tier limits (per-tx, daily, weekly, monthly, total) |
| **Atomic transfers** | ✅ Good | Low | PostgreSQL uses `SELECT ... FOR UPDATE` |
| **Decimal precision** | ✅ Good | Low | Uses `Decimal` not `float` |
| **Private key storage** | 🔴 Critical | High | Hardcoded in config, no vault |
| **Signature verification** | ⚠️ Partial | Medium | Ed25519/ECDSA implemented, but not enforced on all routes |

### Critical Security Issues

#### 1. Private Key Exposure
```python
# legacy/sardis_core/config.py:36
relayer_private_key: str = "0x0000000000000000000000000000000000000000000000000000000000000000"
```
**Risk**: Private keys in code/env files can be leaked.
**Fix**: Use AWS Secrets Manager, HashiCorp Vault, or MPC providers.

#### 2. CORS Wildcard
```python
# legacy/sardis_core/api/main.py:51-57
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # DANGEROUS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
**Risk**: Allows any origin to make authenticated requests.
**Fix**: Whitelist specific domains.

#### 3. Weak Default Secret
```python
# legacy/sardis_core/config.py:27
secret_key: str = "insecure-secret-key-change-me"
admin_password: str = "admin"
```
**Risk**: Default credentials in production.
**Fix**: Require strong secrets via environment validation.

## 3.2 Rate Limiting

### Current State
- **Not implemented** — No rate limiting middleware exists
- [IMPLEMENTATION_PLAN.md](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/IMPLEMENTATION_PLAN.md:0:0-0:0) mentions 100 req/min standard, 1000 req/min premium

### Recommended Implementation
```python
# Using slowapi or custom middleware
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.get("/api/v2/payments")
@limiter.limit("100/minute")
async def list_payments():
    pass
```

## 3.3 Key Management

### Current State
- Keys stored in environment variables
- No rotation mechanism
- No HSM/MPC integration

### Recommended Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    KEY MANAGEMENT                            │
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │   Turnkey    │    │  Fireblocks  │    │   AWS KMS    │  │
│  │  (MPC Keys)  │    │  (MPC Keys)  │    │  (Secrets)   │  │
│  └──────┬───────┘    └──────┬───────┘    └──────┬───────┘  │
│         │                   │                   │           │
│         └───────────────────┼───────────────────┘           │
│                             │                               │
│                             ▼                               │
│                    ┌──────────────┐                         │
│                    │ Key Router   │                         │
│                    │ (sardis-chain)│                        │
│                    └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

## 3.4 Transaction Trust Boundaries

### Current Trust Model
```
Agent (untrusted) → API (semi-trusted) → Ledger (trusted) → Chain (trusted)
```

### Identified Vulnerabilities

| Boundary | Vulnerability | Mitigation |
|----------|--------------|------------|
| Agent → API | Replay attacks | ✅ Replay cache implemented |
| Agent → API | Expired mandates | ✅ TTL check implemented |
| Agent → API | Forged signatures | ✅ Ed25519/ECDSA verification |
| API → Ledger | Double-spend | ✅ Atomic transactions with locks |
| API → Chain | Front-running | ❌ Not addressed |
| Chain → Ledger | Reorg handling | ❌ Not implemented |

## 3.5 Unsafe Patterns

### 1. In-Memory State for Financial Data
```python
# legacy/sardis_core/services/payment_service.py:151
self._holds: dict[str, PaymentHold] = {}
```
**Risk**: Server restart loses active holds.
**Fix**: Persist to database.

### 2. Synchronous Lock in Async Context
```python
# legacy/sardis_core/services/payment_service.py:693
def _check_idempotency(self, key: str) -> Optional[PaymentResult]:
    with self._lock:  # threading.Lock in async code
```
**Risk**: Blocks event loop.
**Fix**: Use `asyncio.Lock()`.

### 3. Broad Exception Handling
```python
# sardis-protocol/verifier.py:54
except Exception:  # noqa: BLE001
    return VerificationResult(False, "signature_malformed")
```
**Risk**: Hides actual errors.
**Fix**: Catch specific exceptions.

## 3.6 Compliance Recommendations

### GENIUS Act Alignment
The codebase mentions GENIUS Act compliance. Current implementation:

| Requirement | Status | Gap |
|-------------|--------|-----|
| Transaction monitoring | ⚠️ Partial | Ledger exists, no real-time alerts |
| SAR reporting | ❌ Missing | Hooks defined, not connected |
| KYC integration | ❌ Missing | No identity verification |
| Sanctions screening | ❌ Missing | No OFAC/SDN checks |
| Audit trail | ✅ Implemented | Merkle-anchored ledger |

### Recommended Integrations
- **Persona** — KYC/identity verification
- **Elliptic** — Blockchain analytics, sanctions screening
- **Chainalysis** — Transaction monitoring
- **Sardine** — Fraud detection

---

# 4. API and SDK Audit

## 4.1 API Route Analysis

### V2 API ([sardis-api](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-api:0:0-0:0))

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v2/mandates/execute` | POST | Execute single mandate | ✅ Implemented |
| `/api/v2/ap2/payments/execute` | POST | Execute AP2 bundle | ✅ Implemented |
| `/api/v2/docs` | GET | OpenAPI docs | ✅ Implemented |

### V1 API ([legacy/sardis_core/api](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/legacy/sardis_core/api:0:0-0:0))

| Endpoint | Method | Purpose | Status |
|----------|--------|---------|--------|
| `/api/v1/agents` | CRUD | Agent management | ✅ Implemented |
| `/api/v1/payments` | POST | Execute payment | ✅ Implemented |
| `/api/v1/payments/holds` | CRUD | Pre-authorization | ✅ Implemented |
| `/api/v1/payments/{id}/refund` | POST | Refund transaction | ✅ Implemented |
| `/api/v1/merchants` | CRUD | Merchant management | ✅ Implemented |
| `/api/v1/webhooks` | CRUD | Webhook management | ✅ Implemented |
| `/api/v1/risk` | GET | Risk scoring | ✅ Implemented |
| `/api/v1/marketplace` | CRUD | A2A marketplace | ✅ Implemented |

## 4.2 API Design Issues

### 1. Inconsistent Versioning
- V1 at `/api/v1/*` (legacy)
- V2 at `/api/v2/*` (new)
- No deprecation headers or migration path

### 2. Missing Error Handling
```python
# sardis-api/routers/ap2.py:37-38
except PaymentExecutionError as exc:
    raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=str(exc))
```
**Issue**: Generic 400 for all errors. No error codes.

### 3. No Pagination Metadata
```python
# legacy/sardis_core/api/routes/payments.py:700
async def list_agent_transactions(
    agent_id: str,
    limit: int = 50,
    offset: int = 0,
) -> list[TransactionResponse]:
```
**Issue**: Returns list without total count, next/prev links.

## 4.3 Recommended API Restructure

### Unified V2 API Design

```
/api/v2/
├── /agents
│   ├── POST   /                    # Create agent
│   ├── GET    /                    # List agents
│   ├── GET    /{id}                # Get agent
│   ├── PATCH  /{id}                # Update agent
│   └── DELETE /{id}                # Deactivate agent
│
├── /wallets
│   ├── GET    /{id}                # Get wallet
│   ├── GET    /{id}/balance        # Get balance
│   ├── POST   /{id}/fund           # Fund wallet
│   └── GET    /{id}/transactions   # List transactions
│
├── /payments
│   ├── POST   /execute             # Execute payment
│   ├── GET    /{id}                # Get payment
│   ├── POST   /{id}/refund         # Refund payment
│   └── GET    /{id}/verify         # On-chain verification
│
├── /holds
│   ├── POST   /                    # Create hold
│   ├── GET    /{id}                # Get hold
│   ├── POST   /{id}/capture        # Capture hold
│   └── POST   /{id}/void           # Void hold
│
├── /mandates
│   ├── POST   /execute             # Execute mandate
│   └── POST   /ap2/execute         # Execute AP2 bundle
│
├── /policies
│   ├── GET    /{agent_id}          # Get policy
│   ├── PUT    /{agent_id}          # Update policy
│   └── POST   /{agent_id}/rules    # Add merchant rule
│
└── /webhooks
    ├── POST   /                    # Register webhook
    ├── GET    /                    # List webhooks
    ├── DELETE /{id}                # Remove webhook
    └── GET    /{id}/deliveries     # List deliveries
```

### Standardized Error Response

```json
{
  "error": {
    "code": "INSUFFICIENT_BALANCE",
    "message": "Wallet balance too low for this transaction",
    "details": {
      "required": "150.00",
      "available": "100.00",
      "currency": "USDC"
    },
    "request_id": "req_abc123xyz",
    "documentation_url": "https://docs.sardis.network/errors#INSUFFICIENT_BALANCE"
  }
}
```

## 4.4 SDK Audit

### Python SDK ([sardis-sdk-python](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-sdk-python:0:0-0:0))

**Current State**: Minimal, 30 lines
```python
class SardisClient:
    async def execute_payment(self, mandate: PaymentMandate) -> dict
    async def execute_ap2_payment(self, bundle: dict) -> dict
```

**Missing**:
- Agent management
- Wallet operations
- Hold/capture/void
- Webhook registration
- Error handling classes
- Retry logic
- Type hints for responses

### TypeScript SDK ([sardis-sdk-js](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-sdk-js:0:0-0:0))

**Current State**: Minimal, 52 lines
```typescript
class SardisClient {
    executePayment(input: ExecutePaymentInput): Promise<MandateExecutionResponse>
    executeAp2Payment(input: ExecuteAp2PaymentInput): Promise<ExecuteAp2PaymentResponse>
}
```

**Missing**:
- Same gaps as Python SDK
- No browser/Node detection
- No request interceptors

## 4.5 Proposed SDK Design

### Python SDK Structure
```
sardis-sdk-python/
├── sardis/
│   ├── __init__.py
│   ├── client.py           # Main client
│   ├── agents.py           # Agent operations
│   ├── wallets.py          # Wallet operations
│   ├── payments.py         # Payment operations
│   ├── mandates.py         # Mandate operations
│   ├── policies.py         # Policy operations
│   ├── webhooks.py         # Webhook operations
│   ├── models/
│   │   ├── agent.py
│   │   ├── wallet.py
│   │   ├── payment.py
│   │   ├── mandate.py
│   │   └── errors.py
│   └── utils/
│       ├── signing.py      # Ed25519/ECDSA helpers
│       ├── retry.py        # Exponential backoff
│       └── validation.py
├── tests/
└── pyproject.toml
```

### TypeScript SDK Structure
```
sardis-sdk-js/
├── src/
│   ├── index.ts
│   ├── client.ts
│   ├── resources/
│   │   ├── agents.ts
│   │   ├── wallets.ts
│   │   ├── payments.ts
│   │   ├── mandates.ts
│   │   └── webhooks.ts
│   ├── models/
│   │   ├── agent.ts
│   │   ├── wallet.ts
│   │   ├── payment.ts
│   │   └── errors.ts
│   └── utils/
│       ├── signing.ts
│       └── retry.ts
├── tests/
├── package.json
└── tsconfig.json
```

---

# 5. Database and State Layer Review

## 5.1 Current Schema Analysis

### V1 Schema (PostgreSQL via Alembic)

```sql
-- From legacy/sardis_core/database/models.py

CREATE TABLE organizations (
    org_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    admin_ids JSON,
    settings JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE agents (
    agent_id VARCHAR PRIMARY KEY,
    name VARCHAR NOT NULL,
    owner_id VARCHAR NOT NULL,
    organization_id VARCHAR REFERENCES organizations,
    description TEXT,
    wallet_id VARCHAR,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE wallets (
    wallet_id VARCHAR PRIMARY KEY,
    agent_id VARCHAR REFERENCES agents NOT NULL,
    balances JSON,  -- {"USDC": "100.00", "USDT": "50.00"}
    currency VARCHAR DEFAULT 'USDC',
    limit_per_tx NUMERIC(20,6),
    limit_total NUMERIC(20,6),
    spent_total NUMERIC(20,6),
    virtual_card JSON,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE transactions (
    tx_id VARCHAR PRIMARY KEY,
    from_wallet VARCHAR NOT NULL,
    to_wallet VARCHAR NOT NULL,
    amount NUMERIC(20,6) NOT NULL,
    fee NUMERIC(20,6) DEFAULT 0,
    currency VARCHAR NOT NULL,
    purpose VARCHAR,
    status VARCHAR NOT NULL,
    error_message TEXT,
    extra_data JSON,
    created_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE
);

CREATE TABLE api_keys (
    key_id VARCHAR PRIMARY KEY,
    key_hash VARCHAR NOT NULL,
    owner_id VARCHAR NOT NULL,
    name VARCHAR,
    permissions JSON,
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE
);
```

### V2 Schema (SQLite)

```sql
-- From sardis-protocol/storage.py and sardis-ledger/records.py

CREATE TABLE mandate_chains (
    mandate_id TEXT PRIMARY KEY,
    payload TEXT NOT NULL,  -- JSON blob
    created_at INTEGER NOT NULL
);

CREATE TABLE replay_cache (
    mandate_id TEXT PRIMARY KEY,
    expires_at INTEGER NOT NULL
);

CREATE TABLE ledger_entries (
    tx_id TEXT PRIMARY KEY,
    mandate_id TEXT,
    from_wallet TEXT,
    to_wallet TEXT,
    amount TEXT,
    currency TEXT,
    chain TEXT,
    chain_tx_hash TEXT,
    audit_anchor TEXT,
    created_at TEXT
);
```

## 5.2 Schema Issues

| Issue | Severity | Details |
|-------|----------|---------|
| **JSON blobs for structured data** | 🟡 Medium | `balances`, `permissions`, `virtual_card` should be normalized |
| **No spending policy table** | 🟡 Medium | Policies created in-memory, not persisted |
| **No merchant rules table** | 🟡 Medium | Rules embedded in policy, not queryable |
| **No holds table** | 🔴 High | Holds stored in-memory only |
| **No webhook deliveries table** | 🟡 Medium | Can't track delivery status |
| **No audit log table** | 🟡 Medium | No immutable action log |
| **Missing indexes** | 🟡 Medium | Only `created_at` indexed on transactions |

## 5.3 Production-Ready Schema Proposal

```sql
-- =====================================================
-- CORE ENTITIES
-- =====================================================

CREATE TABLE organizations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    settings JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    organization_id UUID REFERENCES organizations(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    public_key BYTEA,  -- Ed25519/ECDSA public key
    key_algorithm VARCHAR(20) DEFAULT 'ed25519',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_agents_org ON agents(organization_id);
CREATE INDEX idx_agents_active ON agents(is_active) WHERE is_active = TRUE;

-- =====================================================
-- WALLETS & BALANCES
-- =====================================================

CREATE TABLE wallets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    agent_id UUID REFERENCES agents(id) NOT NULL,
    chain_address VARCHAR(66),  -- 0x... or Solana address
    chain VARCHAR(20) DEFAULT 'base',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_wallets_agent ON wallets(agent_id);
CREATE INDEX idx_wallets_chain ON wallets(chain, chain_address);

CREATE TABLE token_balances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    wallet_id UUID REFERENCES wallets(id) NOT NULL,
    token VARCHAR(10) NOT NULL,  -- USDC, USDT, PYUSD, EURC
    balance NUMERIC(20,6) DEFAULT 0,
    spent_total NUMERIC(20,6) DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(wallet_id, token)
);

CREATE INDEX idx_balances_wallet ON token_balances(wallet_id);

-- =====================================================
-- SPENDING POLICIES
-- =====================================================

CREATE TABLE spending_policies (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID REFERENCES agents(id) UNIQUE NOT NULL,
    trust_level VARCHAR(20) DEFAULT 'low',
    limit_per_tx NUMERIC(20,6) DEFAULT 100,
    limit_total NUMERIC(20,6) DEFAULT 1000,
    require_preauth BOOLEAN DEFAULT FALSE,
    allowed_scopes VARCHAR[] DEFAULT ARRAY['all'],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE time_window_limits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES spending_policies(id) NOT NULL,
    window_type VARCHAR(20) NOT NULL,  -- daily, weekly, monthly
    limit_amount NUMERIC(20,6) NOT NULL,
    current_spent NUMERIC(20,6) DEFAULT 0,
    window_start TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(policy_id, window_type)
);

CREATE TABLE merchant_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    policy_id UUID REFERENCES spending_policies(id) NOT NULL,
    rule_type VARCHAR(10) NOT NULL,  -- allow, deny
    merchant_id VARCHAR(64),
    category VARCHAR(50),
    max_per_tx NUMERIC(20,6),
    daily_limit NUMERIC(20,6),
    reason TEXT,
    expires_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_merchant_rules_policy ON merchant_rules(policy_id);
CREATE INDEX idx_merchant_rules_merchant ON merchant_rules(merchant_id);

-- =====================================================
-- TRANSACTIONS
-- =====================================================

CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    from_wallet_id UUID REFERENCES wallets(id) NOT NULL,
    to_wallet_id UUID REFERENCES wallets(id) NOT NULL,
    amount NUMERIC(20,6) NOT NULL,
    fee NUMERIC(20,6) DEFAULT 0,
    token VARCHAR(10) NOT NULL,
    purpose TEXT,
    status VARCHAR(20) NOT NULL,  -- pending, completed, failed, refunded
    error_message TEXT,
    idempotency_key VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_tx_from ON transactions(from_wallet_id);
CREATE INDEX idx_tx_to ON transactions(to_wallet_id);
CREATE INDEX idx_tx_status ON transactions(status);
CREATE INDEX idx_tx_created ON transactions(created_at DESC);
CREATE UNIQUE INDEX idx_tx_idempotency ON transactions(idempotency_key) WHERE idempotency_key IS NOT NULL;

CREATE TABLE on_chain_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    transaction_id UUID REFERENCES transactions(id) NOT NULL,
    chain VARCHAR(20) NOT NULL,
    tx_hash VARCHAR(66) NOT NULL,
    block_number BIGINT,
    from_address VARCHAR(66),
    to_address VARCHAR(66),
    status VARCHAR(20) DEFAULT 'pending',
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chain_records_tx ON on_chain_records(transaction_id);
CREATE INDEX idx_chain_records_hash ON on_chain_records(chain, tx_hash);

-- =====================================================
-- HOLDS (PRE-AUTHORIZATION)
-- =====================================================

CREATE TABLE holds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    external_id VARCHAR(64) UNIQUE NOT NULL,
    wallet_id UUID REFERENCES wallets(id) NOT NULL,
    merchant_id VARCHAR(64),
    amount NUMERIC(20,6) NOT NULL,
    token VARCHAR(10) NOT NULL,
    status VARCHAR(20) DEFAULT 'active',  -- active, captured, voided, expired
    purpose TEXT,
    expires_at TIMESTAMPTZ NOT NULL,
    captured_amount NUMERIC(20,6),
    captured_at TIMESTAMPTZ,
    capture_tx_id UUID REFERENCES transactions(id),
    voided_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_holds_wallet ON holds(wallet_id);
CREATE INDEX idx_holds_status ON holds(status);
CREATE INDEX idx_holds_expires ON holds(expires_at) WHERE status = 'active';

-- =====================================================
-- MANDATES (AP2)
-- =====================================================

CREATE TABLE mandates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mandate_id VARCHAR(64) UNIQUE NOT NULL,
    mandate_type VARCHAR(20) NOT NULL,  -- intent, cart, payment
    issuer VARCHAR(255) NOT NULL,
    subject VARCHAR(255) NOT NULL,
    domain VARCHAR(255) NOT NULL,
    payload JSONB NOT NULL,
    proof JSONB NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    verified_at TIMESTAMPTZ,
    executed_at TIMESTAMPTZ,
    transaction_id UUID REFERENCES transactions(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_mandates_subject ON mandates(subject);
CREATE INDEX idx_mandates_type ON mandates(mandate_type);
CREATE INDEX idx_mandates_expires ON mandates(expires_at);

CREATE TABLE mandate_chains (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    intent_id UUID REFERENCES mandates(id) NOT NULL,
    cart_id UUID REFERENCES mandates(id) NOT NULL,
    payment_id UUID REFERENCES mandates(id) NOT NULL,
    verified_at TIMESTAMPTZ DEFAULT NOW(),
    executed_at TIMESTAMPTZ,
    transaction_id UUID REFERENCES transactions(id)
);

-- =====================================================
-- WEBHOOKS
-- =====================================================

CREATE TABLE webhooks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    url VARCHAR(2048) NOT NULL,
    secret VARCHAR(64) NOT NULL,
    events VARCHAR[] NOT NULL,  -- ['payment.completed', 'hold.created']
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_webhooks_org ON webhooks(organization_id);

CREATE TABLE webhook_deliveries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    webhook_id UUID REFERENCES webhooks(id) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    payload JSONB NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending, delivered, failed
    attempts INTEGER DEFAULT 0,
    last_attempt_at TIMESTAMPTZ,
    response_status INTEGER,
    response_body TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_deliveries_webhook ON webhook_deliveries(webhook_id);
CREATE INDEX idx_deliveries_status ON webhook_deliveries(status) WHERE status = 'pending';

-- =====================================================
-- AUDIT LOG
-- =====================================================

CREATE TABLE audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_type VARCHAR(20) NOT NULL,  -- agent, system, admin
    actor_id VARCHAR(64) NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id VARCHAR(64) NOT NULL,
    changes JSONB,
    ip_address INET,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_audit_actor ON audit_log(actor_type, actor_id);
CREATE INDEX idx_audit_resource ON audit_log(resource_type, resource_id);
CREATE INDEX idx_audit_created ON audit_log(created_at DESC);

-- =====================================================
-- API KEYS
-- =====================================================

CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    key_prefix VARCHAR(8) NOT NULL,  -- First 8 chars for lookup
    key_hash VARCHAR(64) NOT NULL,   -- SHA-256 of full key
    organization_id UUID REFERENCES organizations(id) NOT NULL,
    name VARCHAR(255),
    scopes VARCHAR[] DEFAULT ARRAY['read'],
    rate_limit INTEGER DEFAULT 100,  -- requests per minute
    is_active BOOLEAN DEFAULT TRUE,
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_prefix ON api_keys(key_prefix);
CREATE INDEX idx_api_keys_org ON api_keys(organization_id);
```

## 5.4 Migration Strategy

1. **Create new schema** alongside existing tables
2. **Dual-write** during transition period
3. **Backfill** historical data
4. **Switch reads** to new schema
5. **Drop old tables** after verification

---

# 6. Architecture Redesign Proposal

## 6.1 Target Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              EDGE LAYER                                      │
│  ┌─────────────────────────────────────────────────────────────────────────┐│
│  │  Cloudflare / Vercel Edge                                                ││
│  │  - Rate limiting                                                         ││
│  │  - DDoS protection                                                       ││
│  │  - Geographic routing                                                    ││
│  └─────────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API LAYER                                       │
│  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐ │
│  │  sardis-api          │  │  sardis-api          │  │  sardis-api        │ │
│  │  (Vercel/Cloud Run)  │  │  (Vercel/Cloud Run)  │  │  (Vercel/Cloud Run)│ │
│  │  - Mandate verify    │  │  - Mandate verify    │  │  - Mandate verify  │ │
│  │  - Policy check      │  │  - Policy check      │  │  - Policy check    │ │
│  │  - Queue dispatch    │  │  - Queue dispatch    │  │  - Queue dispatch  │ │
│  └──────────────────────┘  └──────────────────────┘  └────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           SERVICE LAYER                                      │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  WALLET ENGINE   │  │  LIMITS ENGINE   │  │  TX PROCESSOR    │          │
│  │  ---------------  │  │  ---------------  │  │  ---------------  │          │
│  │  - Balance mgmt  │  │  - Policy eval   │  │  - Ledger writes │          │
│  │  - Multi-token   │  │  - Window limits │  │  - Idempotency   │          │
│  │  - Holds         │  │  - Merchant rules│  │  - Refunds       │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
│                                                                              │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  COMPLIANCE      │  │  WEBHOOK SYSTEM  │  │  AUDIT SERVICE   │          │
│  │  ---------------  │  │  ---------------  │  │  ---------------  │          │
│  │  - Token checks  │  │  - Event emit    │  │  - Action log    │          │
│  │  - Amount limits │  │  - Retry queue   │  │  - Merkle anchor │          │
│  │  - SAR hooks     │  │  - Delivery track│  │  - Export        │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BLOCKCHAIN LAYER                                     │
│  ┌──────────────────────────────────────────────────────────────────────┐   │
│  │  CHAIN EXECUTOR (Cloud Run - Long Running)                            │   │
│  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐     │   │
│  │  │  Turnkey   │  │ Fireblocks │  │   Base     │  │  Polygon   │     │   │
│  │  │  MPC Signer│  │  MPC Signer│  │  Executor  │  │  Executor  │     │   │
│  │  └────────────┘  └────────────┘  └────────────┘  └────────────┘     │   │
│  └──────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           DATA LAYER                                         │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐          │
│  │  PostgreSQL      │  │  Redis           │  │  Object Storage  │          │
│  │  (Neon)          │  │  (Upstash)       │  │  (S3/GCS)        │          │
│  │  ---------------  │  │  ---------------  │  │  ---------------  │          │
│  │  - All entities  │  │  - Rate limits   │  │  - Audit exports │          │
│  │  - Transactions  │  │  - Session cache │  │  - Receipts      │          │
│  │  - Audit log     │  │  - Pub/Sub       │  │  - Backups       │          │
│  └──────────────────┘  └──────────────────┘  └──────────────────┘          │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 6.2 Component Specifications

### Core Backend ([sardis-api](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-api:0:0-0:0))
- **Runtime**: Python 3.12, FastAPI
- **Deployment**: Vercel Serverless or Cloud Run
- **Responsibilities**:
  - Request validation
  - Mandate verification
  - Policy evaluation
  - Job dispatch to queue
  - Response formatting

### Wallet Engine ([sardis-wallet](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-wallet:0:0-0:0))
- **Runtime**: Python 3.12
- **Deployment**: Shared library, imported by API
- **Responsibilities**:
  - Balance management
  - Multi-token support
  - Hold creation/capture/void
  - Virtual card management

### Limits Engine (`sardis-limits`)
- **Runtime**: Python 3.12
- **Deployment**: Shared library
- **Responsibilities**:
  - Policy evaluation
  - Time window limit tracking
  - Merchant rule matching
  - Trust level enforcement

### Transaction Processor ([sardis-ledger](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-ledger:0:0-0:0))
- **Runtime**: Python 3.12
- **Deployment**: Shared library
- **Responsibilities**:
  - Atomic ledger writes
  - Idempotency enforcement
  - Refund processing
  - Balance reconciliation

### Webhook System (`sardis-webhooks`)
- **Runtime**: Python 3.12
- **Deployment**: Inngest functions or Cloud Run
- **Responsibilities**:
  - Event emission
  - Retry with exponential backoff
  - Delivery tracking
  - Signature generation

### Audit Service (`sardis-audit`)
- **Runtime**: Python 3.12
- **Deployment**: Shared library + background worker
- **Responsibilities**:
  - Action logging
  - Merkle tree anchoring
  - Compliance exports
  - SAR generation

### Blockchain Service ([sardis-chain](cci:7://file:///Users/efebarandurmaz/Desktop/sardis/sardis-chain:0:0-0:0))
- **Runtime**: Python 3.12
- **Deployment**: Cloud Run (long-running)
- **Responsibilities**:
  - MPC signing (Turnkey/Fireblocks)
  - Transaction broadcast
  - Confirmation polling
  - Reorg handling
  - Gas optimization

### Queue System
- **Provider**: Inngest, QStash, or Cloud Tasks
- **Queues**:
  - `chain-execution` — Blockchain transactions
  - `webhook-delivery` — Webhook dispatch
  - `audit-anchor` — Merkle tree updates
  - `limit-reset` — Time window resets

### CI/CD
- **Provider**: GitHub Actions
- **Pipelines**:
  - `test` — Run pytest, type checking
  - `lint` — Ruff, black, mypy
  - `deploy-staging` — Auto-deploy on PR merge
  - `deploy-production` — Manual approval required
  - `migrate` — Database migrations

## 6.3 Recommended Hosting

| Component | Recommended | Alternative |
|-----------|-------------|-------------|
| API | Vercel Serverless | Cloud Run |
| Dashboard | Vercel Static | Cloudflare Pages |
| Chain Executor | Cloud Run | Fly.io |
| Webhook Worker | Inngest | Cloud Run |
| Database | Neon PostgreSQL | Supabase |
| Cache | Upstash Redis | Momento |
| Queue | Inngest | QStash |
| Secrets | Google Secret Manager | AWS Secrets Manager |
| Monitoring | Datadog | Grafana Cloud |

---

# 7. Future Roadmap (90-Day Engineering Plan)

## Phase 1: Stabilization (Weeks 1-3)

### Objectives
- Consolidate V1/V2 codebases
- Fix critical security issues
- Establish CI/CD pipeline

### Tasks

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Merge V2 packages into unified structure | P0 | 3d | Backend |
| Remove legacy/ directory after migration | P0 | 1d | Backend |
| Implement rate limiting middleware | P0 | 2d | Backend |
| Fix CORS configuration | P0 | 0.5d | Backend |
| Move secrets to vault (AWS SM/GCP SM) | P0 | 2d | DevOps |
| Set up GitHub Actions CI | P1 | 2d | DevOps |
| Add pytest coverage to 60% | P1 | 3d | Backend |
| Implement structured logging | P1 | 1d | Backend |
| Add health check endpoints | P1 | 0.5d | Backend |
| Deploy to staging environment | P1 | 2d | DevOps |

### Acceptance Criteria
- [ ] Single codebase with clear module boundaries
- [ ] All secrets in vault, no hardcoded credentials
- [ ] CI runs on every PR with >60% test coverage
- [ ] Rate limiting active (100 req/min default)
- [ ] Staging environment accessible

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking changes during merge | High | High | Feature flags, gradual rollout |
| CI flakiness | Medium | Medium | Retry logic, test isolation |

### Success Metrics
- Zero hardcoded secrets in codebase
- <5% CI failure rate
- <500ms p99 API latency

---

## Phase 2: Wallet Engine V2 (Weeks 4-6)

### Objectives
- Persist all wallet state to PostgreSQL
- Implement holds in database
- Add conversation memory for AI agents

### Tasks

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Create production schema (Section 5.3) | P0 | 2d | Backend |
| Migrate wallets to new schema | P0 | 3d | Backend |
| Implement holds table + service | P0 | 2d | Backend |
| Add spending_policies table | P0 | 2d | Backend |
| Implement time_window_limits | P1 | 2d | Backend |
| Add merchant_rules table | P1 | 1d | Backend |
| Create conversations table | P1 | 1d | Backend |
| Implement conversation memory in AgentService | P1 | 2d | Backend |
| Add wallet balance caching (Redis) | P2 | 1d | Backend |
| Write migration scripts | P1 | 1d | Backend |

### Acceptance Criteria
- [ ] All wallet operations persist to PostgreSQL
- [ ] Holds survive server restarts
- [ ] Spending policies queryable via API
- [ ] AI agents remember last 10 messages
- [ ] Zero data loss during migration

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Data migration errors | Medium | Critical | Dual-write, rollback plan |
| Performance regression | Medium | High | Load testing, caching |

### Success Metrics
- 100% of holds persisted
- <50ms database query time
- Zero migration-related incidents

---

## Phase 3: Programmable Rails (Weeks 7-9)

### Objectives
- Real blockchain execution
- MPC wallet integration
- Webhook delivery system

### Tasks

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Integrate Turnkey MPC SDK | P0 | 5d | Backend |
| Implement real chain execution | P0 | 5d | Backend |
| Add transaction confirmation polling | P0 | 2d | Backend |
| Implement gas estimation | P1 | 2d | Backend |
| Add reorg detection | P1 | 2d | Backend |
| Create webhook delivery worker | P0 | 3d | Backend |
| Implement retry with backoff | P1 | 1d | Backend |
| Add webhook signature verification | P1 | 1d | Backend |
| Deploy chain executor to Cloud Run | P0 | 2d | DevOps |
| Add on-chain verification endpoint | P2 | 1d | Backend |

### Acceptance Criteria
- [ ] Payments execute on Base Sepolia testnet
- [ ] MPC signing via Turnkey working
- [ ] Webhooks delivered with <5s latency
- [ ] Failed webhooks retried 3x with backoff
- [ ] On-chain transactions verifiable via API

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| MPC integration complexity | High | High | Start with testnet, fallback to simulation |
| Chain congestion | Medium | Medium | Multi-chain routing, gas optimization |
| Webhook delivery failures | Medium | Medium | Dead letter queue, alerting |

### Success Metrics
- >95% transaction success rate
- <30s average confirmation time
- >99% webhook delivery rate

---

## Phase 4: Marketplace for A2A Services (Weeks 10-12)

### Objectives
- Agent-to-agent payment marketplace
- Escrow contract deployment
- Service discovery API

### Tasks

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Deploy SardisEscrow.sol to testnet | P0 | 2d | Smart Contract |
| Create escrow service in backend | P0 | 3d | Backend |
| Implement milestone-based payments | P0 | 3d | Backend |
| Add dispute resolution flow | P1 | 2d | Backend |
| Create service listing API | P1 | 2d | Backend |
| Implement service discovery | P1 | 2d | Backend |
| Add agent reputation system | P2 | 3d | Backend |
| Create marketplace dashboard page | P1 | 3d | Frontend |
| Add A2A payment SDK methods | P1 | 2d | SDK |

### Acceptance Criteria
- [ ] Escrow contract deployed and verified
- [ ] Agents can create/accept service offers
- [ ] Milestone payments release on confirmation
- [ ] Disputes escalate to arbiter
- [ ] Marketplace visible in dashboard

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Smart contract bugs | Medium | Critical | Audit, testnet-first |
| Low marketplace adoption | Medium | Medium | Seed with demo services |

### Success Metrics
- 10+ services listed
- 5+ successful A2A transactions
- Zero escrow disputes unresolved

---

## Phase 5: Production Scale (Weeks 13-16)

### Objectives
- Production deployment
- Mainnet readiness
- Compliance integrations

### Tasks

| Task | Priority | Effort | Owner |
|------|----------|--------|-------|
| Security audit (external) | P0 | 2w | Security |
| Smart contract audit | P0 | 2w | Security |
| Deploy to production infrastructure | P0 | 3d | DevOps |
| Implement blue-green deployment | P1 | 2d | DevOps |
| Add Datadog monitoring | P1 | 2d | DevOps |
| Integrate Persona KYC | P1 | 3d | Backend |
| Integrate Elliptic sanctions screening | P1 | 2d | Backend |
| Create SAR export functionality | P1 | 2d | Backend |
| Load testing (1000 TPS target) | P0 | 3d | QA |
| Create operations runbook | P1 | 2d | DevOps |
| Deploy to mainnet (Base, Polygon) | P0 | 2d | DevOps |

### Acceptance Criteria
- [ ] Zero critical vulnerabilities in audit
- [ ] Production handles 1000 TPS
- [ ] KYC required for >$10k transactions
- [ ] Sanctions screening on all transactions
- [ ] Mainnet contracts deployed and verified

### Risks
| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Audit findings | High | High | Budget for remediation time |
| Mainnet gas costs | Medium | Medium | Gas optimization, batching |
| Compliance gaps | Medium | High | Legal review, phased rollout |

### Success Metrics
- Zero critical audit findings
- <200ms p99 latency at 1000 TPS
- 100% sanctions screening coverage

---

# 8. Deliverables

## 8.1 Architecture Audit Summary

**Overall Assessment**: The Sardis codebase demonstrates solid domain modeling and protocol design, but suffers from **dual-codebase fragmentation** (V1 vs V2), **simulated blockchain execution**, and **missing production infrastructure**.

| Area | Score | Notes |
|------|-------|-------|
| Domain Modeling | 8/10 | Clean separation, good use of dataclasses |
| API Design | 6/10 | Functional but inconsistent versioning |
| Security | 4/10 | Critical gaps in key management, CORS |
| Database | 5/10 | Works but needs normalization |
| Blockchain | 3/10 | Entirely simulated |
| Testing | 5/10 | Good coverage in some areas, gaps in others |
| Documentation | 7/10 | Comprehensive docs, some outdated |

## 8.2 Deployment Compatibility Report

| Platform | Compatibility | Blockers |
|----------|--------------|----------|
| **Vercel Serverless** | ⚠️ Partial | SQLite writes, long-running chain ops |
| **Cloud Run** | ✅ Full | None |
| **Fly.io** | ✅ Full | None |
| **AWS Lambda** | ⚠️ Partial | Same as Vercel |

**Recommendation**: Hybrid deployment with Vercel (API/Dashboard) + Cloud Run (Chain Executor).

## 8.3 Engineering Roadmap

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Phase 1: Stabilization | 3 weeks | Unified codebase, CI/CD, security fixes |
| Phase 2: Wallet Engine V2 | 3 weeks | PostgreSQL migration, holds persistence |
| Phase 3: Programmable Rails | 3 weeks | Real chain execution, webhooks |
| Phase 4: A2A Marketplace | 3 weeks | Escrow, service discovery |
| Phase 5: Production | 4 weeks | Audits, mainnet, compliance |

**Total**: 16 weeks (4 months)

## 8.4 Refactored Folder Structure

```
sardis/
├── apps/
│   ├── api/                    # FastAPI application
│   │   ├── src/
│   │   │   ├── routers/
│   │   │   ├── middleware/
│   │   │   ├── dependencies.py
│   │   │   └── main.py
│   │   ├── tests/
│   │   └── pyproject.toml
│   │
│   ├── dashboard/              # React frontend
│   │   ├── src/
│   │   ├── public/
│   │   └── package.json
│   │
│   └── chain-worker/           # Long-running chain executor
│       ├── src/
│       └── pyproject.toml
│
├── packages/
│   ├── core/                   # Shared domain models
│   │   ├── src/sardis_core/
│   │   │   ├── models/
│   │   │   ├── config.py
│   │   │   └── __init__.py
│   │   └── pyproject.toml
│   │
│   ├── wallet/                 # Wallet engine
│   │   ├── src/sardis_wallet/
│   │   └── pyproject.toml
│   │
│   ├── ledger/                 # Transaction ledger
│   │   ├── src/sardis_ledger/
│   │   └── pyproject.toml
│   │
│   ├── protocol/               # AP2/TAP verification
│   │   ├── src/sardis_protocol/
│   │   └── pyproject.toml
│   │
│   ├── chain/                  # Blockchain execution
│   │   ├── src/sardis_chain/
│   │   └── pyproject.toml
│   │
│   ├── compliance/             # Compliance checks
│   │   ├── src/sardis_compliance/
│   │   └── pyproject.toml
│   │
│   └── webhooks/               # Webhook system
│       ├── src/sardis_webhooks/
│       └── pyproject.toml
│
├── sdks/
│   ├── python/                 # Python SDK
│   │   ├── src/sardis/
│   │   └── pyproject.toml
│   │
│   └── typescript/             # TypeScript SDK
│       ├── src/
│       └── package.json
│
├── contracts/                  # Solidity contracts
│   ├── src/
│   ├── script/
│   ├── test/
│   └── foundry.toml
│
├── infra/                      # Infrastructure as code
│   ├── terraform/
│   └── docker/
│
├── docs/                       # Documentation
│   ├── api/
│   ├── guides/
│   └── architecture/
│
├── migrations/                 # Database migrations
│   └── versions/
│
├── .github/
│   └── workflows/
│
├── pyproject.toml              # Root Python config (workspace)
├── package.json                # Root Node config (workspace)
└── README.md
```

## 8.5 Immediate Tasks (Do Now)

| # | Task | Priority | Effort |
|---|------|----------|--------|
| 1 | Remove hardcoded `relayer_private_key` from config | P0 | 1h |
| 2 | Fix CORS to whitelist specific origins | P0 | 1h |
| 3 | Change default `secret_key` and `admin_password` | P0 | 30m |
| 4 | Add rate limiting middleware | P0 | 4h |
| 5 | Set up GitHub Actions for CI | P0 | 4h |
| 6 | Create `.env.example` with required variables | P1 | 1h |
| 7 | Add `asyncio.Lock` instead of `threading.Lock` | P1 | 2h |
| 8 | Persist holds to database | P1 | 8h |
| 9 | Add structured JSON logging | P1 | 4h |
| 10 | Create health check endpoints | P1 | 2h |

## 8.6 Deferred Tasks

| # | Task | Reason for Deferral |
|---|------|---------------------|
| 1 | Mainnet deployment | Requires security audit |
| 2 | Solana integration | Lower priority than EVM chains |
| 3 | Virtual card issuance (Marqeta) | Requires partnership |
| 4 | Mobile SDK | Web-first approach |
| 5 | Multi-tenant SaaS mode | Single-tenant sufficient for MVP |
| 6 | GraphQL API | REST sufficient for now |
| 7 | Real-time WebSocket updates | Polling acceptable initially |

## 8.7 Critical Issues Before Go-Live

| # | Issue | Severity | Blocker? |
|---|-------|----------|----------|
| 1 | **No real blockchain execution** | 🔴 Critical | Yes |
| 2 | **Private keys in code/env** | 🔴 Critical | Yes |
| 3 | **CORS allows all origins** | 🔴 Critical | Yes |
| 4 | **No rate limiting** | 🔴 Critical | Yes |
| 5 | **Holds not persisted** | 🟡 High | Yes |
| 6 | **No security audit** | 🔴 Critical | Yes |
| 7 | **No KYC integration** | 🟡 High | Depends on jurisdiction |
| 8 | **No sanctions screening** | 🟡 High | Yes for US |
| 9 | **Smart contracts not audited** | 🔴 Critical | Yes |
| 10 | **No disaster recovery plan** | 🟡 High | Yes |

---

# Conclusion

Sardis has a **solid foundation** with well-designed domain models, a clear protocol specification (AP2/TAP), and comprehensive documentation. However, **significant engineering work** is required before production deployment:

1. **Immediate**: Fix security vulnerabilities (keys, CORS, rate limiting)
2. **Short-term**: Consolidate codebases, persist all state to PostgreSQL
3. **Medium-term**: Implement real blockchain execution with MPC
4. **Long-term**: Security audits, compliance integrations, mainnet deployment

The 16-week roadmap provides a structured path from current state to production-ready platform. The hybrid Vercel + Cloud Run architecture balances developer experience with the requirements of long-running blockchain operations.

# Sardis Architecture: Pivot Strategy
## Agent Wallet OS + Agentic Checkout

**Version:** 2.0  
**Date:** January 11, 2026  
**Status:** Architecture Design

---

## Executive Summary

Sardis is pivoting to a **hybrid architecture** that combines:
- **Core:** Agent Wallet OS (non-custodial, compliance-light)
- **Surfaces:** Multiple output modes (on-chain, checkout, API)

This architecture minimizes compliance burden while maximizing code reuse and market positioning.

---

## Architecture Philosophy

### Core Principle: "One OS, Multiple Surfaces"

```
┌─────────────────────────────────────────────────────────────┐
│                    AGENT WALLET OS (CORE)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │  Agent   │  │  Wallet  │  │  Policy  │  │ Mandate  │   │
│  │ Identity │  │  (MPC)   │  │  Engine  │  │  (AP2)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Surface:   │  │   Surface:   │  │   Surface:  │
│   On-Chain   │  │   Checkout   │  │     API      │
│              │  │              │  │              │
│  Blockchain  │  │  PSP Routing │  │  REST/GraphQL│
│  Execution   │  │  (Stripe,    │  │              │
│              │  │   PayPal,    │  │              │
│              │  │   etc.)      │  │              │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Key Benefits:**
1. **Compliance Minimization:** Non-custodial core = no MSB/MTL requirements
2. **Code Reuse:** Core logic shared across all surfaces
3. **Market Flexibility:** Can target developers (OS) or merchants (Checkout)
4. **Future-Proof:** Easy to add new surfaces (cards, ACH, etc.)

---

## Repository Structure

### Current Structure (Pre-Pivot)

```
sardis/
├── packages/
│   ├── sardis-core/          # Domain models
│   ├── sardis-api/           # FastAPI application
│   ├── sardis-chain/         # Blockchain execution
│   ├── sardis-protocol/      # AP2/TAP verification
│   ├── sardis-wallet/        # Wallet management
│   ├── sardis-ledger/        # Transaction ledger
│   ├── sardis-compliance/    # KYC/AML
│   ├── sardis-cards/         # Virtual cards
│   ├── sardis-cli/           # CLI tool
│   ├── sardis-sdk-python/    # Python SDK
│   └── sardis-sdk-js/        # TypeScript SDK
├── contracts/                # Solidity contracts
├── dashboard/                # React dashboard
└── landing/                  # Marketing site
```

### New Structure (Post-Pivot)

```
sardis/
├── core/                              # Agent Wallet OS (Pivot B)
│   ├── agent/                         # Agent identity & management
│   │   ├── __init__.py
│   │   ├── models.py                  # Agent dataclasses
│   │   ├── identity.py                # TAP identity management
│   │   └── repository.py              # Agent storage
│   │
│   ├── wallet/                        # Non-custodial wallet abstraction
│   │   ├── __init__.py
│   │   ├── models.py                  # Wallet dataclasses
│   │   ├── mpc.py                     # MPC abstraction (Turnkey, Fireblocks)
│   │   ├── operations.py              # Sign-only operations
│   │   └── repository.py              # Wallet storage
│   │
│   ├── policy/                        # Spending policy engine
│   │   ├── __init__.py
│   │   ├── models.py                  # Policy dataclasses
│   │   ├── engine.py                  # Policy evaluation
│   │   ├── limits.py                  # Time-window limits
│   │   ├── merchants.py               # Allowlist/denylist
│   │   └── repository.py             # Policy storage
│   │
│   ├── mandate/                       # AP2/TAP mandate verification
│   │   ├── __init__.py
│   │   ├── models.py                  # Mandate dataclasses
│   │   ├── verifier.py                # AP2 verification
│   │   ├── tap.py                     # TAP identity verification
│   │   ├── cache.py                   # Replay protection
│   │   └── repository.py              # Mandate storage
│   │
│   └── sdk/                           # Core SDK
│       ├── python/
│       │   ├── sardis/
│       │   │   ├── agent.py           # Agent operations
│       │   │   ├── wallet.py           # Wallet operations
│       │   │   ├── policy.py           # Policy operations
│       │   │   └── mandate.py          # Mandate operations
│       └── typescript/
│           └── src/
│               ├── agent.ts
│               ├── wallet.ts
│               ├── policy.ts
│               └── mandate.ts
│
├── surfaces/                          # Output modes
│   ├── chain/                         # On-chain mode (existing)
│   │   ├── __init__.py
│   │   ├── executor.py                # Chain executor (refactored)
│   │   ├── router.py                  # Multi-chain routing
│   │   ├── gas.py                     # Gas estimation
│   │   └── confirmation.py            # Transaction confirmation
│   │
│   ├── checkout/                      # Agentic Checkout (Pivot D)
│   │   ├── __init__.py
│   │   ├── button/                    # Checkout button/widget
│   │   │   ├── __init__.py
│   │   │   ├── component.tsx           # React component
│   │   │   ├── styles.css              # Styling
│   │   │   └── hooks.ts                # React hooks
│   │   │
│   │   ├── connectors/                # PSP integrations
│   │   │   ├── __init__.py
│   │   │   ├── base.py                # Abstract connector interface
│   │   │   ├── stripe.py              # Stripe connector
│   │   │   ├── paypal.py              # PayPal connector
│   │   │   ├── coinbase.py            # Coinbase Commerce connector
│   │   │   └── circle.py              # Circle Payments connector
│   │   │
│   │   ├── orchestration/             # Policy → PSP routing
│   │   │   ├── __init__.py
│   │   │   ├── router.py              # PSP selection logic
│   │   │   ├── session.py             # Checkout session management
│   │   │   └── webhooks.py            # PSP webhook handling
│   │   │
│   │   └── merchant/                 # Merchant dashboard
│   │       ├── __init__.py
│   │       ├── api.py                 # Merchant API endpoints
│   │       ├── analytics.py            # Payment analytics
│   │       └── config.py              # PSP configuration
│   │
│   └── api/                           # Pure API mode
│       ├── __init__.py
│       ├── rest/                      # REST endpoints
│       │   ├── agents.py
│       │   ├── wallets.py
│       │   ├── policies.py
│       │   └── mandates.py
│       └── graphql/                    # GraphQL (future)
│
├── shared/                            # Shared utilities
│   ├── compliance/                    # Lightweight compliance
│   │   ├── __init__.py
│   │   ├── identity.py                # Agent identity verification (light KYC)
│   │   └── monitoring.py              # Transaction monitoring (non-regulatory)
│   │
│   ├── ledger/                        # Transaction logging
│   │   ├── __init__.py
│   │   ├── records.py                 # Ledger entry models
│   │   ├── store.py                   # Ledger storage
│   │   └── audit.py                   # Audit trail generation
│   │
│   └── webhooks/                      # Event system
│       ├── __init__.py
│       ├── events.py                  # Event types
│       ├── delivery.py                # Webhook delivery
│       └── repository.py              # Webhook storage
│
├── contracts/                         # Smart contracts (minimal)
│   ├── src/
│   │   ├── NonCustodialWallet.sol     # Non-custodial wallet contract
│   │   └── WalletFactory.sol         # Wallet factory (optional)
│   └── test/
│
├── api/                               # Main API gateway
│   ├── __init__.py
│   ├── main.py                        # FastAPI application
│   ├── middleware/                    # Auth, rate limiting, CORS
│   ├── routers/
│   │   ├── core/                      # Core OS endpoints
│   │   │   ├── agents.py
│   │   │   ├── wallets.py
│   │   │   ├── policies.py
│   │   │   └── mandates.py
│   │   ├── surfaces/
│   │   │   ├── chain.py               # On-chain endpoints
│   │   │   ├── checkout.py            # Checkout endpoints
│   │   │   └── api.py                 # API mode endpoints
│   │   └── shared/
│   │       ├── webhooks.py
│   │       └── ledger.py
│   └── config.py                      # Feature flags
│
├── dashboard/                         # React dashboard
│   └── src/
│       ├── core/                      # Core OS views
│       ├── checkout/                  # Checkout merchant views
│       └── shared/                    # Shared components
│
├── landing/                           # Marketing site
│
└── docs/                              # Documentation
    ├── ARCHITECTURE_PIVOT.md          # This file
    ├── CORE_OS.md                     # Core OS documentation
    ├── CHECKOUT_SURFACE.md            # Checkout surface docs
    └── MIGRATION.md                   # Migration guide
```

---

## Package Mapping (Old → New)

### Core OS Components

| Old Package | New Location | Notes |
|-------------|-------------|-------|
| `sardis-core/` (domain models) | `core/agent/`, `core/wallet/`, `core/policy/` | Split by domain |
| `sardis-protocol/` (AP2/TAP) | `core/mandate/` | Consolidated |
| `sardis-wallet/` (wallet ops) | `core/wallet/` | Merged with core |
| `sardis-chain/` (executor) | `surfaces/chain/` | Moved to surfaces |

### Surface Components

| Old Package | New Location | Notes |
|-------------|-------------|-------|
| `sardis-chain/` | `surfaces/chain/` | On-chain mode |
| `sardis-cards/` | `surfaces/checkout/connectors/` | Future: card connector |
| `sardis-api/` | `api/` + `surfaces/api/` | Split: gateway + API mode |

### Shared Components

| Old Package | New Location | Notes |
|-------------|-------------|-------|
| `sardis-compliance/` | `shared/compliance/` | Lightweight version |
| `sardis-ledger/` | `shared/ledger/` | Unchanged |
| `sardis-sdk-python/` | `core/sdk/python/` | Refactored |
| `sardis-sdk-js/` | `core/sdk/typescript/` | Refactored |

---

## Core OS Architecture

### Agent Identity Layer

```python
# core/agent/models.py
@dataclass
class Agent:
    agent_id: str
    name: str
    public_key: bytes  # Ed25519 or ECDSA-P256
    algorithm: str = "ed25519"
    domain: str = "sardis.network"
    created_at: datetime
    metadata: dict[str, Any] = field(default_factory=dict)
```

**Responsibilities:**
- TAP identity management
- Public key storage
- Agent metadata

### Wallet Abstraction Layer

```python
# core/wallet/models.py
@dataclass
class Wallet:
    wallet_id: str
    agent_id: str
    mpc_provider: str  # "turnkey" | "fireblocks" | "local"
    addresses: dict[str, str]  # chain -> address mapping
    created_at: datetime
    # NO balance storage (non-custodial)
```

**Key Principle:** Wallets are **sign-only**. No fund custody.

**Operations:**
- `sign_transaction()` - Sign via MPC
- `get_address()` - Get wallet address for chain
- `verify_signature()` - Verify signed transaction

### Policy Engine

```python
# core/policy/models.py
@dataclass
class SpendingPolicy:
    agent_id: str
    limit_per_tx: Decimal
    daily_limit: Decimal
    weekly_limit: Decimal
    monthly_limit: Decimal
    merchant_rules: list[MerchantRule]
    allowed_scopes: list[str]  # ["on_chain", "checkout", "api"]
```

**Evaluation Flow:**
1. Check per-transaction limit
2. Check time-window limits (daily/weekly/monthly)
3. Check merchant allowlist/denylist
4. Check scope permissions
5. Return: `APPROVED` | `DENIED` | `CHALLENGE`

### Mandate Verification

```python
# core/mandate/models.py
@dataclass
class PaymentMandate:
    mandate_id: str
    mandate_type: str  # "intent" | "cart" | "payment"
    issuer: str  # Agent ID
    subject: str  # Wallet ID
    domain: str
    payload: dict[str, Any]
    proof: dict[str, Any]  # TAP signature
    expires_at: datetime
```

**Verification Steps:**
1. Check expiration
2. Verify TAP signature
3. Check domain authorization
4. Verify replay protection
5. Validate mandate chain (intent → cart → payment)

---

## Surface: On-Chain Mode

### Architecture

```
core/policy/engine.py (policy check)
         │
         ▼
surfaces/chain/router.py (chain selection)
         │
         ▼
surfaces/chain/executor.py (transaction execution)
         │
         ▼
core/wallet/mpc.py (signing)
         │
         ▼
Blockchain (Base, Polygon, etc.)
```

**Key Changes:**
- Uses core policy engine (no duplication)
- Uses core wallet abstraction (MPC)
- Chain-specific logic isolated in `surfaces/chain/`

---

## Surface: Checkout Mode

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Merchant Website                          │
│  <AgentCheckoutButton agentId="..." amount={100} />         │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Sardis Checkout Orchestration                  │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  1. Verify Agent Identity (core/agent/)              │   │
│  │  2. Check Policy (core/policy/)                      │   │
│  │  3. Verify Mandate (core/mandate/)                  │   │
│  │  4. Select PSP (surfaces/checkout/orchestration/)   │   │
│  │  5. Create Checkout Session                         │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
        ▼                  ▼                  ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Stripe     │  │    PayPal    │  │   Coinbase   │
│   Checkout   │  │    SDK       │  │   Commerce   │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Checkout Flow

1. **Agent Authentication**
   - Merchant embeds `<AgentCheckoutButton />`
   - Agent provides TAP identity proof
   - Verify via `core/agent/identity.py`

2. **Policy Check**
   - Get agent's spending policy
   - Evaluate against transaction amount
   - Check merchant allowlist/denylist
   - Uses `core/policy/engine.py`

3. **PSP Selection**
   - Merchant preference (configured)
   - Agent policy constraints
   - PSP availability
   - Route to selected PSP

4. **Checkout Session**
   - Create session in selected PSP
   - Return checkout URL/component
   - Handle PSP webhooks

5. **Completion**
   - PSP confirms payment
   - Update ledger (shared/ledger/)
   - Emit webhook (shared/webhooks/)
   - Return success to merchant

### PSP Connector Interface

```python
# surfaces/checkout/connectors/base.py
class PSPConnector(ABC):
    @abstractmethod
    async def create_checkout_session(
        self,
        amount: Decimal,
        currency: str,
        agent_id: str,
        metadata: dict[str, Any],
    ) -> CheckoutSession:
        """Create checkout session in PSP"""
        pass
    
    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify PSP webhook signature"""
        pass
    
    @abstractmethod
    async def get_payment_status(
        self,
        session_id: str,
    ) -> PaymentStatus:
        """Get payment status from PSP"""
        pass
```

---

## Feature Flags

### Configuration

```python
# api/config.py
SARDIS_MODES = {
    "core_only": True,           # Agent Wallet OS only
    "checkout_enabled": False,   # Checkout mode (beta)
    "chain_enabled": True,       # On-chain mode
    "api_mode": True,            # Pure API mode
}

CHECKOUT_PSPS = {
    "stripe": {
        "enabled": True,
        "api_key": os.getenv("STRIPE_API_KEY"),
        "webhook_secret": os.getenv("STRIPE_WEBHOOK_SECRET"),
    },
    "paypal": {
        "enabled": False,  # Coming soon
        "client_id": os.getenv("PAYPAL_CLIENT_ID"),
    },
    "coinbase": {
        "enabled": False,  # Coming soon
    },
    "circle": {
        "enabled": False,  # Coming soon
    },
}
```

### Runtime Selection

```python
# api/routers/surfaces/checkout.py
@router.post("/checkout/create")
async def create_checkout(
    request: CheckoutRequest,
    settings: SardisSettings = Depends(get_settings),
):
    if not settings.modes.get("checkout_enabled"):
        raise HTTPException(403, "Checkout mode not enabled")
    
    # Use core OS for policy check
    policy_result = await policy_engine.evaluate(
        agent_id=request.agent_id,
        amount=request.amount,
        merchant_id=request.merchant_id,
    )
    
    if not policy_result.approved:
        raise HTTPException(403, "Policy check failed")
    
    # Route to PSP
    psp = await orchestrator.select_psp(
        merchant_id=request.merchant_id,
        agent_id=request.agent_id,
    )
    
    connector = get_psp_connector(psp)
    session = await connector.create_checkout_session(...)
    
    return session
```

---

## Migration Strategy

### Phase 1: Reorganization (Weeks 1-2)

1. **Create new directory structure**
   - Add `core/`, `surfaces/`, `shared/` directories
   - Keep existing packages for now (gradual migration)

2. **Extract core components**
   - Move domain models to `core/`
   - Move AP2/TAP logic to `core/mandate/`
   - Move policy logic to `core/policy/`

3. **Refactor chain executor**
   - Move to `surfaces/chain/`
   - Update imports to use core components

### Phase 2: Non-Custodial Refactor (Weeks 3-4)

1. **Remove custody assumptions**
   - Update wallet models (no balance storage)
   - Change wallet operations to sign-only
   - Update documentation

2. **Update API endpoints**
   - Remove balance endpoints (or make read-only from chain)
   - Update wallet creation to be non-custodial

### Phase 3: Checkout Surface (Weeks 5-8)

1. **Create checkout module**
   - Implement base connector interface
   - Implement Stripe connector (first PSP)
   - Create checkout button component

2. **Orchestration logic**
   - PSP selection algorithm
   - Checkout session management
   - Webhook handling

3. **Merchant dashboard**
   - PSP configuration UI
   - Payment analytics
   - Policy override settings

### Phase 4: Cleanup (Weeks 9-10)

1. **Remove old packages**
   - After migration complete, remove unused packages
   - Update all imports
   - Update documentation

2. **Update SDKs**
   - Refactor to match new structure
   - Update examples
   - Update documentation

---

## API Endpoints

### Core OS Endpoints

```
POST   /api/v2/agents                    # Create agent
GET    /api/v2/agents/{id}               # Get agent
PATCH  /api/v2/agents/{id}               # Update agent

POST   /api/v2/wallets                   # Create wallet (non-custodial)
GET    /api/v2/wallets/{id}              # Get wallet
GET    /api/v2/wallets/{id}/addresses    # Get wallet addresses

POST   /api/v2/policies                  # Create policy
GET    /api/v2/policies/{agent_id}       # Get policy
PATCH  /api/v2/policies/{agent_id}       # Update policy

POST   /api/v2/mandates/verify           # Verify AP2 mandate
POST   /api/v2/mandates/execute          # Execute mandate
```

### Checkout Surface Endpoints

```
POST   /api/v2/checkout/create          # Create checkout session
GET    /api/v2/checkout/{id}            # Get checkout status
POST   /api/v2/checkout/{id}/complete   # Complete checkout
POST   /api/v2/checkout/webhooks/{psp}  # PSP webhook handler

GET    /api/v2/merchants/{id}           # Get merchant
POST   /api/v2/merchants/{id}/psps      # Configure PSPs
GET    /api/v2/merchants/{id}/analytics # Payment analytics
```

### Chain Surface Endpoints

```
POST   /api/v2/chain/execute            # Execute on-chain payment
GET    /api/v2/chain/status/{tx_hash}   # Get transaction status
POST   /api/v2/chain/estimate-gas       # Estimate gas
GET    /api/v2/chain/chains             # List supported chains
```

---

## Compliance Impact

### Reduced Requirements

| Requirement | Before | After | Reduction |
|-------------|--------|-------|-----------|
| MSB Registration | Required | Not required | 100% |
| MTL Licenses | Required (multi-state) | Not required | 100% |
| Custody Insurance | Required | Not required | 100% |
| KYC/AML Program | Full program | Lightweight (agent identity) | 80% |
| Audit Scope | Critical (funds at risk) | Moderate (code quality) | 60% |

### Remaining Compliance

1. **Agent Identity Verification**
   - Light KYC for agent accounts (email, domain verification)
   - No full KYC/AML program needed

2. **Data Privacy**
   - GDPR/CCPA compliance (standard SaaS)
   - Data retention policies
   - Privacy policy

3. **PSP Compliance**
   - Handled by PSP partners (Stripe, PayPal, etc.)
   - No direct compliance burden

---

## Next Steps

1. **Review & Approve Architecture** (This document)
2. **Create Migration Plan** (Detailed week-by-week)
3. **Begin Phase 1: Reorganization**
4. **Update Strategic Analysis** (Add pivot section)

---

**Document Status:** Draft for Review  
**Last Updated:** January 11, 2026  
**Next Review:** After architecture approval

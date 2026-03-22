# Sardis Guard — MPP Policy Firewall: Reusable Asset Inventory

**For:** Synthesis Hackathon (March 22-29, 2026)
**Project:** Sardis Guard — MPP Policy Firewall
**Date Generated:** 2026-03-19
**Context:** Inventory of production-ready components that can be directly reused for a hackathon demo.

---

## TL;DR — Start Here

You have **7 production-ready subsystems** ready to plug in:

1. **Policy evaluation engine** — 12-check spending policy validation
2. **MPP policy client** — httpx transport that intercepts 402 challenges
3. **Dashboard policy builder** — React UI for policy creation and testing
4. **CLI tools** — Terminal commands for policy listing, checking, and spending analytics
5. **Policy DSL** — Structured JSON format for machine-readable policies
6. **Database backing** — Atomic policy enforcement with row-level locks
7. **Architecture docs** — Complete spending mandate specification

**Quickstart:** Copy the MPP client + policy engine from `sardis-core`, connect to your policy checker function, and you have a working firewall. The dashboard can be skinned for the demo.

---

## 1. SPENDING POLICY ENGINE (Core Decision Logic)

**Best for:** The core "should we allow this payment?" evaluation.

### SpendingPolicy Engine
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/spending_policy.py`
**Lines:** ~400 lines
**What it does:**
- 12-check evaluation pipeline for every payment
- Checks: amount limits, merchant rules, time windows, MCC codes, balance, drift, trust level
- Returns `(allowed: bool, reason: str)` or `(True, "requires_approval")`
- Supports time-window limits (daily/weekly/monthly)
- Built-in trust level presets (LOW/MEDIUM/HIGH/UNLIMITED)

**Key classes:**
- `SpendingPolicy` — the policy object itself
- `TrustLevel` enum — preset limit tiers
- `TimeWindowLimit` — rolling window enforcement
- `MerchantRule` — per-merchant/category allow/deny
- `SpendingScope` — category whitelisting

**How to use:**
```python
from sardis_v2_core import SpendingPolicy, TrustLevel

policy = SpendingPolicy(
    agent_id="agent_123",
    trust_level=TrustLevel.MEDIUM,
    limit_per_tx=Decimal("100"),
    limit_total=Decimal("1000"),
    daily_limit=Decimal("500"),
)

allowed, reason = await policy.evaluate(
    amount=Decimal("50"),
    merchant_id="openai_api",
    category="compute",
)
```

**Reusable for Guard:** YES — This is the core logic. Use it directly.

---

### Policy DSL (Domain-Specific Language)
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/policy_dsl.py`
**Lines:** ~200 lines
**What it does:**
- JSON-friendly policy definition format
- 16 supported rule types: `limit_per_tx`, `limit_total`, `scope`, `mcc_block`, `merchant_allow`, `merchant_block`, `time_window`, `approval_threshold`, `trust_level`, `goal_drift_max`, `kya_required`, `chain_allowlist`, `token_allowlist`, `destination_allowlist`, `destination_blocklist`
- Versioning with deterministic SHA256 hashing
- Validation without compilation

**Key classes:**
- `PolicyRule(type, params)` — single rule
- `PolicyDefinition` — complete policy
- `validate_definition(definition)` → `list[str]` (errors)

**Example:**
```python
definition = PolicyDefinition(
    version="1.0",
    rules=[
        PolicyRule("limit_per_tx", {"amount": "100", "currency": "USDC"}),
        PolicyRule("daily_limit", {"amount": "500"}),
        PolicyRule("merchant_block", {"mcc_codes": ["6012", "7995"]}),
    ],
    metadata={"name": "Guard Policy", "created_by": "efe"},
)

errors = validate_definition(definition)
if not errors:
    policy = definition.compile()
```

**Reusable for Guard:** YES — Use this to define policies in JSON. Wire it to your Tempo MPP client.

---

### Spending Policy Store (Atomic Enforcement)
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/spending_policy_store.py`
**Lines:** ~150 lines
**What it does:**
- Database-backed spending state with atomic limit enforcement
- Uses row-level locking (`SELECT ... FOR UPDATE`)
- Prevents races in multi-instance deployments
- Atomic `record_spend_atomic(agent_id, amount, currency)` call

**Key method:**
```python
async def record_spend_atomic(
    self,
    agent_id: str,
    amount: Decimal,
    currency: str = "USDC",
    merchant_id: str | None = None,
) -> tuple[bool, str]:
    """Atomically check limits and record a spend.

    Returns (success, reason). If success is False, no state is modified.
    Uses SELECT FOR UPDATE to prevent concurrent over-spending.
    """
```

**Reusable for Guard:** MAYBE — Depends on whether your demo uses a database. For a quick hackathon MVP, you might use in-memory tracking instead. But this is production-ready if you need durability.

---

## 2. MPP POLICY CLIENT (The Firewall)

**Best for:** The actual 402-challenge interception and policy gate.

### SardisMPPClient
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-mpp/src/sardis_mpp/client.py`
**Lines:** ~246 lines
**What it does:**
- httpx-based HTTP client that intercepts 402 (payment required) challenges
- Pluggable policy checker function
- Converts MPP challenges to Sardis policy evaluation
- Records all payment attempts (approved + denied) for audit trail
- Drop-in replacement for `httpx.AsyncClient`

**Key classes:**
- `SardisMPPClient` — main client
- `SardisPolicyTransport` — the underlying httpx transport
- `MPPPaymentRecord` — audit log entry
- `MPPPaymentDenied` — exception raised when policy blocks payment

**How to use:**
```python
from sardis_mpp import SardisMPPClient
from mpp.methods.tempo.client import TempoMethod
from mpp.methods.tempo.account import TempoAccount
from eth_account import Account

# Define your policy checker
async def sardis_policy_check(amount, merchant, payment_type, currency, network):
    # Your policy logic here
    return (True, "allowed")  # or (False, "reason")

account = TempoAccount(Account.from_key("0x..."))
tempo = TempoMethod(account=account, rpc_url="https://rpc.tempo.xyz")

client = SardisMPPClient(
    methods=[tempo],
    policy_checker=sardis_policy_check,
)

# Auto-handles 402, checks policy, pays, retries
response = await client.get("https://api.example.com/data")

# Audit trail
for record in client.payment_records:
    print(f"{record.url}: {record.policy_result} ({record.policy_reason})")
```

**Reusable for Guard:** YES — This is **exactly what you need**. It already bridges MPP to Sardis policy. Just wire your policy engine to the `policy_checker` callback.

---

## 3. POLICY GUARDS (Protocol-Specific Bridges)

### X402PolicyGuard
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/x402_policy_guard.py`
**Lines:** ~180 lines
**What it does:**
- Bridges x402 protocol challenges to the ControlPlane
- Converts x402 protocol objects to ExecutionIntents
- Two methods: `evaluate()` (simulation) and `submit()` (execution)

**Key methods:**
```python
async def evaluate(
    self,
    challenge: X402Challenge,
    agent_id: str,
    org_id: str,
    wallet_id: str,
) -> tuple[bool, str]:
    """Simulate payment through control plane. Returns (allowed, error_reason)."""

async def submit(
    self,
    challenge: X402Challenge,
    agent_id: str,
    org_id: str,
    wallet_id: str,
) -> ExecutionResult:
    """Execute payment through control plane."""
```

**Reusable for Guard:** MAYBE — This is more for on-chain x402 (EIP-402). For Tempo MPP, you might not need this. But it's a good reference for how to structure a protocol bridge.

---

### ERC8183PolicyGuard
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/erc8183_policy_guard.py`
**Lines:** ~150 lines
**What it does:**
- Similar to X402PolicyGuard, but for ERC-8183 job actions (fund/settlement)
- Bridges job actions to the ControlPlane

**Reusable for Guard:** MAYBE — Only if you're also integrating ERC-8183. Skip for pure MPP.

---

## 4. DASHBOARD COMPONENTS (UI for Policy Management)

### PolicyBuilder Component
**File:** `/Users/efebarandurmaz/sardis/dashboard/src/components/PolicyBuilder.tsx`
**Lines:** ~500 lines
**What it does:**
- React component for creating policies via natural language or templates
- Parses NL → structured policy
- Shows templates: `trusted_vendor`, `sandbox`, `enterprise`, etc.
- Real-time preview and testing
- Template selection with quick presets

**Key features:**
- Natural language input
- Template library
- Policy preview with warnings
- "Test this policy" button
- Warnings for risky rules

**Reusable for Guard:** YES — Fork this for your demo. Replace the templates with MPP-specific ones (e.g., "Allow Tempo payments only", "Block high-risk services").

---

### Policies Page
**File:** `/Users/efebarandurmaz/sardis/dashboard/src/pages/Policies.tsx`
**Lines:** ~600 lines
**What it does:**
- Full policy management UI
- List, view, create, edit, test policies
- Policy playground for simulation
- Agent filtering
- Status badges (active/inactive)

**Reusable for Guard:** YES — Use as reference for your policy management dashboard.

---

### Supporting Components
- **PolicyTemplates** (`dashboard/src/components/PolicyTemplates.tsx`) — Template card library
- **StatCard** (`dashboard/src/components/StatCard.tsx`) — Reusable stat display
- **Charts** (`dashboard/src/components/charts/SpendingChart.tsx`, etc.) — Spending visualization

**Reusable for Guard:** YES — All can be reused with minimal modification.

---

## 5. CLI TOOLS (Terminal Interface)

### Policy Commands
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-cli/src/sardis_cli/commands/policies.py`
**Lines:** ~150 lines
**Commands:**
- `sardis policies list --agent <id>` — List all policies for an agent
- `sardis policies check --agent <id> --amount <amt> --to <dest>` — Simulate a payment
- Additional subcommands for create/update/delete

**Reusable for Guard:** YES — Great for CLI demo. Add MPP-specific commands like:
```bash
sardis guard check --mpp-url "api.example.com" --method tempo --amount 50
```

---

### Spending Commands
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-cli/src/sardis_cli/commands/spending.py`
**Lines:** ~80 lines
**Commands:**
- `sardis spending summary [--period daily|weekly|monthly]` — Spending analytics
- Breaks down by agent, merchant, category
- JSON output for scripting

**Reusable for Guard:** YES — Use for demo reporting.

---

## 6. ARCHITECTURE DOCS (Reference & Spec)

### Spending Mandate Specification
**File:** `/Users/efebarandurmaz/sardis/docs/architecture/spending-mandate-spec.md`
**What it has:**
- Complete schema for spending mandates (agent authorization primitives)
- Lifecycle state machine (draft → active → suspended → revoked/expired/consumed)
- Enforcement model (5 layers: identity → mandate → policy → execution → audit)
- Use cases and examples

**Why it matters:** This spec defines the **authorization model** that your Guard uses. Understand it so you can explain the architecture to judges.

**Key concepts for Guard:**
- **Mandate** = authorization token for an agent to spend
- **Policy** = rules that govern how the mandate is used
- **Guard** = enforces policy on every payment attempt

**Reusable for Guard:** YES — Reference this in your demo explanation. Show the mandate-policy-guard stack.

---

### Payment Orchestrator
**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/orchestrator.py`
**Lines:** ~800+ lines
**What it does:**
- Central entry point for all payment execution
- 6-phase pipeline:
  1. KYA verification (fail-fast)
  2. Mandate validation (optional)
  3. Policy validation (fail-fast)
  4. Group policy (optional)
  5. Compliance (KYC/sanctions)
  6. Execution + audit

**Reusable for Guard:** MAYBE — Your Guard might be simpler for a hackathon. But this shows how policy fits into the full payment flow. Read it to understand integration points.

---

## 7. DEDUP STORE (Idempotency & Replay Protection)

**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/dedup_store.py`
**Lines:** ~150 lines
**What it does:**
- In-memory and Redis-backed deduplication
- Prevents double-pay race conditions
- Two implementations:
  - `MemoryDedupStore` (dev/testing)
  - `RedisDedupStore` (production)

**Methods:**
```python
async def check(self, mandate_id: str) -> Any | None:
    """Check if we've already processed this. Returns stored result or None."""

async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
    """Atomic check + set. Prevents races."""
```

**Reusable for Guard:** YES — Use to prevent duplicate MPP payments if your client retries.

---

## 8. TRUST INFRASTRUCTURE (Agent Identity)

**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/trust_infrastructure.py`
**Lines:** ~400 lines
**What it does:**
- Agent identity verification (TAP protocol)
- Code hash attestation
- Trust scoring
- KYA levels (NONE/BASIC/VERIFIED/ATTESTED)

**Reusable for Guard:** MAYBE — If you want to verify agent identity before allowing MPP payments. For a quick demo, you might skip this.

---

## 9. PLUGINS SYSTEM (Extensibility)

**File:** `/Users/efebarandurmaz/sardis/packages/sardis-core/src/sardis_v2_core/plugins/`
**What it does:**
- Pluggable policy engines
- `PolicyPlugin` base class with `async evaluate(transaction)` method
- Built-in: `CustomPolicyPlugin` (rules-based)
- Health check interface

**Reusable for Guard:** YES — If you want to support custom policy logic. But for MVP, just use `SpendingPolicy` directly.

---

## 10. DATABASE SCHEMA REFERENCES

**File:** `packages/sardis-core/src/sardis_v2_core/` (search for `*_repository*.py` or `migrations/`)
**Tables you might need:**
- `spending_policies` — policy definitions per agent
- `mandates` — authorization records
- `mandate_state_transitions` — audit log
- `transactions` — payment records with policy_id, mandate_id
- `ledger_anchors` — immutable audit trail

**For Guard:** You might not need a database for a hackathon MVP. But know these tables exist if you want to wire your demo into the full system.

---

## LANDING PAGE COMPONENTS

**Note:** Landing page components are **not available** (`landing/src/` is empty or minimal). But the dashboard components can be styled for a landing page.

**Option:** Fork the PolicyBuilder component and skin it as a "Try the Guard" demo on your landing page.

---

## RECOMMENDED ARCHITECTURE FOR GUARD DEMO

```
┌─────────────────────────────────────────────────────────────────┐
│  Frontend (React)                                               │
│  ┌─────────────────────────────────────────────────────────────┤
│  │  PolicyBuilder component (fork from dashboard)               │
│  │  - Natural language policy input                             │
│  │  - Template selection (Tempo, Stripe, Lightning)             │
│  │  - Real-time preview                                         │
│  │                                                              │
│  │  PolicyTest component (custom)                               │
│  │  - Simulated MPP challenge input                             │
│  │  - "Should I pay?" result                                    │
│  │  - Audit trail visualization                                 │
│  └─────────────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────────────┤
│  Backend (Python)                                               │
│  ┌─────────────────────────────────────────────────────────────┤
│  │  FastAPI routes                                              │
│  │  - POST /guard/policies (create)                             │
│  │  - GET /guard/policies/{id}                                  │
│  │  - POST /guard/check (simulate payment)                      │
│  │                                                              │
│  │  SardisMPPClient (from sardis-mpp)                           │
│  │  - httpx transport with policy interception                  │
│  │  - Callback to your policy checker                           │
│  │                                                              │
│  │  SpendingPolicy (from sardis-core)                           │
│  │  - 12-check evaluation pipeline                              │
│  │  - Per-tx, daily, weekly, monthly limits                     │
│  │                                                              │
│  │  Policy DSL (from sardis-core)                               │
│  │  - JSON policy compilation                                   │
│  │  - Deterministic versioning                                  │
│  │                                                              │
│  │  Dedup + audit logging                                       │
│  └─────────────────────────────────────────────────────────────┤
├─────────────────────────────────────────────────────────────────┤
│  Optional: Database (PostgreSQL)                                │
│  ┌─────────────────────────────────────────────────────────────┤
│  │  spending_policies — policy definitions                      │
│  │  payment_records — audit trail                               │
│  │  mandates — authorization records (if using full system)     │
│  └─────────────────────────────────────────────────────────────┤
└─────────────────────────────────────────────────────────────────┘
```

---

## QUICK START CHECKLIST

For a working demo by end of day:

- [ ] Fork the **SardisMPPClient** → wrap your policy checker
- [ ] Fork the **SpendingPolicy** → configure limits
- [ ] Fork the **PolicyBuilder** component → add MPP templates
- [ ] Create a simple API wrapper → `/guard/check` endpoint
- [ ] Wire up the dashboard to your backend
- [ ] Add CLI commands → `sardis guard check --mpp-url ...`
- [ ] Create sample policies (conservative defaults)
- [ ] Document the 5-layer enforcement model

**Estimated effort:** 4-6 hours for a working MVP.

---

## FILE PATHS QUICK REFERENCE

```
Policy Engine Core:
  sardis-core/src/sardis_v2_core/spending_policy.py
  sardis-core/src/sardis_v2_core/policy_dsl.py
  sardis-core/src/sardis_v2_core/spending_policy_store.py

MPP Client:
  sardis-mpp/src/sardis_mpp/client.py

Policy Guards:
  sardis-core/src/sardis_v2_core/x402_policy_guard.py
  sardis-core/src/sardis_v2_core/erc8183_policy_guard.py

Dashboard UI:
  dashboard/src/components/PolicyBuilder.tsx
  dashboard/src/pages/Policies.tsx
  dashboard/src/components/PolicyTemplates.tsx
  dashboard/src/components/charts/SpendingChart.tsx

CLI:
  sardis-cli/src/sardis_cli/commands/policies.py
  sardis-cli/src/sardis_cli/commands/spending.py

Docs:
  docs/architecture/spending-mandate-spec.md
  docs/plans/ (various design docs)
```

---

## NOTES FOR JUDGES

When presenting, emphasize:

1. **You're not building from scratch** — Sardis already has a production policy engine. You're adapting it to secure MPP.
2. **The full stack is covered** — From on-chain (SPT, Tempo) to off-chain (policies, audit), this is a complete solution.
3. **Real-world constraints** — Policies handle 12 different checks, not just amount limits. Merchants, time windows, compliance, agent drift, etc.
4. **Auditability** — Every payment is recorded with the policy result and mandate ID. Immutable ledger on-chain.

---

**Good luck with the demo!** 🚀

# Technical Interview Guide

## Sardis -- Founding Engineer Interview

---

## Interview Structure

| Section | Duration | Focus |
|---------|----------|-------|
| 1. Async Python & FastAPI | 15 min | Core backend competency |
| 2. Smart Contracts & Blockchain | 15 min | On-chain infrastructure |
| 3. Payment Systems | 15 min | Fintech domain knowledge |
| 4. MPC & Key Management | 10 min | Cryptography fundamentals |
| 5. System Design | 20 min | Architecture and distributed systems |
| Wrap-up | 5 min | Candidate questions, next steps |

**Total: 80 minutes**

---

## Scoring Rubric

Each question is scored 1-4:

| Score | Label | Criteria |
|-------|-------|----------|
| 1 | **Below Bar** | Cannot answer; fundamental misunderstanding |
| 2 | **Approaching** | Partial answer; understands concept but misses key details |
| 3 | **Meets Bar** | Solid answer; demonstrates working knowledge and practical experience |
| 4 | **Exceeds** | Exceptional answer; shows deep expertise, considers edge cases, references real-world experience |

**Hiring threshold:** Average score >= 2.5 across all sections, no section average below 2.0.

---

## Section 1: Async Python & FastAPI (15 min)

### Q1.1: Concurrency Model

**Question:** Explain the difference between `asyncio.gather()`, `asyncio.create_task()`, and `asyncio.to_thread()`. When would you use each in a FastAPI application?

**Expected Answer (3):**
- `gather()` runs multiple coroutines concurrently and waits for all to complete -- use for parallel I/O (e.g., fetching data from multiple providers simultaneously)
- `create_task()` schedules a coroutine without waiting -- use for fire-and-forget work (e.g., sending a webhook notification after responding to the client)
- `to_thread()` runs synchronous blocking code in a thread pool -- use for wrapping blocking SDKs (e.g., Stripe SDK calls that use `requests` internally)
- Mentions that `to_thread` is critical for not blocking the event loop

**Exceeds (4):** Discusses structured concurrency with `TaskGroup` (Python 3.11+), cancellation semantics, exception propagation in `gather(return_exceptions=True)`, and why FastAPI's dependency injection is async-aware.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q1.2: Connection Pool Management

**Question:** You have a FastAPI application that connects to PostgreSQL (via asyncpg) and Redis (via aioredis). How do you manage connection pool lifecycle? What happens if you do not manage it properly?

**Expected Answer (3):**
- Use FastAPI lifespan events (`@asynccontextmanager` lifespan) to create pools on startup and close on shutdown
- asyncpg: `asyncpg.create_pool()` with `min_size`/`max_size` configuration
- Failure to close pools leads to connection leaks, exhausting database connection limits
- Connection pools should be shared across requests via app state or dependency injection

**Exceeds (4):** Discusses pool sizing strategy (connections = CPU cores * 2 + effective_spindle_count), health checks, connection recycling, and how Neon serverless PostgreSQL has different pooling characteristics (PgBouncer, connection limits per branch).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q1.3: Dependency Injection for Testing

**Question:** Sardis uses FastAPI's dependency injection to swap providers in tests. How would you design a DI system where the `CardProvider` can be either `StripeIssuingProvider` or a `MockProvider` depending on environment?

**Expected Answer (3):**
- Define `CardProvider` as an abstract base class (ABC)
- Use `Depends()` with a factory function that checks environment/config
- Override dependencies in tests with `app.dependency_overrides[get_card_provider] = lambda: MockProvider()`
- Mentions that DI enables testing without real Stripe API calls

**Exceeds (4):** Discusses making `chain_executor` private in DI so only the orchestrator can access it (a pattern Sardis already uses), the importance of fail-closed defaults, and how to handle provider-specific initialization errors gracefully.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q1.4: Idempotency

**Question:** An AI agent sends a payment request. Due to a network timeout, the agent retries. How do you ensure the payment is not executed twice?

**Expected Answer (3):**
- Client sends an `idempotency_key` header (UUID generated client-side)
- Server stores the idempotency key with a unique constraint in the database
- On retry, server detects the duplicate key and returns the original response
- Key should be scoped to the operation (not globally unique across all operations)

**Exceeds (4):** Discusses `SELECT ... FOR UPDATE NOWAIT` for race condition prevention, database-level unique constraints vs. application-level dedup (Redis), TTL on idempotency keys, and how Sardis's checkout system uses both `idempotency_key` unique constraints and `SELECT FOR UPDATE NOWAIT` to prevent double-pay.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

## Section 2: Smart Contracts & Blockchain (15 min)

### Q2.1: ERC-20 Approval Flow

**Question:** Walk me through the ERC-20 `approve` + `transferFrom` pattern. Why is it necessary? What is the security risk, and how do modern standards address it?

**Expected Answer (3):**
- `approve(spender, amount)` grants allowance; `transferFrom(from, to, amount)` uses that allowance
- Necessary because smart contracts cannot pull tokens without prior authorization
- Security risk: unlimited approvals (type(uint256).max) can be exploited if the spender contract is compromised
- Modern mitigation: EIP-2612 `permit` (gasless approvals via signature), time-limited approvals

**Exceeds (4):** Discusses the front-running vulnerability in `approve` (race condition between old and new approval), `increaseAllowance`/`decreaseAllowance` pattern, and how Safe accounts handle token approvals via delegated module execution.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q2.2: Safe Smart Accounts

**Question:** Sardis uses Safe Smart Accounts (v1.4.1) as the wallet infrastructure. What is a Safe account, how does it differ from an EOA, and what capabilities does it provide for agent wallets?

**Expected Answer (3):**
- Safe is a multi-signature smart contract wallet (contract account vs. EOA)
- Supports n-of-m signature schemes (e.g., 2-of-3 signers)
- Supports modules (extensions that can execute transactions with custom logic)
- Key advantage for agents: programmable spending rules, key rotation without changing address, batched transactions

**Exceeds (4):** Discusses Zodiac Roles module (pre-deployed, allows scoped permissions for agent signers), the Guard interface (pre-transaction checks), ERC-4337 compatibility for account abstraction, and why Safe is preferred over custom wallet contracts (audited, battle-tested, pre-deployed on all EVM chains).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q2.3: Gas Optimization

**Question:** An agent needs to make a USDC payment on Base. How would you minimize gas costs? What is a paymaster and how does Circle's paymaster work?

**Expected Answer (3):**
- Base L2 has lower gas than Ethereum L1 (~$0.01 vs. ~$1-5 per transaction)
- Gas optimization: batch transactions, use EIP-2930 access lists, avoid storage writes when possible
- Paymaster: a contract that pays gas on behalf of the user (ERC-4337)
- Circle Paymaster: pays gas in USDC instead of ETH (user does not need ETH)

**Exceeds (4):** Discusses the two paymaster models (Circle permissionless: USDC gas; Pimlico: sponsor model), EIP-4844 blob transactions for further L2 cost reduction, gas estimation strategies, and the tradeoff between pre-funding ETH vs. paymaster fees.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q2.4: On-Chain Audit Trail

**Question:** Sardis maintains an append-only ledger for all transactions. Would you implement this on-chain, off-chain, or hybrid? What are the tradeoffs?

**Expected Answer (3):**
- **On-chain:** Immutable, transparent, but expensive and slow for high-volume operations
- **Off-chain:** Fast and cheap, but requires trust in the operator
- **Hybrid:** Log critical anchors (hashes, Merkle roots) on-chain, store full details off-chain
- Sardis uses a hybrid approach: full audit trail in PostgreSQL, with periodic hash anchoring on-chain

**Exceeds (4):** Discusses SardisLedgerAnchor contract (batch Merkle root anchoring), the tradeoff between anchoring frequency and cost, how to verify off-chain records against on-chain roots, and the role of the ledger in dispute resolution with Circle's RefundProtocol.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

## Section 3: Payment Systems (15 min)

### Q3.1: Card Authorization Flow

**Question:** A card is swiped at a merchant. Walk me through the authorization flow from swipe to approval, and explain where Sardis can intervene in real-time.

**Expected Answer (3):**
- Merchant POS -> Acquirer -> Card Network (Visa/Mastercard) -> Issuer -> Authorization response
- Stripe Issuing sends `issuing_authorization.request` webhook to Sardis
- Sardis has < 3 seconds to respond with approve/decline
- Sardis checks: spending policy engine (natural language rules), card limits (per-tx, daily, monthly), merchant category restrictions

**Exceeds (4):** Discusses the difference between authorization and settlement (capture), partial authorizations, MCC codes and how Sardis's policy engine uses them, the two-stage authorization check in StripeIssuingProvider (policy evaluator first, then card.can_authorize), and how merchant-locked cards enforce single-merchant restrictions.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q3.2: Settlement and Reconciliation

**Question:** An agent pays a merchant with USDC. The merchant wants USD in their bank account. Describe the end-to-end settlement flow and the reconciliation challenges.

**Expected Answer (3):**
- USDC transfer on-chain from agent wallet to merchant/escrow address
- Off-ramp: USDC to USD via Bridge (quote -> deposit -> ACH/wire delivery)
- Reconciliation: match on-chain transaction hash with off-ramp transaction ID and bank deposit
- Challenges: timing mismatches (on-chain instant, ACH 1-2 days), FX rate changes, partial settlements

**Exceeds (4):** Discusses the Postgres reconciliation queue, velocity limits on off-ramp (daily/weekly/monthly caps), how checkout sessions track `idempotency_key` + `client_secret` for end-to-end dedup, and the role of SSE streaming for real-time payment status updates to the checkout UI.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q3.3: Multi-Rail Routing

**Question:** Sardis needs to send $500 USD from an agent to a recipient's bank account. We have Bridge (ACH, wire) and Lightspark Grid (RTP, FedNow, ACH). How would you decide which provider and rail to use?

**Expected Answer (3):**
- Consider urgency: instant (RTP/FedNow via Grid) vs. standard (ACH via Bridge)
- Consider cost: RTP ~$0.50-2.00, ACH ~$0.10-0.50
- Consider amount: small amounts favor Grid instant, large amounts may favor Bridge wire
- Fallback logic: try primary provider, fallback to secondary if primary fails or rate-limits

**Exceeds (4):** Describes a routing table approach (currency + urgency -> provider + rail), health-aware routing (circuit breaker per provider), cost optimization with configurable preferences, and how Sardis already implements priority routing (EUR -> Striga SEPA, USD instant -> Grid, USD standard -> Bridge ACH).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q3.4: Webhook Security

**Question:** You receive a webhook from Stripe saying a card transaction was authorized. How do you verify it is legitimate and not a replay attack?

**Expected Answer (3):**
- Verify HMAC-SHA256 signature using the webhook secret (`stripe.Webhook.construct_event()`)
- Stripe includes a timestamp in the signature; reject events older than 5 minutes
- Use the event ID for idempotent processing (do not process the same event twice)
- Store processed event IDs to prevent reprocessing

**Exceeds (4):** Discusses the Sardis webhook delivery tracking table (`event_id` + delivery status for dedup), the difference between signature verification and replay protection, how to handle webhook delivery retries gracefully, and the requirement that webhook signatures are mandatory in all non-dev environments (enforced by TDD remediation).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

## Section 4: MPC & Key Management (10 min)

### Q4.1: MPC Custody Model

**Question:** Sardis uses Turnkey for MPC (Multi-Party Computation) custody. What is MPC in the context of key management, and why is it preferable to storing private keys?

**Expected Answer (3):**
- MPC splits a private key into shares held by multiple parties
- No single party ever possesses the full key -- signing requires cooperation
- Advantages: no single point of compromise, key never exists in one place
- Turnkey provides the MPC infrastructure; Sardis never has access to full private keys

**Exceeds (4):** Discusses threshold signatures (t-of-n), the difference between MPC and multisig (MPC produces a standard ECDSA signature vs. multisig requires multiple on-chain signatures), key rotation without changing the wallet address, and how this architecture enables "non-custodial" designation (important for regulatory positioning).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

### Q4.2: API Key Security

**Question:** How would you design the API key system for Sardis? An API key grants access to wallet operations -- how do you store, validate, and revoke keys?

**Expected Answer (3):**
- Store hashed keys (SHA-256) in the database, not plaintext
- Show the key once at creation; never display again
- Validate by hashing the incoming key and comparing against stored hash
- Support key rotation: create new key, deprecation period, revoke old key
- Scope keys by permission level (read-only, payment, admin)

**Exceeds (4):** Discusses key prefixing conventions (`sk_live_`, `sk_test_` for environment detection), rate limiting per key, audit logging of key usage, HMAC-signed API requests for additional security (as used by Bridge and Striga), and how to implement key revocation that takes effect immediately across distributed API instances.

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

## Section 5: System Design (20 min)

### Q5.1: Design Exercise

**Question:** Design the payment orchestration pipeline for Sardis. An AI agent calls `sardis.pay(to="merchant", amount=50, token="USDC")`. Walk me through every step from API call to settled payment, including all the checks, state transitions, and failure modes.

**Evaluation Criteria:**

**Input Processing (Score: ___/4)**
- API request validation (Pydantic models)
- Authentication and authorization (API key -> org -> wallet ownership)
- Idempotency key check
- Rate limiting

**Policy Evaluation (Score: ___/4)**
- Natural language policy parsing and evaluation
- Amount limits (per-tx, daily, monthly)
- Merchant/category restrictions
- Time-of-day rules
- AGIT (Agent Guardrail Integrity Test) fail-closed check
- KYA (Know Your Agent) identity verification

**Execution Pipeline (Score: ___/4)**
- Chain selection (which chain has sufficient balance?)
- Gas estimation and paymaster selection
- Transaction construction (ERC-20 transfer, Safe module execution)
- MPC signing via Turnkey
- Transaction submission and confirmation waiting
- Retry logic for failed transactions

**Post-Execution (Score: ___/4)**
- Ledger entry creation (append-only audit trail)
- Balance update
- Webhook notification to the agent operator
- Analytics/metrics emission
- State machine transition: PENDING -> APPROVED -> SUBMITTED -> CONFIRMED -> SETTLED

**Failure Modes (Score: ___/4)**
- Policy denial -> return reason, no state change
- Insufficient balance -> return error, no state change
- Chain congestion -> retry with gas escalation
- MPC signing failure -> circuit breaker, alert
- Transaction revert -> rollback, refund if applicable
- Webhook delivery failure -> retry queue with exponential backoff

| Component | Score (1-4) | Notes |
|-----------|-------------|-------|
| Input Processing | | |
| Policy Evaluation | | |
| Execution Pipeline | | |
| Post-Execution | | |
| Failure Modes | | |

---

### Q5.2: Scaling Question

**Question:** The system currently handles 100 payments per minute. A major partner integration will bring 10,000 payments per minute. What breaks first, and how do you prepare?

**Expected Answer (3):**
- Database connections: PostgreSQL connection pool exhaustion (fix: PgBouncer, connection pooling, read replicas)
- RPC rate limits: blockchain node rate limiting (fix: multiple RPC providers with fallback, dedicated nodes)
- Redis: rate limiter and dedup store under load (fix: Redis Cluster, key partitioning)
- Webhook delivery: outbound webhook queue backup (fix: async queue with workers, backpressure)

**Exceeds (4):** Discusses horizontal API scaling (stateless FastAPI instances behind load balancer), database partitioning strategies (shard by org_id or wallet_id), batch transaction submission (multicall for on-chain operations), queue-based architecture for non-critical path operations, and specific Neon serverless PostgreSQL scaling characteristics (autoscaling compute, connection limits per branch).

| Score | Notes |
|-------|-------|
| 1 2 3 4 | |

---

## Pairing Session Options (Round 3)

Choose one based on candidate strength:

### Option A: Build a Webhook Handler (Backend Focus)
Implement a Stripe Issuing authorization webhook handler that:
1. Verifies the webhook signature
2. Looks up the card's spending policy
3. Evaluates the policy against the authorization
4. Returns approve/decline within 3 seconds
5. Includes tests

### Option B: Implement a Policy Rule (Full-Stack)
Add a new policy rule type (e.g., "time-of-day restriction") that:
1. Extends the policy DSL
2. Adds API endpoints for CRUD
3. Integrates with the policy evaluation engine
4. Includes tests

### Option C: Smart Contract Test (Solidity Focus)
Write Foundry tests for an ERC-20 spending limit contract:
1. Set a daily limit
2. Verify transactions within limit succeed
3. Verify transactions exceeding limit revert
4. Test limit reset at day boundary

---

## Overall Assessment

| Section | Avg Score | Notes |
|---------|-----------|-------|
| 1. Async Python & FastAPI | /4 | |
| 2. Smart Contracts & Blockchain | /4 | |
| 3. Payment Systems | /4 | |
| 4. MPC & Key Management | /4 | |
| 5. System Design | /4 | |
| **Overall Average** | **/4** | |

### Decision

- [ ] **Strong Hire** -- Exceeds bar in most areas, exceptional depth
- [ ] **Hire** -- Meets bar across the board, strong in key areas
- [ ] **Lean Hire** -- Meets bar in most areas, compensating strengths
- [ ] **No Hire** -- Below bar in critical areas
- [ ] **Strong No Hire** -- Fundamental gaps in required skills

### Red Flags

- Cannot explain async/await fundamentals
- Has never worked with databases in production
- Uncomfortable with ambiguity ("what exactly should I build?")
- No curiosity about the agent economy or fintech
- Over-engineers simple problems

### Green Flags

- Has built payment/fintech systems before
- Contributes to open-source projects
- Asks thoughtful questions about the business
- Proposes simpler solutions first, then discusses scaling
- Shows genuine excitement about the problem space

### Interviewer Notes

**Strengths:**

**Concerns:**

**Overall Recommendation:**

---

**Interviewer:** ______________________________
**Date:** ______________________________
**Candidate:** ______________________________

# Sardis Architecture

## Overview

Sardis is a programmable stablecoin payment network designed specifically for AI agents. This document describes the system architecture, component design, data flows, and scaling strategies.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              SARDIS PLATFORM                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐                 │
│  │   AI Agent 1   │  │   AI Agent 2   │  │   AI Agent N   │                 │
│  │  (Shopping)    │  │  (Data Buyer)  │  │  (Automation)  │                 │
│  └───────┬────────┘  └───────┬────────┘  └───────┬────────┘                 │
│          │                   │                   │                          │
│          └───────────────────┼───────────────────┘                          │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         SARDIS SDK                                     │  │
│  │   • SardisClient        • Wallet Operations     • Payment Methods     │  │
│  │   • Event Handlers      • Risk Checks           • Transaction History │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         API GATEWAY                                    │  │
│  │   • Rate Limiting       • Authentication        • Request Validation  │  │
│  │   • API Versioning      • CORS                  • Logging             │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│          ┌───────────────────┼───────────────────┐                          │
│          ▼                   ▼                   ▼                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                     │
│  │    Agent     │   │   Payment    │   │   Webhook    │                     │
│  │   Service    │   │   Service    │   │   Service    │                     │
│  └──────────────┘   └──────────────┘   └──────────────┘                     │
│          │                   │                   │                          │
│          ▼                   ▼                   ▼                          │
│  ┌──────────────┐   ┌──────────────┐   ┌──────────────┐                     │
│  │    Wallet    │   │     Risk     │   │     Fee      │                     │
│  │   Service    │   │   Service    │   │   Service    │                     │
│  └──────────────┘   └──────────────┘   └──────────────┘                     │
│          │                   │                   │                          │
│          └───────────────────┼───────────────────┘                          │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                         LEDGER LAYER                                   │  │
│  │   • Transaction Processing   • Balance Management   • Audit Trail     │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                              │                                               │
│                              ▼                                               │
│  ┌───────────────────────────────────────────────────────────────────────┐  │
│  │                      CHAIN ABSTRACTION LAYER                           │  │
│  │                                                                        │  │
│  │   ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌─────────┐               │  │
│  │   │  Base   │   │Ethereum │   │ Polygon │   │ Solana  │               │  │
│  │   │ (EVM)   │   │ (EVM)   │   │ (EVM)   │   │ (SVM)   │               │  │
│  │   └─────────┘   └─────────┘   └─────────┘   └─────────┘               │  │
│  │                                                                        │  │
│  │   Tokens: USDC, USDT, PYUSD, EURC                                      │  │
│  └───────────────────────────────────────────────────────────────────────┘  │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. API Gateway

The API Gateway is the entry point for all client requests.

**Responsibilities:**
- Request authentication and authorization
- Rate limiting (per-agent and global)
- Request/response logging
- API versioning
- CORS handling
- Request validation

**Technology:** FastAPI with custom middleware

### 2. Agent Service

Manages AI agent registration and lifecycle.

```python
class AgentService:
    """Core agent management operations."""
    
    def register_agent(name, owner_id, limits) -> Agent
    def get_agent(agent_id) -> Agent
    def update_agent(agent_id, updates) -> Agent
    def deactivate_agent(agent_id) -> bool
```

**Data Model:**
```
Agent
├── agent_id (unique identifier)
├── name
├── owner_id
├── wallet_id (linked wallet)
├── is_active
├── created_at
└── metadata
```

### 3. Wallet Service

Manages wallets with multi-token support and spending limits.

**Features:**
- Multi-token balance tracking (USDC, USDT, PYUSD, EURC)
- Per-transaction and total spending limits
- Virtual card abstraction
- Balance queries and updates

**Data Model:**
```
Wallet
├── wallet_id
├── agent_id
├── balances (per token)
├── limits
│   ├── limit_per_tx
│   ├── limit_total
│   └── spent_total
├── virtual_card
│   ├── card_id
│   └── masked_number
└── is_active
```

### 4. Payment Service

Orchestrates payment execution with full validation.

**Payment Flow:**
```
1. Validate Request
   ├── Check agent exists
   ├── Check recipient exists
   └── Validate amount > 0

2. Risk Assessment
   ├── Calculate risk score
   ├── Check velocity limits
   └── Verify service authorization

3. Balance & Limit Check
   ├── Sufficient balance?
   ├── Within per-tx limit?
   └── Within total limit?

4. Execute Transfer
   ├── Debit source wallet
   ├── Credit destination wallet
   ├── Collect fee to pool
   └── Record transaction

5. Post-Processing
   ├── Update risk profile
   ├── Emit webhook events
   └── Return result
```

### 5. Risk Service

Provides fraud prevention and risk scoring.

**Risk Factors:**
| Factor | Weight | Description |
|--------|--------|-------------|
| High Velocity | 20 | Too many transactions per hour |
| Large Amount | 15 | Transaction exceeds threshold |
| New Wallet | 10 | Wallet less than 24 hours old |
| Failed Attempts | 25 | High failure rate |
| Pattern Anomaly | 15 | Unusual spending pattern |
| Unauthorized Service | 10 | Paying non-authorized service |

**Risk Levels:**
- **Low (0-24):** Normal operations
- **Medium (25-49):** Monitor closely
- **High (50-74):** Require review
- **Critical (75-100):** Block transaction

### 6. Webhook Service

Real-time event notifications to external systems.

**Supported Events:**
- `payment.completed` - Payment successfully processed
- `payment.failed` - Payment failed
- `wallet.created` - New wallet created
- `wallet.funded` - Wallet received funds
- `limit.exceeded` - Spending limit exceeded
- `risk.alert` - High risk transaction detected

**Delivery Guarantees:**
- At-least-once delivery
- Exponential backoff retry (1s, 5s, 30s)
- HMAC-SHA256 signature verification
- 10 second timeout per delivery

### 7. Chain Abstraction Layer

Unified interface for multi-chain operations.

**Supported Chains:**
| Chain | Type | Finality | Avg Fee |
|-------|------|----------|---------|
| Base | EVM (L2) | ~2s | ~$0.001 |
| Ethereum | EVM | ~3m | ~$1-5 |
| Polygon | EVM | ~5s | ~$0.01 |
| Solana | SVM | ~1s | ~$0.0001 |

**Chain Router:**
```python
class ChainRouter:
    """Selects optimal chain for transactions."""
    
    def find_optimal_route(
        amount: Decimal,
        token: TokenType,
        preferred_chain: Optional[ChainType] = None,
        max_fee: Optional[Decimal] = None
    ) -> OptimalRoute
```

## Data Flow

### Payment Request Flow

```
┌──────────┐    ┌─────────┐    ┌──────────┐    ┌────────┐    ┌────────┐
│  Agent   │    │   API   │    │ Payment  │    │ Ledger │    │ Chain  │
│  (SDK)   │    │ Gateway │    │ Service  │    │        │    │        │
└────┬─────┘    └────┬────┘    └────┬─────┘    └───┬────┘    └───┬────┘
     │               │              │              │             │
     │  POST /pay    │              │              │             │
     │──────────────>│              │              │             │
     │               │  validate    │              │             │
     │               │─────────────>│              │             │
     │               │              │  risk check  │             │
     │               │              │──────────────>              │
     │               │              │              │             │
     │               │              │  transfer    │             │
     │               │              │──────────────>│             │
     │               │              │              │  on-chain   │
     │               │              │              │────────────>│
     │               │              │              │<────────────│
     │               │              │<─────────────│             │
     │               │<─────────────│              │             │
     │<──────────────│              │              │             │
     │               │              │              │             │
```

## Scaling Strategy

### Target Scale: 1M+ Agents

#### 1. Horizontal Scaling

```
                    Load Balancer
                         │
         ┌───────────────┼───────────────┐
         │               │               │
    ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
    │  API    │    │  API    │    │  API    │
    │ Node 1  │    │ Node 2  │    │ Node N  │
    └────┬────┘    └────┬────┘    └────┬────┘
         │               │               │
         └───────────────┼───────────────┘
                         │
                    Redis Cluster
                    (Session/Cache)
                         │
                    PostgreSQL
                    (Primary + Replicas)
```

#### 2. Database Sharding

**Sharding Strategy:**
- Shard by `agent_id` (consistent hashing)
- 64 logical shards mapped to physical nodes
- Read replicas per shard for query scaling

**Schema per Shard:**
```sql
-- agents_shard_XX
CREATE TABLE agents (
    agent_id VARCHAR(32) PRIMARY KEY,
    -- ...
);

-- wallets_shard_XX  
CREATE TABLE wallets (
    wallet_id VARCHAR(32) PRIMARY KEY,
    agent_id VARCHAR(32) REFERENCES agents,
    -- ...
);

-- transactions_shard_XX
CREATE TABLE transactions (
    tx_id VARCHAR(40) PRIMARY KEY,
    from_wallet VARCHAR(32),
    to_wallet VARCHAR(32),
    -- ...
);
```

#### 3. Caching Strategy

**Redis Cache Layers:**
```
L1: Local In-Memory (per node)
├── Hot wallet balances
├── Agent session data
└── TTL: 1 minute

L2: Redis Cluster
├── Wallet state
├── Transaction status
├── Risk profiles
└── TTL: 5 minutes

L3: Database
└── Source of truth
```

#### 4. Message Queue Architecture

```
┌────────────┐    ┌────────────────┐    ┌────────────────┐
│   API      │───>│  Transaction   │───>│  Settlement    │
│  Servers   │    │    Queue       │    │   Workers      │
└────────────┘    └────────────────┘    └────────────────┘
                          │
                          ▼
                  ┌────────────────┐    ┌────────────────┐
                  │   Webhook      │───>│   Webhook      │
                  │    Queue       │    │   Workers      │
                  └────────────────┘    └────────────────┘
```

**Queue Configuration:**
- Transaction Queue: Kafka with exactly-once semantics
- Webhook Queue: RabbitMQ with retry/DLQ
- Chain Settlement: Dedicated workers per chain

#### 5. Performance Targets

| Metric | Target | Strategy |
|--------|--------|----------|
| API Latency (p99) | <100ms | Edge caching, connection pooling |
| Payment Processing | <500ms | Async settlement, optimistic updates |
| Throughput | 10K TPS | Horizontal scaling, sharding |
| Availability | 99.99% | Multi-region, failover |

## Security Architecture

### Authentication & Authorization

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   API Key   │───>│   JWT       │───>│  RBAC       │
│   Verify    │    │   Validate  │    │   Check     │
└─────────────┘    └─────────────┘    └─────────────┘
```

**Roles:**
- `agent:read` - View agent/wallet info
- `agent:write` - Create/update agents
- `payment:execute` - Make payments
- `admin:*` - Full access

### Key Management

```
┌─────────────────────────────────────────────────────┐
│                  KEY MANAGEMENT                      │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────────┐    ┌──────────────┐              │
│  │   HSM        │    │   KMS        │              │
│  │ (Hardware)   │───>│ (AWS/GCP)    │              │
│  └──────────────┘    └──────────────┘              │
│          │                   │                      │
│          ▼                   ▼                      │
│  ┌──────────────────────────────────────────────┐  │
│  │              MPC Signing Service              │  │
│  │   • Threshold signatures (2-of-3)            │  │
│  │   • No single point of compromise            │  │
│  │   • Audit logging                            │  │
│  └──────────────────────────────────────────────┘  │
│                                                      │
└─────────────────────────────────────────────────────┘
```

## Deployment Architecture

### Production Environment

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS / GCP                                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Region: US-East-1                  Region: EU-West-1           │
│  ┌─────────────────────┐           ┌─────────────────────┐     │
│  │  ┌───────────────┐  │           │  ┌───────────────┐  │     │
│  │  │ API Cluster   │  │           │  │ API Cluster   │  │     │
│  │  │ (EKS/GKE)     │  │           │  │ (EKS/GKE)     │  │     │
│  │  └───────────────┘  │           │  └───────────────┘  │     │
│  │                      │           │                      │     │
│  │  ┌───────────────┐  │           │  ┌───────────────┐  │     │
│  │  │ PostgreSQL    │  │◄─────────►│  │ PostgreSQL    │  │     │
│  │  │ (Primary)     │  │  Repl.    │  │ (Replica)     │  │     │
│  │  └───────────────┘  │           │  └───────────────┘  │     │
│  │                      │           │                      │     │
│  │  ┌───────────────┐  │           │  ┌───────────────┐  │     │
│  │  │ Redis Cluster │  │◄─────────►│  │ Redis Cluster │  │     │
│  │  └───────────────┘  │           │  └───────────────┘  │     │
│  └─────────────────────┘           └─────────────────────┘     │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    Global Services                        │   │
│  │  • CloudFront/CloudFlare CDN                             │   │
│  │  • Route53/Cloud DNS (Geo-routing)                       │   │
│  │  • Secrets Manager                                        │   │
│  │  • CloudWatch/Stackdriver Monitoring                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Monitoring & Observability

### Metrics

**Business Metrics:**
- Total transaction volume
- Active agents count
- Payment success rate
- Average transaction value

**Technical Metrics:**
- API latency (p50, p95, p99)
- Error rates by endpoint
- Database query times
- Queue depths

**Infrastructure Metrics:**
- CPU/Memory utilization
- Network I/O
- Disk usage
- Container health

### Alerting

| Alert | Threshold | Severity |
|-------|-----------|----------|
| API Error Rate | >1% | Critical |
| Latency p99 | >500ms | Warning |
| Payment Failures | >5% | Critical |
| Queue Backlog | >1000 | Warning |
| Database Connections | >80% | Warning |

## Disaster Recovery

### Backup Strategy

- **Database:** Point-in-time recovery, 30-day retention
- **Transaction Logs:** Immutable storage, 7-year retention
- **Configuration:** GitOps, version controlled

### Recovery Targets

| Metric | Target |
|--------|--------|
| RTO (Recovery Time Objective) | <15 minutes |
| RPO (Recovery Point Objective) | <1 minute |

### Failover Process

1. Health check detects primary failure
2. DNS failover to secondary region (automatic, <30s)
3. Promote read replica to primary
4. Resume operations
5. Sync and rebuild original primary

## Future Considerations

### Phase 3 Enhancements

1. **Real-time Cross-chain Bridges**
   - Atomic swaps between chains
   - Liquidity aggregation

2. **Advanced Analytics**
   - Spending pattern analysis
   - Predictive risk scoring
   - Agent behavior insights

3. **Programmable Payments**
   - Scheduled payments
   - Conditional payments (escrow)
   - Multi-signature requirements

4. **Marketplace Protocol**
   - Agent-to-agent payment rails
   - Service discovery
   - Reputation system


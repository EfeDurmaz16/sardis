# Sardis Implementation Plan - Phase 5: Production Readiness

## Overview

This document outlines the implementation plan for Phase 5, focusing on making Sardis production-ready. We've successfully completed Phases 1-4 (Core Infrastructure, Blockchain Integration, AI Agent Logic, and Frontend Dashboard). Now we focus on stability, features, and real-world deployment.

---

## Current Status Summary

### ✅ What's Working
- AI agents with natural language understanding (OpenAI GPT-4o)
- Multi-token wallets (USDC, USDT, PYUSD, EURC)
- PostgreSQL database with full persistence
- React dashboard with chat interface
- Spending limits and validation
- Multi-chain support (Base, Ethereum, Polygon, Solana)
- System wallets (treasury, fees, settlement)

### ⚠️ Known Issues
1. **No Conversation Memory**: AI agents are stateless, can't remember previous messages
2. **Simulated Blockchain**: On-chain settlements not actually executing
3. **No Product Catalog**: Merchants exist but have no products
4. **Incomplete Auth**: API keys exist but not enforced everywhere
5. **No Webhooks**: Event system defined but not delivering
6. **Missing Features**: Receipts, notifications, analytics

---

## Phase 5: Production Readiness

### Priority 1: Core Stability (2-3 weeks)

#### 1.1 Conversation Memory for AI Agents
**Goal**: Enable agents to remember conversation history

**Tasks**:
- [ ] Add `conversations` table to database
  ```sql
  CREATE TABLE conversations (
      conversation_id VARCHAR(40) PRIMARY KEY,
      agent_id VARCHAR(32) REFERENCES agents,
      messages JSONB,
      created_at TIMESTAMP,
      updated_at TIMESTAMP
  );
  ```
- [ ] Update `AgentService` to store/retrieve message history
- [ ] Modify chat interface to send `conversation_id`
- [ ] Add conversation management endpoints
  - `GET /agents/{id}/conversations`
  - `GET /conversations/{id}/messages`
  - `DELETE /conversations/{id}`
- [ ] Update AI prompt to include conversation history
- [ ] Add conversation expiry (auto-delete after 24h)

**Files to Modify**:
- `sardis_core/database/models.py` - Add DBConversation model
- `sardis_core/services/agent_service.py` - Add memory management
- `sardis_core/api/routes/agents.py` - Add conversation endpoints
- `dashboard/src/components/ChatInterface.tsx` - Track conversation_id

**Estimated Time**: 3-4 days

---

#### 1.2 Proper Authentication & Authorization
**Goal**: Secure all endpoints with proper auth

**Tasks**:
- [ ] Implement API key middleware for all routes
- [ ] Add role-based access control (RBAC)
  - `admin` - Full access
  - `developer` - Create agents, make payments
  - `readonly` - View only
- [ ] Add API key scopes
  - `agents:read`, `agents:write`
  - `payments:execute`
  - `webhooks:manage`
- [ ] Implement rate limiting per API key
  - 100 requests/minute for standard keys
  - 1000 requests/minute for premium keys
- [ ] Add JWT authentication for dashboard
- [ ] Implement session management

**Files to Modify**:
- `sardis_core/api/auth.py` - Enhanced auth logic
- `sardis_core/api/dependencies.py` - Add auth dependencies
- `sardis_core/database/models.py` - Add permissions to DBApiKey
- All route files - Add auth dependencies

**Estimated Time**: 4-5 days

---

#### 1.3 Error Handling & Logging
**Goal**: Production-grade error handling and observability

**Tasks**:
- [ ] Implement structured logging (JSON format)
- [ ] Add request ID tracking
- [ ] Create custom exception classes
  - `InsufficientBalanceError`
  - `SpendingLimitExceededError`
  - `AgentNotFoundError`
  - `InvalidTransactionError`
- [ ] Add error response standardization
  ```json
  {
    "error": {
      "code": "INSUFFICIENT_BALANCE",
      "message": "Wallet balance too low",
      "details": {...},
      "request_id": "req_abc123"
    }
  }
  ```
- [ ] Implement Sentry integration for error tracking
- [ ] Add performance monitoring (OpenTelemetry)
- [ ] Create health check endpoints
  - `/health` - Basic health
  - `/health/db` - Database connectivity
  - `/health/redis` - Cache connectivity

**Files to Create/Modify**:
- `sardis_core/exceptions.py` - Custom exceptions
- `sardis_core/logging.py` - Logging configuration
- `sardis_core/middleware/` - Request tracking middleware
- `sardis_core/api/routes/health.py` - Health checks

**Estimated Time**: 3-4 days

---

### Priority 2: Essential Features (3-4 weeks)

#### 2.1 Merchant Product Catalog
**Goal**: Enable merchants to list products for agents to purchase

**Tasks**:
- [ ] Create product database schema
  ```sql
  CREATE TABLE products (
      product_id VARCHAR(40) PRIMARY KEY,
      merchant_id VARCHAR(32) REFERENCES agents,
      name VARCHAR(200),
      description TEXT,
      price NUMERIC(20, 6),
      currency VARCHAR(10),
      category VARCHAR(50),
      is_available BOOLEAN,
      metadata JSONB,
      created_at TIMESTAMP
  );
  ```
- [ ] Add product management API
  - `POST /merchants/{id}/products` - Add product
  - `GET /merchants/{id}/products` - List products
  - `PUT /products/{id}` - Update product
  - `DELETE /products/{id}` - Remove product
- [ ] Create product catalog page in dashboard
- [ ] Add product search and filtering
- [ ] Update AI agent to browse products
  - New tool: `browse_products(merchant_id, category)`
  - New tool: `search_products(query)`
- [ ] Add shopping cart functionality

**Files to Create/Modify**:
- `sardis_core/database/models.py` - DBProduct model
- `sardis_core/models/product.py` - Product Pydantic model
- `sardis_core/api/routes/catalog.py` - Product endpoints
- `sardis_core/services/catalog_service.py` - Product logic
- `dashboard/src/pages/Products.tsx` - Product management UI

**Estimated Time**: 5-6 days

---

#### 2.2 Transaction Receipts & Notifications
**Goal**: Provide transaction confirmations and notifications

**Tasks**:
- [ ] Generate PDF receipts for transactions
- [ ] Add email notification system
  - Transaction completed
  - Payment failed
  - Spending limit warning
  - Low balance alert
- [ ] Create notification preferences
- [ ] Add in-app notification center
- [ ] Implement SMS notifications (Twilio)
- [ ] Add receipt download in dashboard

**Files to Create/Modify**:
- `sardis_core/services/notification_service.py` - Notification logic
- `sardis_core/services/receipt_service.py` - PDF generation
- `sardis_core/api/routes/notifications.py` - Notification endpoints
- `dashboard/src/components/NotificationCenter.tsx` - UI component

**Estimated Time**: 4-5 days

---

#### 2.3 Agent Performance Analytics
**Goal**: Provide insights into agent spending and behavior

**Tasks**:
- [ ] Create analytics database tables
  ```sql
  CREATE TABLE agent_analytics (
      agent_id VARCHAR(32),
      date DATE,
      total_transactions INT,
      total_spent NUMERIC(20, 6),
      avg_transaction NUMERIC(20, 6),
      top_merchant VARCHAR(32),
      PRIMARY KEY (agent_id, date)
  );
  ```
- [ ] Build analytics aggregation service
- [ ] Create analytics dashboard page
  - Spending trends (daily, weekly, monthly)
  - Top merchants
  - Transaction success rate
  - Average transaction size
- [ ] Add export functionality (CSV, JSON)
- [ ] Implement real-time metrics

**Files to Create/Modify**:
- `sardis_core/services/analytics_service.py` - Analytics logic
- `sardis_core/api/routes/analytics.py` - Analytics endpoints
- `dashboard/src/pages/Analytics.tsx` - Analytics UI

**Estimated Time**: 5-6 days

---

### Priority 3: Blockchain Integration (2-3 weeks)

#### 3.1 Real On-Chain Settlements
**Goal**: Execute actual blockchain transactions

**Tasks**:
- [ ] Integrate MPC wallet provider (Fireblocks, Turnkey, or Coinbase)
- [ ] Implement wallet creation on-chain
- [ ] Add transaction signing and broadcasting
- [ ] Implement transaction confirmation polling
- [ ] Add gas estimation and optimization
- [ ] Handle chain reorganizations
- [ ] Add transaction retry logic
- [ ] Implement nonce management

**Files to Modify**:
- `sardis_core/chains/base.py` - Real Web3 calls
- `sardis_core/chains/ethereum.py` - Ethereum integration
- `sardis_core/chains/polygon.py` - Polygon integration
- `sardis_core/chains/solana.py` - Solana integration
- `sardis_core/services/blockchain_service.py` - Enhanced logic

**Estimated Time**: 7-10 days

---

#### 3.2 Gas Optimization & Fee Management
**Goal**: Minimize transaction costs

**Tasks**:
- [ ] Implement EIP-1559 gas estimation
- [ ] Add gas price oracles
- [ ] Implement transaction batching
- [ ] Add fee prediction API
- [ ] Create gas refund mechanism
- [ ] Implement priority fee management

**Files to Create/Modify**:
- `sardis_core/services/gas_service.py` - Gas optimization
- `sardis_core/api/routes/fees.py` - Fee estimation endpoints

**Estimated Time**: 4-5 days

---

### Priority 4: Deployment & DevOps (1-2 weeks)

#### 4.1 Production Deployment
**Goal**: Deploy to production environment

**Tasks**:
- [ ] Set up AWS/GCP infrastructure
  - EKS/GKE for API servers
  - RDS/Cloud SQL for PostgreSQL
  - ElastiCache/Memorystore for Redis
  - S3/GCS for file storage
- [ ] Configure CI/CD pipeline (GitHub Actions)
- [ ] Set up monitoring (Datadog, New Relic)
- [ ] Configure CDN (CloudFlare)
- [ ] Implement blue-green deployment
- [ ] Add database migration strategy
- [ ] Set up backup and disaster recovery

**Estimated Time**: 5-7 days

---

#### 4.2 Documentation & Testing
**Goal**: Comprehensive docs and test coverage

**Tasks**:
- [ ] Write API integration guide
- [ ] Create video tutorials
- [ ] Add Postman collection
- [ ] Increase test coverage to 80%+
- [ ] Add integration tests
- [ ] Add load testing (Locust, k6)
- [ ] Create runbook for operations

**Estimated Time**: 4-5 days

---

## Timeline Summary

| Phase | Duration | Deliverables |
|-------|----------|--------------|
| **Priority 1: Core Stability** | 2-3 weeks | Conversation memory, Auth, Logging |
| **Priority 2: Features** | 3-4 weeks | Product catalog, Notifications, Analytics |
| **Priority 3: Blockchain** | 2-3 weeks | Real on-chain settlements, Gas optimization |
| **Priority 4: Deployment** | 1-2 weeks | Production infrastructure, CI/CD |
| **Total** | **8-12 weeks** | Production-ready Sardis platform |

---

## Success Metrics

### Technical Metrics
- [ ] API latency p99 < 200ms
- [ ] 99.9% uptime
- [ ] Test coverage > 80%
- [ ] Zero critical security vulnerabilities
- [ ] Database query time < 50ms

### Business Metrics
- [ ] 100+ active agents
- [ ] 1000+ transactions processed
- [ ] < 1% transaction failure rate
- [ ] 10+ integrated merchants

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| OpenAI API downtime | High | Implement fallback to simpler models |
| Blockchain congestion | Medium | Multi-chain routing, gas optimization |
| Database scaling | High | Implement sharding, read replicas |
| Security breach | Critical | Regular audits, bug bounty program |

---

## Next Steps

1. **Week 1-2**: Implement conversation memory and authentication
2. **Week 3-4**: Add product catalog and notifications
3. **Week 5-6**: Enable real blockchain settlements
4. **Week 7-8**: Deploy to production and monitor

---

## Questions & Decisions Needed

1. **MPC Provider**: Which provider to use? (Fireblocks, Turnkey, Coinbase)
2. **Cloud Provider**: AWS or GCP?
3. **Monitoring**: Datadog, New Relic, or self-hosted?
4. **Email Provider**: SendGrid, AWS SES, or Postmark?
5. **Payment for OpenAI**: How to handle API costs at scale?

---

## Resources Required

- **Engineering**: 2-3 full-time developers
- **DevOps**: 1 part-time engineer
- **Design**: 1 part-time designer (for analytics UI)
- **Budget**: 
  - Cloud infrastructure: $500-1000/month
  - OpenAI API: $200-500/month
  - Monitoring tools: $100-200/month
  - MPC provider: $1000-2000/month

---

**Last Updated**: December 2, 2025
**Status**: Phase 5 Planning Complete, Ready to Execute

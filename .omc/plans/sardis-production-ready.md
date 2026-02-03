# Sardis Production Readiness Implementation Plan

## Overview

This plan addresses all gaps identified in the comprehensive audit to make Sardis production-ready. It focuses on:
- 2 MISSING critical features (Approvals backend, Background jobs)
- 12 PARTIAL implementations requiring completion
- Tech debt cleanup (TODO/FIXME, failing tests, deprecations)

Tasks are organized into parallelizable groups for swarm execution, with dependencies clearly marked.

---

## Task Groups (for Swarm Parallelization)

### Group 1: Critical Missing Infrastructure (BLOCKERS - Must Complete First)

These are foundational - other features depend on them.

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T001 | Create approvals database schema with migration | `packages/sardis-api/migrations/004_approvals.sql` | `feat(db): add approvals table schema with indexes` | 1h |
| T002 | Implement ApprovalRepository for PostgreSQL CRUD | `packages/sardis-core/src/sardis_v2_core/approval_repository.py` | `feat(core): add ApprovalRepository for approval persistence` | 1.5h |
| T003 | Create ApprovalService with business logic | `packages/sardis-core/src/sardis_v2_core/approval_service.py` | `feat(core): add ApprovalService with create/approve/deny/expire` | 1.5h |
| T004 | Add approvals API router with REST endpoints | `packages/sardis-api/src/sardis_api/routers/approvals.py` | `feat(api): add /api/v2/approvals endpoints` | 1.5h |
| T005 | Wire approvals router into FastAPI app | `packages/sardis-api/src/sardis_api/main.py` | `feat(api): integrate approvals router with dependencies` | 0.5h |
| T006 | Add approval notification via webhooks | `packages/sardis-core/src/sardis_v2_core/approval_notifier.py` | `feat(core): add ApprovalNotifier for webhook notifications` | 1h |
| T007 | Create background jobs module with APScheduler | `packages/sardis-core/src/sardis_v2_core/scheduler.py` | `feat(core): add APScheduler-based job scheduler` | 1.5h |
| T008 | Implement spending limit reset job (daily/weekly/monthly) | `packages/sardis-core/src/sardis_v2_core/jobs/spending_reset.py` | `feat(jobs): add spending limit reset scheduled job` | 1h |
| T009 | Implement hold expiration job | `packages/sardis-core/src/sardis_v2_core/jobs/hold_expiry.py` | `feat(jobs): add hold expiration cleanup job` | 1h |
| T010 | Implement approval expiration job | `packages/sardis-core/src/sardis_v2_core/jobs/approval_expiry.py` | `feat(jobs): add approval request expiration job` | 0.5h |
| T011 | Add scheduler startup to FastAPI lifespan | `packages/sardis-api/src/sardis_api/main.py` | `feat(api): start scheduler on app startup` | 0.5h |

---

## DETAILED SPECIFICATIONS (Critic Feedback Addressed)

### 1. Approvals Database Schema (T001)

**Reference**: MCP TypeScript interface at `packages/sardis-mcp-server/src/tools/approvals.ts` lines 28-41

```sql
-- Migration: 004_approvals.sql

-- Create enum types
CREATE TYPE approval_status AS ENUM ('pending', 'approved', 'denied', 'expired', 'cancelled');
CREATE TYPE approval_urgency AS ENUM ('low', 'medium', 'high');

-- Create approvals table
CREATE TABLE IF NOT EXISTS approvals (
    -- Primary key
    id VARCHAR(64) PRIMARY KEY,  -- Format: appr_<timestamp_base36>

    -- Core fields (from MCP TypeScript interface)
    action VARCHAR(64) NOT NULL,           -- 'payment', 'create_card', etc.
    vendor VARCHAR(255),                    -- Vendor name for payments
    amount DECIMAL(18, 6),                  -- Payment amount (nullable for non-payment actions)
    purpose TEXT,                           -- Purpose description
    reason TEXT,                            -- Reason for approval request
    card_limit DECIMAL(18, 6),             -- Card limit (for create_card action)

    -- Status tracking
    status approval_status NOT NULL DEFAULT 'pending',
    urgency approval_urgency NOT NULL DEFAULT 'medium',

    -- Actor tracking
    requested_by VARCHAR(64) NOT NULL,     -- Agent ID who requested
    reviewed_by VARCHAR(255),               -- Email/ID of human reviewer

    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,        -- When approval request expires
    reviewed_at TIMESTAMPTZ,                -- When decision was made

    -- Foreign keys (soft references - IDs stored, not enforced)
    agent_id VARCHAR(64),                   -- FK to agents table
    wallet_id VARCHAR(64),                  -- FK to wallets table
    organization_id VARCHAR(64),            -- FK to organizations table (future)

    -- Metadata
    metadata JSONB DEFAULT '{}'::jsonb      -- Extensible metadata
);

-- Required indexes for performance
CREATE INDEX idx_approvals_status ON approvals(status);
CREATE INDEX idx_approvals_agent_id ON approvals(agent_id);
CREATE INDEX idx_approvals_wallet_id ON approvals(wallet_id);
CREATE INDEX idx_approvals_organization_id ON approvals(organization_id);
CREATE INDEX idx_approvals_requested_by ON approvals(requested_by);
CREATE INDEX idx_approvals_expires_at ON approvals(expires_at) WHERE status = 'pending';
CREATE INDEX idx_approvals_created_at ON approvals(created_at DESC);

-- Composite index for common query patterns
CREATE INDEX idx_approvals_status_urgency ON approvals(status, urgency) WHERE status = 'pending';

-- Comments for documentation
COMMENT ON TABLE approvals IS 'Human approval requests for agent actions exceeding policy limits';
COMMENT ON COLUMN approvals.id IS 'Unique approval ID, format: appr_<base36_timestamp>';
COMMENT ON COLUMN approvals.action IS 'Type of action: payment, create_card, transfer, etc.';
COMMENT ON COLUMN approvals.requested_by IS 'Agent ID that initiated the approval request';
COMMENT ON COLUMN approvals.reviewed_by IS 'Human reviewer email or admin ID';
```

**Python Dataclass** (for `approval_repository.py`):

```python
@dataclass
class Approval:
    id: str
    action: str
    status: Literal['pending', 'approved', 'denied', 'expired', 'cancelled']
    urgency: Literal['low', 'medium', 'high']
    requested_by: str
    created_at: datetime
    expires_at: datetime
    vendor: Optional[str] = None
    amount: Optional[Decimal] = None
    purpose: Optional[str] = None
    reason: Optional[str] = None
    card_limit: Optional[Decimal] = None
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    agent_id: Optional[str] = None
    wallet_id: Optional[str] = None
    organization_id: Optional[str] = None
    metadata: dict = field(default_factory=dict)
```

---

### 2. Bridge Integration Clarification (T019)

**DECISION: Remove T019 as duplicate.**

The codebase already has a complete `BridgeOfframpProvider` implementation at:
- `packages/sardis-cards/src/sardis_cards/offramp.py` (lines 220-408)

**Existing Implementation Features:**
- `BridgeOfframpProvider` class with full API integration
- HMAC signature authentication (`_sign_request` method)
- Quote retrieval (`get_quote`)
- Transfer execution (`execute_offramp`)
- Transaction status polling (`get_transaction_status`)
- Deposit address generation (`get_deposit_address`)
- Sandbox/production environment support

**Already Wired in `main.py`** (lines 621-638):
```python
# Initialize OfframpService (used by ramp + cards)
bridge_api_key = os.getenv("BRIDGE_API_KEY")
bridge_api_secret = os.getenv("BRIDGE_API_SECRET")
if bridge_api_key and bridge_api_secret:
    from sardis_cards.offramp import BridgeOfframpProvider, OfframpService
    bridge_provider = BridgeOfframpProvider(...)
    offramp_service = OfframpService(provider=bridge_provider)
```

**No new `sardis-ramp/bridge_provider.py` needed.** The existing `sardis-cards` package already provides Bridge integration. Task T019 is **REMOVED** from this plan.

---

### 3. Scheduler Integration Pattern (T007, T011)

**APScheduler Registration Pattern** for `packages/sardis-core/src/sardis_v2_core/scheduler.py`:

```python
"""Background job scheduler for Sardis."""
from __future__ import annotations

import logging
from typing import Callable, Optional, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor

logger = logging.getLogger("sardis.scheduler")


class SardisScheduler:
    """APScheduler wrapper for Sardis background jobs."""

    def __init__(
        self,
        database_url: Optional[str] = None,
        timezone: str = "UTC",
    ):
        # Job store for persistence (survives restarts)
        jobstores = {}
        if database_url:
            jobstores["default"] = SQLAlchemyJobStore(url=database_url)

        # Async executor for FastAPI compatibility
        executors = {
            "default": AsyncIOExecutor(),
        }

        job_defaults = {
            "coalesce": True,      # Combine missed runs into one
            "max_instances": 1,    # Only one instance per job
            "misfire_grace_time": 60 * 5,  # 5 min grace period
        }

        self._scheduler = AsyncIOScheduler(
            jobstores=jobstores,
            executors=executors,
            job_defaults=job_defaults,
            timezone=timezone,
        )
        self._started = False

    def add_cron_job(
        self,
        func: Callable,
        job_id: str,
        *,
        hour: int = 0,
        minute: int = 0,
        day_of_week: str = "*",
        **kwargs: Any,
    ) -> None:
        """Register a cron-style job."""
        self._scheduler.add_job(
            func,
            "cron",
            id=job_id,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"Registered cron job: {job_id}")

    def add_interval_job(
        self,
        func: Callable,
        job_id: str,
        *,
        seconds: int = 300,
        **kwargs: Any,
    ) -> None:
        """Register an interval job."""
        self._scheduler.add_job(
            func,
            "interval",
            id=job_id,
            seconds=seconds,
            replace_existing=True,
            **kwargs,
        )
        logger.info(f"Registered interval job: {job_id} (every {seconds}s)")

    async def start(self) -> None:
        """Start the scheduler."""
        if not self._started:
            self._scheduler.start()
            self._started = True
            logger.info("Scheduler started")

    async def shutdown(self, wait: bool = True) -> None:
        """Stop the scheduler gracefully."""
        if self._started:
            self._scheduler.shutdown(wait=wait)
            self._started = False
            logger.info("Scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._started and self._scheduler.running


# Singleton instance
_scheduler: Optional[SardisScheduler] = None


def get_scheduler() -> SardisScheduler:
    """Get the global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler not initialized. Call init_scheduler() first.")
    return _scheduler


def init_scheduler(database_url: Optional[str] = None) -> SardisScheduler:
    """Initialize the global scheduler."""
    global _scheduler
    _scheduler = SardisScheduler(database_url=database_url)
    return _scheduler
```

**FastAPI Lifespan Integration** for `main.py` (T011):

```python
# Add to imports at top of main.py
from sardis_v2_core.scheduler import init_scheduler, get_scheduler
from sardis_v2_core.jobs.spending_reset import reset_spending_limits
from sardis_v2_core.jobs.hold_expiry import expire_holds
from sardis_v2_core.jobs.approval_expiry import expire_approvals

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # ... existing startup code ...

    # Initialize and start scheduler
    database_url = os.getenv("DATABASE_URL", "")
    scheduler = init_scheduler(
        database_url=database_url if database_url.startswith("postgresql") else None
    )

    # Register jobs
    scheduler.add_cron_job(
        reset_spending_limits,
        job_id="spending_reset_daily",
        hour=0, minute=0,  # Midnight UTC
    )
    scheduler.add_interval_job(
        expire_holds,
        job_id="hold_expiry_check",
        seconds=300,  # Every 5 minutes
    )
    scheduler.add_interval_job(
        expire_approvals,
        job_id="approval_expiry_check",
        seconds=60,  # Every minute
    )

    await scheduler.start()
    app.state.scheduler = scheduler
    logger.info("Background scheduler started with jobs registered")

    yield  # App runs here

    # Shutdown
    logger.info("Shutting down Sardis API...")
    await scheduler.shutdown(wait=True)
    # ... existing shutdown code ...
```

**Job State Persistence**: When `database_url` is provided to `init_scheduler()`, APScheduler uses `SQLAlchemyJobStore` which persists job state (last run time, next run time) to a `apscheduler_jobs` table. This survives restarts and prevents duplicate executions.

---

### 4. MCC Data Source Specification (T025-T026)

**Data Source**: Static JSON file embedded in the package.

**File**: `packages/sardis-core/src/sardis_v2_core/data/mcc_codes.json`

**Structure**:
```json
{
  "version": "2024.1",
  "last_updated": "2024-01-15",
  "codes": {
    "7995": {
      "description": "Gambling - Betting/Casino",
      "category": "gambling",
      "risk_level": "high",
      "default_blocked": true
    },
    "5912": {
      "description": "Drug Stores and Pharmacies",
      "category": "healthcare",
      "risk_level": "low",
      "default_blocked": false
    },
    "5813": {
      "description": "Bars, Cocktail Lounges, Taverns",
      "category": "alcohol",
      "risk_level": "medium",
      "default_blocked": false
    }
  },
  "categories": {
    "gambling": {
      "name": "Gambling & Betting",
      "codes": ["7995", "7994", "7993"],
      "default_policy": "block"
    },
    "alcohol": {
      "name": "Alcohol & Tobacco",
      "codes": ["5813", "5921", "5993"],
      "default_policy": "warn"
    },
    "healthcare": {
      "name": "Healthcare & Pharmacy",
      "codes": ["5912", "8011", "8021"],
      "default_policy": "allow"
    }
  }
}
```

**MCC Service Implementation** (`packages/sardis-core/src/sardis_v2_core/mcc_service.py`):

```python
"""Merchant Category Code (MCC) lookup service."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

# Load MCC data from embedded JSON
_MCC_DATA_PATH = Path(__file__).parent / "data" / "mcc_codes.json"
_MCC_DATA: Optional[dict] = None


@dataclass
class MCCInfo:
    code: str
    description: str
    category: str
    risk_level: str  # 'low', 'medium', 'high'
    default_blocked: bool


def _load_mcc_data() -> dict:
    """Load MCC data from JSON file (cached)."""
    global _MCC_DATA
    if _MCC_DATA is None:
        with open(_MCC_DATA_PATH) as f:
            _MCC_DATA = json.load(f)
    return _MCC_DATA


def get_mcc_info(mcc_code: str) -> Optional[MCCInfo]:
    """Look up MCC code information."""
    data = _load_mcc_data()
    code_info = data["codes"].get(mcc_code)
    if not code_info:
        return None
    return MCCInfo(
        code=mcc_code,
        description=code_info["description"],
        category=code_info["category"],
        risk_level=code_info["risk_level"],
        default_blocked=code_info["default_blocked"],
    )


def get_category_codes(category: str) -> list[str]:
    """Get all MCC codes in a category."""
    data = _load_mcc_data()
    cat_info = data["categories"].get(category)
    return cat_info["codes"] if cat_info else []


def is_blocked_category(mcc_code: str, blocked_categories: list[str]) -> bool:
    """Check if MCC code belongs to a blocked category."""
    info = get_mcc_info(mcc_code)
    if not info:
        return False  # Unknown codes allowed by default
    return info.category in blocked_categories
```

**Integration with `spending_policy.py`** (T026):

```python
# In spending_policy.py, add to policy check:
from .mcc_service import get_mcc_info, is_blocked_category

def check_mcc_policy(
    mcc_code: Optional[str],
    policy: SpendingPolicy,
) -> PolicyResult:
    """Check if MCC code is allowed by policy."""
    if not mcc_code:
        return PolicyResult(allowed=True)

    # Check explicit blocked categories in policy
    blocked_categories = policy.blocked_merchant_categories or []
    if is_blocked_category(mcc_code, blocked_categories):
        return PolicyResult(
            allowed=False,
            reason=f"Merchant category blocked: {mcc_code}",
        )

    # Check default high-risk blocks
    mcc_info = get_mcc_info(mcc_code)
    if mcc_info and mcc_info.default_blocked:
        return PolicyResult(
            allowed=False,
            reason=f"High-risk merchant category: {mcc_info.description}",
        )

    return PolicyResult(allowed=True)
```

---

### 5. Wallet Freeze Persistence Story (T029-T031)

**Decision**: Add `is_frozen` field to both PostgreSQL `wallets` table AND the `Wallet` Pydantic model.

**Database Migration** (`packages/sardis-api/migrations/005_wallet_freeze.sql`):

```sql
-- Add freeze columns to wallets table
ALTER TABLE wallets
ADD COLUMN IF NOT EXISTS is_frozen BOOLEAN NOT NULL DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS frozen_at TIMESTAMPTZ,
ADD COLUMN IF NOT EXISTS frozen_by VARCHAR(255),
ADD COLUMN IF NOT EXISTS freeze_reason TEXT;

-- Index for finding frozen wallets
CREATE INDEX IF NOT EXISTS idx_wallets_is_frozen ON wallets(is_frozen) WHERE is_frozen = TRUE;

COMMENT ON COLUMN wallets.is_frozen IS 'Whether wallet is frozen (blocks all transactions)';
COMMENT ON COLUMN wallets.frozen_at IS 'Timestamp when wallet was frozen';
COMMENT ON COLUMN wallets.frozen_by IS 'Admin/system that froze the wallet';
COMMENT ON COLUMN wallets.freeze_reason IS 'Reason for freezing (compliance, suspicious activity, etc.)';
```

**Wallet Dataclass Update** (`packages/sardis-core/src/sardis_v2_core/wallets.py`):

```python
class Wallet(BaseModel):
    """Non-custodial wallet for AI agents."""
    # ... existing fields ...

    # Freeze state (NEW)
    is_frozen: bool = False
    frozen_at: Optional[datetime] = None
    frozen_by: Optional[str] = None
    freeze_reason: Optional[str] = None

    def freeze(self, by: str, reason: str) -> None:
        """Freeze the wallet."""
        self.is_frozen = True
        self.frozen_at = datetime.now(timezone.utc)
        self.frozen_by = by
        self.freeze_reason = reason
        self.updated_at = datetime.now(timezone.utc)

    def unfreeze(self) -> None:
        """Unfreeze the wallet."""
        self.is_frozen = False
        self.frozen_at = None
        self.frozen_by = None
        self.freeze_reason = None
        self.updated_at = datetime.now(timezone.utc)
```

**WalletRepository Update** (`wallet_repository.py`):

```python
async def freeze(
    self,
    wallet_id: str,
    frozen_by: str,
    reason: str,
) -> Optional[Wallet]:
    """Freeze a wallet (blocks all transactions)."""
    wallet = self._wallets.get(wallet_id)
    if not wallet:
        return None
    wallet.freeze(by=frozen_by, reason=reason)
    return wallet

async def unfreeze(self, wallet_id: str) -> Optional[Wallet]:
    """Unfreeze a wallet."""
    wallet = self._wallets.get(wallet_id)
    if not wallet:
        return None
    wallet.unfreeze()
    return wallet

async def get_frozen_wallets(self) -> List[Wallet]:
    """Get all frozen wallets."""
    return [w for w in self._wallets.values() if w.is_frozen]
```

**TTLDict Cache Integration**:

The `WalletRepository` uses `TTLDict` for in-memory caching. The freeze state is stored on the `Wallet` object itself, so:
- When a wallet is loaded from PostgreSQL, `is_frozen` is populated
- When `freeze()` is called, it updates the in-memory `Wallet` object
- The next database sync writes the frozen state to PostgreSQL
- TTL expiry evicts the wallet from cache, but freeze state persists in DB

**For PostgreSQL-backed repository**, add to SQL queries:

```python
# In PostgresWalletRepository.freeze():
async def freeze(self, wallet_id: str, frozen_by: str, reason: str) -> Optional[Wallet]:
    async with self._pool.acquire() as conn:
        result = await conn.fetchrow(
            """
            UPDATE wallets
            SET is_frozen = TRUE,
                frozen_at = NOW(),
                frozen_by = $2,
                freeze_reason = $3,
                updated_at = NOW()
            WHERE wallet_id = $1
            RETURNING *
            """,
            wallet_id, frozen_by, reason
        )
        if result:
            # Invalidate cache
            self._cache.pop(wallet_id, None)
            return self._row_to_wallet(result)
        return None
```

---

## Updated Task Groups

### Group 2: Database & Infrastructure (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T012 | Set up Alembic for migration management | `packages/sardis-api/alembic.ini`, `packages/sardis-api/alembic/env.py` | `feat(db): add Alembic migration framework` | 1h |
| T013 | Convert existing SQL migrations to Alembic versions | `packages/sardis-api/alembic/versions/*.py` | `refactor(db): convert SQL migrations to Alembic` | 1.5h |
| T014 | Add database audit triggers for critical tables | `packages/sardis-api/migrations/005_audit_triggers.sql` | `feat(db): add audit triggers for transactions/wallets/approvals` | 1h |
| T015 | Add distributed locks to Redis cache | `packages/sardis-core/src/sardis_v2_core/cache.py` | `feat(cache): add distributed lock support with Redis SETNX` | 1h |
| T016 | Add cache metrics collection (hit/miss/latency) | `packages/sardis-core/src/sardis_v2_core/cache.py` | `feat(cache): add cache metrics for monitoring` | 1h |
| T017 | Add tests for cache.py | `tests/test_cache.py` | `test(cache): add unit tests for CacheService` | 1h |
| T018 | Add tests for redis_nonce_manager.py | `tests/test_redis_nonce_manager.py` | `test(chain): add unit tests for RedisNonceManager` | 1h |

### Group 3: On-Ramp Completion (Can Run in Parallel)

**NOTE: T019 REMOVED** - Bridge integration already exists in `sardis-cards/offramp.py`

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T020 | Add KYC trigger before on-ramp above threshold | `packages/sardis-ramp/src/ramp.py` | `feat(ramp): trigger KYC check before high-value on-ramp` | 1h |
| T021 | Add wallet credit on successful on-ramp webhook | `packages/sardis-api/src/sardis_api/routers/ramp.py` | `feat(ramp): credit wallet balance on onramp webhook completion` | 1h |
| T022 | Add on-ramp integration tests | `tests/integration/test_onramp_flow.py` | `test(ramp): add on-ramp integration tests` | 1h |

### Group 4: A2A Transfer & Crypto Payments (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T023 | Implement gas-free meta-transaction support | `packages/sardis-chain/src/sardis_chain/meta_tx.py` | `feat(chain): add EIP-2771 meta-transaction support` | 2h |
| T024 | Add batch transfer API endpoint | `packages/sardis-api/src/sardis_api/routers/transactions.py` | `feat(api): add POST /transactions/batch endpoint` | 1.5h |
| T025 | Add MCC lookup service with static JSON data source | `packages/sardis-core/src/sardis_v2_core/mcc_service.py`, `packages/sardis-core/src/sardis_v2_core/data/mcc_codes.json` | `feat(core): add MCC lookup service for merchant categorization` | 1h |
| T026 | Integrate MCC lookup into payment policy checks | `packages/sardis-core/src/sardis_v2_core/spending_policy.py` | `feat(policy): use MCC codes for category-based blocking` | 1h |

### Group 5: Off-Ramp & Compliance Completion (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T027 | Add velocity checks to off-ramp (daily/weekly limits) | `packages/sardis-cards/src/sardis_cards/offramp.py` | `feat(offramp): add velocity checks for withdrawal limits` | 1.5h |
| T028 | Implement SAR (Suspicious Activity Report) generation | `packages/sardis-compliance/src/sardis_compliance/sar.py` | `feat(compliance): add SAR report generation` | 2h |
| T029 | Add wallet freeze capability with DB persistence | `packages/sardis-core/src/sardis_v2_core/wallet_repository.py`, `packages/sardis-core/src/sardis_v2_core/wallets.py`, `packages/sardis-api/migrations/006_wallet_freeze.sql` | `feat(core): add wallet freeze/unfreeze with PostgreSQL persistence` | 1h |
| T030 | Add freeze endpoint to API | `packages/sardis-api/src/sardis_api/routers/wallets.py` | `feat(api): add POST /wallets/{id}/freeze endpoint` | 0.5h |
| T031 | Block transactions from frozen wallets | `packages/sardis-core/src/sardis_v2_core/transactions.py` | `feat(core): reject transactions from frozen wallets` | 0.5h |

### Group 6: CI/CD & Monitoring (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T032 | Add mypy to CI pipeline | `.github/workflows/ci.yml` | `ci: add mypy type checking to lint job` | 0.5h |
| T033 | Add explicit deploy workflow for staging/production | `.github/workflows/deploy.yml` | `ci: add deployment workflow with environment gates` | 1h |
| T034 | Add coverage enforcement to CI (fail under 70%) | `.github/workflows/ci.yml` | `ci: enforce 70% coverage threshold` | 0.5h |
| T035 | Add Sentry integration for error tracking | `packages/sardis-api/src/sardis_api/monitoring.py` | `feat(monitoring): add Sentry SDK integration` | 1h |
| T036 | Add Prometheus metrics endpoint | `packages/sardis-api/src/sardis_api/routers/metrics.py` | `feat(monitoring): add /metrics endpoint for Prometheus` | 1h |
| T037 | Add structured logging with correlation IDs | `packages/sardis-core/src/sardis_v2_core/logging_config.py` | `feat(core): add structured logging with request correlation` | 1h |

### Group 7: Security & Dependencies (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T038 | Update hono to fix CVE vulnerabilities | `packages/sardis-mcp-server/package.json` | `fix(deps): update hono to latest secure version` | 0.5h |
| T039 | Update esbuild to fix CVE vulnerabilities | `packages/sardis-sdk-js/package.json`, `landing/package.json` | `fix(deps): update esbuild to latest secure version` | 0.5h |
| T040 | Run npm audit fix across all packages | `packages/*/package.json` | `fix(deps): resolve npm audit vulnerabilities` | 1h |
| T041 | Add dependabot configuration | `.github/dependabot.yml` | `ci: add dependabot for automated security updates` | 0.5h |

### Group 8: Documentation (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T042 | Create incident response playbook | `docs/INCIDENT_PLAYBOOK.md` | `docs: add incident response playbook` | 1.5h |
| T043 | Add runbook for common operations | `docs/RUNBOOK.md` | `docs: add operational runbook` | 1h |
| T044 | Document approval flow for operators | `docs/APPROVAL_FLOW.md` | `docs: add approval workflow documentation` | 0.5h |

### Group 9: Tech Debt & Test Fixes (Can Run in Parallel)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T045 | Fix 9 failing SDK tests (token refresh issue) | `packages/sardis-sdk-python/tests/*.py`, `packages/sardis-sdk-python/src/sardis_sdk/client.py` | `fix(sdk): resolve token refresh test failures` | 1.5h |
| T046 | Fix regex deprecation warning in marketplace router | `packages/sardis-api/src/sardis_api/routers/marketplace.py` | `fix(api): replace deprecated regex with re module` | 0.5h |
| T047 | Add tests for approvals module | `tests/test_approvals.py` | `test(approvals): add unit tests for approval flow` | 1h |
| T048 | Add tests for scheduler and jobs | `tests/test_scheduler.py` | `test(jobs): add unit tests for background jobs` | 1h |

### Group 10: Final Integration & Verification (Depends on Groups 1-9)

| Task ID | Description | Files | Commit Message | Est. |
|---------|-------------|-------|----------------|------|
| T049 | E2E test: approval flow with webhook notification | `tests/e2e/test_approval_e2e.py` | `test(e2e): add approval flow end-to-end test` | 1h |
| T050 | E2E test: on-ramp to wallet credit flow | `tests/e2e/test_onramp_e2e.py` | `test(e2e): add on-ramp integration test` | 1h |
| T051 | E2E test: off-ramp with velocity checks | `tests/e2e/test_offramp_velocity.py` | `test(e2e): add off-ramp velocity check test` | 1h |
| T052 | E2E test: wallet freeze blocks transactions | `tests/e2e/test_wallet_freeze.py` | `test(e2e): add wallet freeze blocking test` | 0.5h |
| T053 | Run full test suite and verify 70%+ coverage | N/A | N/A | 0.5h |
| T054 | Update pyproject.toml with all new dependencies | `pyproject.toml`, `packages/*/pyproject.toml` | `chore: update dependencies for production` | 0.5h |

---

## Environment Variables (Defer to End)

After all tasks complete, ensure these environment variables are configured:

### Required (Production)
```bash
# Database
DATABASE_URL=postgresql://...

# API Keys
SARDIS_API_KEY=sk_...
SARDIS_SECRET_KEY=<32-char-secret>

# Turnkey MPC
TURNKEY_API_KEY=...
TURNKEY_ORGANIZATION_ID=...
TURNKEY_PRIVATE_KEY=...

# Compliance
PERSONA_API_KEY=...
PERSONA_WEBHOOK_SECRET=<min-32-chars>
ELLIPTIC_API_KEY=...

# Cards
LITHIC_API_KEY=...
LITHIC_WEBHOOK_SECRET=...

# Ramp (Bridge already in sardis-cards)
BRIDGE_API_KEY=...
BRIDGE_API_SECRET=...
ONRAMPER_API_KEY=...
ONRAMPER_WEBHOOK_SECRET=...

# Cache
UPSTASH_REDIS_URL=...

# Monitoring
SENTRY_DSN=...
```

### Optional
```bash
# Feature flags
SARDIS_ENABLE_META_TX=true
SARDIS_ENABLE_BATCH_TRANSFERS=true

# Scheduler
SCHEDULER_TIMEZONE=UTC
SPENDING_RESET_CRON="0 0 * * *"  # Daily at midnight
HOLD_EXPIRY_CHECK_INTERVAL=300   # 5 minutes
```

---

## Verification Checklist

### Group 1: Critical Infrastructure
- [ ] T001: `SELECT * FROM approvals LIMIT 1;` returns columns (not error)
- [ ] T002-T004: `curl -X POST /api/v2/approvals` creates approval
- [ ] T005: Approvals router accessible in OpenAPI docs
- [ ] T006: Webhook fires on approval status change
- [ ] T007-T011: Scheduler starts with app, jobs execute on schedule

### Group 2: Database & Infrastructure
- [ ] T012-T013: `alembic upgrade head` runs without errors
- [ ] T014: Changes to transactions table create audit_log entries
- [ ] T015: Distributed locks prevent concurrent operations
- [ ] T016-T018: All cache tests pass, metrics visible

### Group 3: On-Ramp
- [ ] T020-T021: On-ramp webhook credits wallet balance
- [ ] T022: Integration tests pass

### Group 4: A2A & Crypto
- [ ] T023: Meta-transactions execute without user gas
- [ ] T024: Batch endpoint processes multiple transfers
- [ ] T025-T026: MCC codes block gambling category (7995)

### Group 5: Off-Ramp & Compliance
- [ ] T027: Off-ramp rejected when velocity limit exceeded
- [ ] T028: SAR report generates with required fields
- [ ] T029-T031: Frozen wallet cannot send transactions

### Group 6: CI/CD & Monitoring
- [ ] T032-T034: CI passes with mypy, coverage >=70%
- [ ] T035: Errors appear in Sentry dashboard
- [ ] T036: `/metrics` returns Prometheus format
- [ ] T037: Logs include `correlation_id` field

### Group 7: Security
- [ ] T038-T041: `npm audit` shows 0 vulnerabilities

### Group 8: Documentation
- [ ] T042-T044: All docs exist and are complete

### Group 9: Tech Debt
- [ ] T045: All SDK tests pass
- [ ] T046: No deprecation warnings in logs
- [ ] T047-T048: New tests pass

### Group 10: Final
- [ ] T049-T052: All E2E tests pass
- [ ] T053: Coverage report shows >=70%
- [ ] T054: `uv sync` and `pnpm install` succeed

---

## Dependency Graph

```
Group 1 (Critical) ─────────────────────────────────────┐
    │                                                    │
    ├── T001 (DB Schema) ──► T002 (Repository) ──► T003 (Service) ──► T004 (API)
    │                                                    │
    ├── T007 (Scheduler) ──► T008, T009, T010 (Jobs) ──► T011 (Startup)
    │                                                    │
    └────────────────────────────────────────────────────┼──► Group 10 (Final)
                                                         │
Groups 2-9 (Parallel) ───────────────────────────────────┘
```

---

## Estimated Total Time

| Group | Tasks | Estimated Hours |
|-------|-------|-----------------|
| Group 1 | 11 | 11.5h |
| Group 2 | 7 | 8.5h |
| Group 3 | 3 | 3h |
| Group 4 | 4 | 5.5h |
| Group 5 | 5 | 5.5h |
| Group 6 | 6 | 5h |
| Group 7 | 4 | 2.5h |
| Group 8 | 3 | 3h |
| Group 9 | 4 | 4h |
| Group 10 | 6 | 4.5h |
| **Total** | **53** | **53h** |

With 5 parallel agents in swarm mode (Groups 2-9 parallel after Group 1):
- **Critical path**: ~16h (Group 1 + Group 10)
- **Parallel work**: ~8.5h (longest parallel group)
- **Estimated wall-clock time**: ~24h with parallel execution

---

## Success Criteria

1. All 53 tasks marked complete
2. All E2E tests passing
3. Coverage >= 70%
4. npm audit: 0 vulnerabilities
5. No TODO/FIXME remaining in production code
6. All environment variables documented
7. Incident playbook and runbook complete

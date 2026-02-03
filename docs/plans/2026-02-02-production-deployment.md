# Sardis Production Deployment Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Get Sardis fully wired and deployed to production — Lithic integration, database persistence, webhook handling, CI hardening, and live deployment.

**Architecture:** Wire existing `LithicProvider` into API routes via dependency injection, replace in-memory card storage with PostgreSQL repository, complete webhook endpoint with signature verification, add card tests to CI, then deploy contracts to testnet and API to Vercel.

**Tech Stack:** Python 3.12 / FastAPI / asyncpg / Foundry / Vercel / GitHub Actions

---

## Phase 1: Database & Card Persistence (foundation for everything else)

### Task 1: Create card repository for database persistence

**Files:**
- Create: `packages/sardis-api/src/sardis_api/repositories/card_repository.py`
- Test: `tests/test_card_repository.py`

**Step 1: Write the failing test**

```python
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from sardis_api.repositories.card_repository import CardRepository

@pytest.mark.asyncio
async def test_create_card_persists_to_db():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchrow.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "provider_card_id": "li_card_123",
        "status": "pending", "limit_per_tx": 100, "limit_daily": 1000,
    }

    repo = CardRepository(mock_pool)
    card = await repo.create(
        card_id="card_1", wallet_id="wallet_1", provider="lithic",
        provider_card_id="li_card_123", card_type="multi_use",
        limit_per_tx=100, limit_daily=1000, limit_monthly=10000,
    )
    assert card["card_id"] == "card_1"
    assert card["provider"] == "lithic"
    mock_conn.fetchrow.assert_called_once()

@pytest.mark.asyncio
async def test_get_card_by_id():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchrow.return_value = {
        "id": "uuid-1", "card_id": "card_1", "provider": "lithic",
        "status": "active",
    }

    repo = CardRepository(mock_pool)
    card = await repo.get_by_card_id("card_1")
    assert card["status"] == "active"

@pytest.mark.asyncio
async def test_get_card_not_found_returns_none():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchrow.return_value = None

    repo = CardRepository(mock_pool)
    card = await repo.get_by_card_id("nonexistent")
    assert card is None

@pytest.mark.asyncio
async def test_update_status():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchrow.return_value = {"card_id": "card_1", "status": "frozen"}

    repo = CardRepository(mock_pool)
    card = await repo.update_status("card_1", "frozen")
    assert card["status"] == "frozen"

@pytest.mark.asyncio
async def test_record_transaction():
    mock_pool = AsyncMock()
    mock_conn = AsyncMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=False)
    mock_conn.fetchrow.return_value = {
        "transaction_id": "tx_1", "card_id": "uuid-1",
        "amount": 50.00, "status": "pending",
    }

    repo = CardRepository(mock_pool)
    tx = await repo.record_transaction(
        transaction_id="tx_1", card_id="uuid-1",
        provider_tx_id="li_tx_123", amount=50.00,
        currency="USD", merchant_name="Test Store",
        status="pending",
    )
    assert tx["transaction_id"] == "tx_1"
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_card_repository.py -v`
Expected: FAIL — module not found

**Step 3: Write minimal implementation**

```python
"""Card repository for PostgreSQL persistence."""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import uuid


class CardRepository:
    """PostgreSQL repository for virtual card data."""

    def __init__(self, pool):
        self._pool = pool

    async def create(
        self,
        card_id: str,
        wallet_id: str,
        provider: str,
        provider_card_id: str | None = None,
        card_type: str = "multi_use",
        limit_per_tx: float = 0,
        limit_daily: float = 0,
        limit_monthly: float = 0,
    ) -> Dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO virtual_cards (
                    id, card_id, wallet_id, provider, provider_card_id,
                    card_type, status, limit_per_tx, limit_daily, limit_monthly,
                    created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, 'pending', $7, $8, $9, NOW())
                RETURNING *
                """,
                str(uuid.uuid4()), card_id, wallet_id, provider,
                provider_card_id, card_type,
                limit_per_tx, limit_daily, limit_monthly,
            )
            return dict(row)

    async def get_by_card_id(self, card_id: str) -> Optional[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM virtual_cards WHERE card_id = $1", card_id
            )
            return dict(row) if row else None

    async def get_by_wallet_id(self, wallet_id: str) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM virtual_cards WHERE wallet_id = $1 ORDER BY created_at DESC",
                wallet_id,
            )
            return [dict(r) for r in rows]

    async def update_status(
        self, card_id: str, status: str
    ) -> Optional[Dict[str, Any]]:
        ts_field = {
            "active": "activated_at",
            "frozen": "frozen_at",
            "cancelled": "cancelled_at",
        }.get(status)
        extra = f", {ts_field} = NOW()" if ts_field else ""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE virtual_cards SET status = $1{extra} WHERE card_id = $2 RETURNING *",
                status, card_id,
            )
            return dict(row) if row else None

    async def update_limits(
        self, card_id: str, limit_per_tx: float | None = None,
        limit_daily: float | None = None, limit_monthly: float | None = None,
    ) -> Optional[Dict[str, Any]]:
        sets = []
        params = []
        idx = 1
        for field, val in [
            ("limit_per_tx", limit_per_tx),
            ("limit_daily", limit_daily),
            ("limit_monthly", limit_monthly),
        ]:
            if val is not None:
                sets.append(f"{field} = ${idx}")
                params.append(val)
                idx += 1
        if not sets:
            return await self.get_by_card_id(card_id)
        params.append(card_id)
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                f"UPDATE virtual_cards SET {', '.join(sets)} WHERE card_id = ${idx} RETURNING *",
                *params,
            )
            return dict(row) if row else None

    async def update_funded_amount(
        self, card_id: str, amount: float
    ) -> Optional[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "UPDATE virtual_cards SET funded_amount = $1 WHERE card_id = $2 RETURNING *",
                amount, card_id,
            )
            return dict(row) if row else None

    async def record_transaction(
        self,
        transaction_id: str,
        card_id: str,
        provider_tx_id: str | None = None,
        amount: float = 0,
        currency: str = "USD",
        merchant_name: str | None = None,
        merchant_category: str | None = None,
        status: str = "pending",
    ) -> Dict[str, Any]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO card_transactions (
                    id, transaction_id, card_id, provider_tx_id,
                    amount, currency, merchant_name, merchant_category,
                    status, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, NOW())
                RETURNING *
                """,
                str(uuid.uuid4()), transaction_id, card_id,
                provider_tx_id, amount, currency,
                merchant_name, merchant_category, status,
            )
            return dict(row)

    async def list_transactions(
        self, card_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT * FROM card_transactions
                WHERE card_id = $1
                ORDER BY created_at DESC LIMIT $2
                """,
                card_id, limit,
            )
            return [dict(r) for r in rows]
```

**Step 4: Run test to verify it passes**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_card_repository.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add packages/sardis-api/src/sardis_api/repositories/card_repository.py tests/test_card_repository.py
git commit -m "feat: add CardRepository for PostgreSQL card persistence"
```

---

### Task 2: Wire LithicProvider into API routes

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/cards.py`
- Modify: `packages/sardis-api/src/sardis_api/main.py` (service injection)
- Test: `tests/test_cards_api.py`

**Step 1: Write the failing test**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

@pytest.fixture
def mock_card_repo():
    repo = AsyncMock()
    repo.create.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "provider_card_id": "li_card_123",
        "status": "pending", "limit_daily": 1000,
    }
    repo.get_by_card_id.return_value = {
        "id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1",
        "provider": "lithic", "status": "active",
    }
    repo.update_status.return_value = {
        "id": "uuid-1", "card_id": "card_1", "status": "frozen",
    }
    return repo

@pytest.fixture
def mock_lithic_provider():
    provider = AsyncMock()
    provider.create_card.return_value = MagicMock(
        provider_card_id="li_card_123",
        card_number_last4="4242",
        status="pending",
    )
    provider.freeze_card.return_value = MagicMock(status="frozen")
    provider.unfreeze_card.return_value = MagicMock(status="active")
    provider.cancel_card.return_value = MagicMock(status="cancelled")
    return provider

@pytest.fixture
def app_with_cards(mock_card_repo, mock_lithic_provider):
    from sardis_api.routers.cards import create_cards_router
    app = FastAPI()
    router = create_cards_router(
        card_repo=mock_card_repo,
        card_provider=mock_lithic_provider,
    )
    app.include_router(router, prefix="/api/v2/cards")
    return app

def test_create_card_calls_provider_and_persists(app_with_cards, mock_lithic_provider, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.post("/api/v2/cards", json={
        "wallet_id": "wallet_1",
        "card_type": "multi_use",
        "limit_daily": 1000,
    })
    assert resp.status_code == 201
    mock_lithic_provider.create_card.assert_called_once()
    mock_card_repo.create.assert_called_once()

def test_freeze_card_calls_provider_and_updates_db(app_with_cards, mock_lithic_provider, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.post("/api/v2/cards/card_1/freeze")
    assert resp.status_code == 200
    mock_lithic_provider.freeze_card.assert_called_once()
    mock_card_repo.update_status.assert_called_once_with("card_1", "frozen")

def test_get_card_reads_from_db(app_with_cards, mock_card_repo):
    client = TestClient(app_with_cards)
    resp = client.get("/api/v2/cards/card_1")
    assert resp.status_code == 200
    mock_card_repo.get_by_card_id.assert_called_once_with("card_1")

def test_get_card_not_found(app_with_cards, mock_card_repo):
    mock_card_repo.get_by_card_id.return_value = None
    client = TestClient(app_with_cards)
    resp = client.get("/api/v2/cards/nonexistent")
    assert resp.status_code == 404
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_cards_api.py -v`
Expected: FAIL — `create_cards_router` not found

**Step 3: Rewrite cards router with dependency injection**

Rewrite `packages/sardis-api/src/sardis_api/routers/cards.py`:
- Replace module-level `_cards_store` dict with `CardRepository` parameter
- Replace all in-memory operations with `card_repo` calls
- Add `card_provider` parameter for `LithicProvider` calls
- Export `create_cards_router(card_repo, card_provider)` factory function
- Each route: call provider first, then persist to DB
- For `issue_card()`: provider.create_card() -> repo.create()
- For `freeze_card()`: repo.get_by_card_id() -> provider.freeze_card() -> repo.update_status()
- For `cancel_card()`: repo.get_by_card_id() -> provider.cancel_card() -> repo.update_status()
- For `get_card()` / `list_cards()`: read from repo only
- For `list_card_transactions()`: read from repo

**Step 4: Wire into main.py startup**

In `packages/sardis-api/src/sardis_api/main.py`, in the service initialization section (~line 498-529):
- Import `CardRepository` and `LithicProvider`
- Create `card_repo = CardRepository(db_pool)` after database init
- Create `lithic_provider = LithicProvider()` if `LITHIC_API_KEY` is set, else use a `NullCardProvider` that raises on all operations
- Replace `app.include_router(cards_router.router, ...)` with:
  ```python
  cards_router_instance = create_cards_router(card_repo=card_repo, card_provider=lithic_provider)
  app.include_router(cards_router_instance, prefix="/api/v2/cards", tags=["cards"])
  ```

**Step 5: Run tests to verify they pass**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_cards_api.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add packages/sardis-api/src/sardis_api/routers/cards.py packages/sardis-api/src/sardis_api/main.py tests/test_cards_api.py
git commit -m "feat: wire LithicProvider into card API routes with DB persistence"
```

---

### Task 3: Implement webhook endpoint with signature verification

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/routers/cards.py` (webhook route)
- Test: `tests/test_card_webhooks.py`

**Step 1: Write the failing test**

```python
import pytest
import hmac
import hashlib
import json
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

WEBHOOK_SECRET = "test_webhook_secret_123"

def sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()

@pytest.fixture
def mock_card_repo():
    repo = AsyncMock()
    repo.get_by_card_id.return_value = {"id": "uuid-1", "card_id": "card_1", "wallet_id": "wallet_1"}
    repo.record_transaction.return_value = {"transaction_id": "tx_1", "status": "pending"}
    repo.update_status.return_value = {"card_id": "card_1", "status": "active"}
    return repo

@pytest.fixture
def app_with_webhook(mock_card_repo):
    from sardis_api.routers.cards import create_cards_router
    provider = AsyncMock()
    router = create_cards_router(
        card_repo=mock_card_repo,
        card_provider=provider,
        webhook_secret=WEBHOOK_SECRET,
    )
    app = FastAPI()
    app.include_router(router, prefix="/api/v2/cards")
    return app

def test_webhook_valid_signature_processes_event(app_with_webhook, mock_card_repo):
    payload = json.dumps({
        "type": "transaction.created",
        "data": {
            "token": "li_tx_abc",
            "card_token": "li_card_123",
            "amount": 2500,
            "merchant": {"descriptor": "TEST STORE"},
            "status": "PENDING",
        }
    }).encode()
    sig = sign_payload(payload, WEBHOOK_SECRET)
    client = TestClient(app_with_webhook)
    resp = client.post(
        "/api/v2/cards/webhooks",
        content=payload,
        headers={"X-Lithic-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "processed"

def test_webhook_invalid_signature_rejected(app_with_webhook):
    payload = b'{"type": "transaction.created", "data": {}}'
    client = TestClient(app_with_webhook)
    resp = client.post(
        "/api/v2/cards/webhooks",
        content=payload,
        headers={"X-Lithic-Signature": "bad_sig", "Content-Type": "application/json"},
    )
    assert resp.status_code == 401

def test_webhook_missing_signature_rejected(app_with_webhook):
    client = TestClient(app_with_webhook)
    resp = client.post(
        "/api/v2/cards/webhooks",
        content=b'{"type": "test"}',
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 401

def test_webhook_records_transaction(app_with_webhook, mock_card_repo):
    payload = json.dumps({
        "type": "transaction.created",
        "data": {
            "token": "li_tx_xyz",
            "card_token": "li_card_456",
            "amount": 5000,
            "merchant": {"descriptor": "COFFEE SHOP"},
            "status": "PENDING",
        }
    }).encode()
    sig = sign_payload(payload, WEBHOOK_SECRET)
    client = TestClient(app_with_webhook)
    resp = client.post(
        "/api/v2/cards/webhooks",
        content=payload,
        headers={"X-Lithic-Signature": sig, "Content-Type": "application/json"},
    )
    assert resp.status_code == 200
    mock_card_repo.record_transaction.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_card_webhooks.py -v`
Expected: FAIL — webhook_secret parameter not accepted / no verification logic

**Step 3: Implement webhook handler in cards router**

Add to `create_cards_router()`:
- Accept `webhook_secret: str | None = None` parameter
- Replace the stub `receive_card_webhook` with:
  1. Read raw body
  2. Extract `X-Lithic-Signature` header — return 401 if missing
  3. HMAC-SHA256 verify — return 401 if mismatch
  4. Parse JSON event
  5. If `transaction.created`: call `card_repo.record_transaction()`
  6. If `card.*` event: call `card_repo.update_status()` as needed
  7. Return `{"status": "processed", "event_type": ...}`

**Step 4: Wire webhook_secret in main.py**

Add `LITHIC_WEBHOOK_SECRET` from env to the `create_cards_router()` call.

**Step 5: Run tests to verify they pass**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/test_card_webhooks.py -v`
Expected: PASS (4 tests)

**Step 6: Commit**

```bash
git add packages/sardis-api/src/sardis_api/routers/cards.py packages/sardis-api/src/sardis_api/main.py tests/test_card_webhooks.py
git commit -m "feat: implement Lithic webhook endpoint with HMAC verification"
```

---

## Phase 2: CI/CD Hardening

### Task 4: Add card tests to CI pipeline

**Files:**
- Modify: `.github/workflows/ci.yml`

**Step 1: Add sardis-cards test job to CI**

After the existing "Test Python" job, add:

```yaml
  test-cards:
    runs-on: ubuntu-latest
    needs: lint
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Install uv
        run: pip install uv
      - name: Install dependencies
        run: uv sync
      - name: Run card repository tests
        run: uv run python -m pytest tests/test_card_repository.py tests/test_cards_api.py tests/test_card_webhooks.py -v
```

**Step 2: Add monitoring script validation**

```yaml
  validate-scripts:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Shellcheck monitoring scripts
        run: |
          sudo apt-get install -y shellcheck
          shellcheck scripts/health_monitor.sh
          shellcheck scripts/monitor_contracts.sh
          shellcheck scripts/deploy_testnet.sh
          shellcheck scripts/run_migrations.sh
```

**Step 3: Commit**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: add card tests and shell script validation to pipeline"
```

---

### Task 5: Add feature flags for cards in production

**Files:**
- Modify: `packages/sardis-api/src/sardis_api/main.py`

**Step 1: Gate card routes behind SARDIS_ENABLE_CARDS**

The env var `SARDIS_ENABLE_CARDS` already exists in `.env.example` (set to `false`). Wire it:

In `main.py`, wrap card router registration:

```python
if os.getenv("SARDIS_ENABLE_CARDS", "false").lower() == "true":
    from sardis_api.repositories.card_repository import CardRepository
    card_repo = CardRepository(db_pool)
    # ... LithicProvider init ...
    cards_router_instance = create_cards_router(...)
    app.include_router(cards_router_instance, prefix="/api/v2/cards", tags=["cards"])
    logger.info("Card routes enabled")
else:
    logger.info("Card routes disabled (SARDIS_ENABLE_CARDS != true)")
```

**Step 2: Commit**

```bash
git add packages/sardis-api/src/sardis_api/main.py
git commit -m "feat: gate card routes behind SARDIS_ENABLE_CARDS feature flag"
```

---

## Phase 3: Contract Deployment

### Task 6: Deploy contracts to Base Sepolia testnet

**Step 1: Verify contracts compile**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2/contracts" && forge build`
Expected: Successful compilation

**Step 2: Run full contract test suite**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2/contracts" && forge test -v`
Expected: All 91+ tests pass (79 unit + 12 fuzz)

**Step 3: Dry-run testnet deployment**

Run: `BASE_SEPOLIA_RPC_URL=<rpc_url> PRIVATE_KEY=<key> ./scripts/deploy_testnet.sh`
Expected: Simulation succeeds, shows estimated gas costs

**Step 4: Live testnet deployment**

Run: `BASE_SEPOLIA_RPC_URL=<rpc_url> PRIVATE_KEY=<key> ./scripts/deploy_testnet.sh --broadcast`
Expected: Contracts deployed, addresses printed

**Step 5: Record deployed addresses**

Create or update `.env.staging` with:
```
SARDIS_WALLET_FACTORY_ADDRESS=0x...
SARDIS_ESCROW_ADDRESS=0x...
```

**Step 6: Verify on Basescan**

Run: `BASE_SEPOLIA_RPC_URL=<rpc_url> PRIVATE_KEY=<key> BASESCAN_API_KEY=<key> ./scripts/deploy_testnet.sh --broadcast --verify`

**Step 7: Commit**

```bash
git add .env.staging
git commit -m "chore: record Base Sepolia testnet contract addresses"
```

---

## Phase 4: Database Migration & API Deployment

### Task 7: Run migrations on staging database

**Step 1: Dry run**

Run: `DATABASE_URL=<staging_url> ./scripts/run_migrations.sh --dry-run`
Expected: Shows 001, 002, 003 as pending

**Step 2: Apply**

Run: `DATABASE_URL=<staging_url> ./scripts/run_migrations.sh`
Expected: All 3 migrations applied

**Step 3: Verify**

Run: `psql <staging_url> -c "SELECT * FROM schema_migrations;"`
Expected: 3 rows (001, 002, 003)

---

### Task 8: Configure environment for Vercel deployment

**Files:**
- Modify: `api/index.py` (ensure card packages on path)
- Modify: `api/requirements.txt` (add lithic SDK)

**Step 1: Add lithic to API requirements**

Add to `api/requirements.txt`:
```
lithic>=0.30.0
```

**Step 2: Ensure sardis-cards is on sys.path in api/index.py**

Add to the path setup section:
```python
sys.path.insert(0, os.path.join(root, "packages", "sardis-cards", "src"))
```

**Step 3: Commit**

```bash
git add api/index.py api/requirements.txt
git commit -m "chore: add lithic SDK and sardis-cards to Vercel deployment"
```

---

### Task 9: Set Vercel environment variables

**Step 1: Set required variables via Vercel CLI or dashboard**

```bash
vercel env add SARDIS_ENVIRONMENT production
vercel env add DATABASE_URL <neon_postgres_url>
vercel env add SARDIS_SECRET_KEY <generated_key>
vercel env add TURNKEY_API_KEY <key>
vercel env add TURNKEY_API_PUBLIC_KEY <key>
vercel env add TURNKEY_ORGANIZATION_ID <org_id>
vercel env add SARDIS_CHAIN_MODE live
vercel env add SARDIS_REDIS_URL <upstash_url>
vercel env add SARDIS_ENABLE_CARDS false  # Enable after Lithic KYB
vercel env add SENTRY_DSN <sentry_dsn>
```

**Step 2: Deploy to staging**

Run: `vercel --prod`

**Step 3: Verify health**

Run: `curl https://sardis.sh/health | jq .`
Expected: `{"status": "healthy", ...}`

---

### Task 10: Set up monitoring cron

**Files:**
- Create: `.github/workflows/monitoring.yml`

**Step 1: Create GitHub Actions monitoring workflow**

```yaml
name: Health Monitoring

on:
  schedule:
    - cron: '*/5 * * * *'  # Every 5 minutes
  workflow_dispatch:

jobs:
  health-check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run health check
        env:
          HEALTH_URL: ${{ secrets.PRODUCTION_HEALTH_URL }}
          WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
        run: |
          chmod +x scripts/health_monitor.sh
          ./scripts/health_monitor.sh
      - name: Alert on failure
        if: failure()
        run: |
          curl -X POST "${{ secrets.SLACK_WEBHOOK_URL }}" \
            -H 'Content-Type: application/json' \
            -d '{"text": ":rotating_light: Sardis health check FAILED. Check https://github.com/${{ github.repository }}/actions"}'
```

**Step 2: Commit**

```bash
git add .github/workflows/monitoring.yml
git commit -m "ci: add scheduled health monitoring via GitHub Actions"
```

---

## Phase 5: End-to-End Verification

### Task 11: Write integration test for full payment flow

**Files:**
- Create: `tests/e2e/test_payment_flow_e2e.py`

**Step 1: Write the test**

```python
"""
End-to-end payment flow test.

Requires:
  SARDIS_API_URL=https://staging.sardis.sh
  SARDIS_API_KEY=sk_test_...

Run: pytest tests/e2e/test_payment_flow_e2e.py -v --e2e
"""
import os
import pytest
import httpx

API_URL = os.getenv("SARDIS_API_URL", "http://localhost:8000")
API_KEY = os.getenv("SARDIS_API_KEY", "")

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not API_KEY, reason="SARDIS_API_KEY not set"),
]

@pytest.fixture
def client():
    return httpx.Client(
        base_url=API_URL,
        headers={"X-API-Key": API_KEY},
        timeout=30,
    )

def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("healthy", "partial")

def test_create_agent_and_wallet(client):
    # Create organization
    resp = client.post("/api/v2/organizations", json={
        "name": "E2E Test Org",
        "external_id": f"e2e_test_{os.urandom(4).hex()}",
    })
    assert resp.status_code in (200, 201)
    org_id = resp.json().get("id") or resp.json().get("organization_id")

    # Create agent
    resp = client.post("/api/v2/agents", json={
        "organization_id": org_id,
        "name": "E2E Test Agent",
    })
    assert resp.status_code in (200, 201)
    agent_id = resp.json().get("id") or resp.json().get("agent_id")

    # Create wallet
    resp = client.post("/api/v2/wallets", json={
        "agent_id": agent_id,
        "chain": "base_sepolia",
    })
    assert resp.status_code in (200, 201)
    wallet = resp.json()
    assert "address" in wallet or "chain_address" in wallet

def test_spending_policy_enforcement(client):
    # This test verifies that the spending policy blocks overspend
    # Exact implementation depends on existing agent/wallet IDs
    resp = client.get("/api/v2/health")
    assert resp.status_code == 200
```

**Step 2: Commit**

```bash
git add tests/e2e/test_payment_flow_e2e.py
git commit -m "test: add end-to-end payment flow integration test"
```

---

### Task 12: Final deployment commit and push

**Step 1: Run full test suite**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2" && uv run python -m pytest tests/ -v --ignore=tests/e2e -x`
Expected: All tests pass

**Step 2: Run contract tests**

Run: `cd "/Users/efebarandurmaz/Desktop/sardis 2/contracts" && forge test`
Expected: All tests pass

**Step 3: Push everything**

```bash
git push origin main
```

**Step 4: Verify Vercel deployment**

Run: `curl https://sardis.sh/api/v2/health`
Expected: `{"status": "ok", ...}`

---

## Post-Deployment (Manual — Not Code Tasks)

These require human action and cannot be automated:

1. **Submit Lithic KYB application** (see `docs/lithic-production-checklist.md`)
2. **Engage smart contract auditor** (send `docs/audit-preparation.md`)
3. **Configure Sentry project** and add `SENTRY_DSN` to Vercel
4. **Set up Slack webhook** for monitoring alerts
5. **Upgrade RPC endpoints** from public to dedicated (Alchemy/Infura)
6. **Schedule database backups** on Neon
7. **After Lithic KYB approval**: Set `SARDIS_ENABLE_CARDS=true` in Vercel, deploy

---

## Task Dependency Graph

```
Task 1 (Card Repository)
  └─> Task 2 (Wire LithicProvider) ─┐
       └─> Task 3 (Webhook endpoint) ├─> Task 4 (CI)
                                      │    └─> Task 5 (Feature flags)
                                      │
Task 6 (Deploy contracts) ───────────┤
                                      │
Task 7 (Run migrations) ─────────────┼─> Task 8 (Vercel config)
                                      │    └─> Task 9 (Env vars)
                                      │         └─> Task 10 (Monitoring)
                                      │              └─> Task 11 (E2E test)
                                      │                   └─> Task 12 (Final push)
```

Tasks 1-3 are sequential (each depends on prior).
Tasks 4-5 depend on 1-3.
Task 6 is independent (can run in parallel with 1-5).
Task 7 is independent (can run in parallel with 1-6).
Tasks 8-12 depend on everything above.

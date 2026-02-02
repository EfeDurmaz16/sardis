import sys
import importlib
import pytest
from unittest.mock import AsyncMock, MagicMock

# Import the module directly to avoid sardis_api.__init__ side effects
import importlib.util
_spec = importlib.util.spec_from_file_location(
    "sardis_api.repositories.card_repository",
    "/Users/efebarandurmaz/Desktop/sardis 2/packages/sardis-api/src/sardis_api/repositories/card_repository.py",
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
CardRepository = _mod.CardRepository


def _make_pool_and_conn():
    """Create a mock pool that supports `async with pool.acquire() as conn`."""
    mock_conn = AsyncMock()
    mock_ctx = AsyncMock()
    mock_ctx.__aenter__.return_value = mock_conn
    mock_ctx.__aexit__.return_value = False
    mock_pool = MagicMock()
    mock_pool.acquire.return_value = mock_ctx
    return mock_pool, mock_conn


@pytest.mark.asyncio
async def test_create_card_persists_to_db():
    mock_pool, mock_conn = _make_pool_and_conn()
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
    mock_pool, mock_conn = _make_pool_and_conn()
    mock_conn.fetchrow.return_value = {
        "id": "uuid-1", "card_id": "card_1", "provider": "lithic", "status": "active",
    }
    repo = CardRepository(mock_pool)
    card = await repo.get_by_card_id("card_1")
    assert card["status"] == "active"


@pytest.mark.asyncio
async def test_get_card_not_found_returns_none():
    mock_pool, mock_conn = _make_pool_and_conn()
    mock_conn.fetchrow.return_value = None
    repo = CardRepository(mock_pool)
    card = await repo.get_by_card_id("nonexistent")
    assert card is None


@pytest.mark.asyncio
async def test_update_status():
    mock_pool, mock_conn = _make_pool_and_conn()
    mock_conn.fetchrow.return_value = {"card_id": "card_1", "status": "frozen"}
    repo = CardRepository(mock_pool)
    card = await repo.update_status("card_1", "frozen")
    assert card["status"] == "frozen"


@pytest.mark.asyncio
async def test_record_transaction():
    mock_pool, mock_conn = _make_pool_and_conn()
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

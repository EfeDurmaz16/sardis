"""
Pytest configuration and fixtures for Sardis SDK tests.
"""
import pytest

from sardis_sdk import AsyncSardisClient


# Mock response data
MOCK_RESPONSES = {
    "health": {
        "status": "healthy",
        "version": "0.3.0",
    },
    "wallet": {
        "wallet_id": "wallet_test123",
        "agent_id": "agent_001",
        "mpc_provider": "turnkey",
        "addresses": {"base_sepolia": "0x1234567890abcdef1234567890abcdef12345678"},
        "currency": "USDC",
        "limit_per_tx": "1000.00",
        "limit_total": "10000.00",
        "is_active": True,
        "created_at": "2025-01-20T00:00:00Z",
        "updated_at": "2025-01-20T00:00:00Z",
    },
    "balance": {
        "wallet_id": "wallet_test123",
        "chain": "base",
        "token": "USDC",
        "balance": "1000.00",
        "balance_minor": 1000000000,
        "address": "0x1234567890abcdef1234567890abcdef12345678",
    },
    "mandate": {
        "mandate_id": "mandate_abc123",
        "status": "completed",
        "chain_tx_hash": "0xabcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890",
        "chain": "base_sepolia",
        "ledger_tx_id": "ltx_456",
        "audit_anchor": "anchor_789",
    },
    "hold": {
        "hold_id": "hold_xyz789",
        "wallet_id": "wallet_test123",
        "amount": "100.00",
        "token": "USDC",
        "status": "active",
        "expires_at": "2025-01-21T00:00:00Z",
        "created_at": "2025-01-20T00:00:00Z",
    },
    "webhook": {
        "id": "webhook_def456",
        "url": "https://example.com/webhook",
        "events": ["payment.completed", "payment.failed"],
        "active": True,
        "secret": "whsec_abc123",
        "created_at": "2025-01-20T00:00:00Z",
    },
    "policy": {
        "allowed": True,
        "policy_id": "policy_test",
        "reason": None,
    },
    "policy_violation": {
        "allowed": False,
        "policy_id": "policy_test",
        "reason": "Amount exceeds daily limit",
    },
}


@pytest.fixture
def api_key() -> str:
    """Test API key."""
    return "test-api-key"


@pytest.fixture
def base_url() -> str:
    """Test base URL."""
    return "https://api.sardis.network"


@pytest.fixture
async def client(api_key: str, base_url: str) -> AsyncSardisClient:
    """Create a test client."""
    client = AsyncSardisClient(api_key=api_key, base_url=base_url)
    yield client
    await client.close()


@pytest.fixture
def mock_responses() -> dict:
    """Return mock response data."""
    return MOCK_RESPONSES


@pytest.fixture
def mock_health_response(httpx_mock):
    """Mock health endpoint."""
    httpx_mock.add_response(
        url="https://api.sardis.network/health",
        method="GET",
        json=MOCK_RESPONSES["health"],
    )
    return httpx_mock


@pytest.fixture
def mock_wallet_endpoints(httpx_mock):
    """Mock wallet endpoints."""
    # Create wallet
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/wallets",
        method="POST",
        json=MOCK_RESPONSES["wallet"],
    )
    # Get wallet
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/wallets/wallet_test123",
        method="GET",
        json=MOCK_RESPONSES["wallet"],
    )
    # Get balance
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/wallets/wallet_test123/balance",
        method="GET",
        json=MOCK_RESPONSES["balance"],
    )
    return httpx_mock


@pytest.fixture
def mock_payment_endpoints(httpx_mock):
    """Mock payment endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/mandates/execute",
        method="POST",
        json=MOCK_RESPONSES["mandate"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/ap2/payments/execute",
        method="POST",
        json=MOCK_RESPONSES["mandate"],
    )
    return httpx_mock


@pytest.fixture
def mock_hold_endpoints(httpx_mock):
    """Mock hold endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/holds",
        method="POST",
        json=MOCK_RESPONSES["hold"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/holds/hold_xyz789",
        method="GET",
        json=MOCK_RESPONSES["hold"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/holds/hold_xyz789/capture",
        method="POST",
        json={**MOCK_RESPONSES["hold"], "status": "captured"},
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/holds/hold_xyz789/void",
        method="POST",
        json={**MOCK_RESPONSES["hold"], "status": "voided"},
    )
    return httpx_mock


@pytest.fixture
def mock_webhook_endpoints(httpx_mock):
    """Mock webhook endpoints."""
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/webhooks",
        method="POST",
        json=MOCK_RESPONSES["webhook"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/webhooks",
        method="GET",
        json={"webhooks": [MOCK_RESPONSES["webhook"]]},
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/webhooks/webhook_def456",
        method="GET",
        json=MOCK_RESPONSES["webhook"],
    )
    httpx_mock.add_response(
        url="https://api.sardis.network/api/v2/webhooks/webhook_def456",
        method="DELETE",
        status_code=204,
    )
    return httpx_mock

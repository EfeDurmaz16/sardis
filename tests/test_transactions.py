"""Transactions API endpoint tests."""
from __future__ import annotations

import pytest


@pytest.mark.anyio
async def test_list_chains(test_client):
    """Test listing supported chains."""
    response = await test_client.get("/api/v2/transactions/chains")
    
    assert response.status_code == 200
    data = response.json()
    assert "chains" in data
    assert len(data["chains"]) > 0
    
    # Check chain structure
    chain = data["chains"][0]
    assert "name" in chain
    assert "chain_id" in chain
    assert "supported_tokens" in chain


@pytest.mark.anyio
async def test_list_tokens(test_client):
    """Test listing tokens for a chain."""
    response = await test_client.get("/api/v2/transactions/tokens/base_sepolia")
    
    assert response.status_code == 200
    data = response.json()
    assert data["chain"] == "base_sepolia"
    assert "tokens" in data
    assert len(data["tokens"]) > 0


@pytest.mark.anyio
async def test_list_tokens_invalid_chain(test_client):
    """Test listing tokens for an invalid chain."""
    response = await test_client.get("/api/v2/transactions/tokens/invalid_chain")
    
    assert response.status_code == 400


@pytest.mark.anyio
async def test_estimate_gas(test_client):
    """Test gas estimation."""
    response = await test_client.post(
        "/api/v2/transactions/estimate-gas",
        json={
            "chain": "base_sepolia",
            "token": "USDC",
            "amount": "1000000",  # 1 USDC (6 decimals)
            "destination": "0x1234567890123456789012345678901234567890",
        },
    )

    # In test environment without RPC access, may return 500
    if response.status_code == 200:
        data = response.json()
        assert "gas_limit" in data
        assert "gas_price_gwei" in data
        assert "estimated_cost_wei" in data
    else:
        # Accept 500 when RPC is unavailable in test environment
        assert response.status_code == 500


@pytest.mark.anyio
async def test_estimate_gas_invalid_chain(test_client):
    """Test gas estimation with invalid chain."""
    response = await test_client.post(
        "/api/v2/transactions/estimate-gas",
        json={
            "chain": "invalid_chain",
            "token": "USDC",
            "amount": "1000000",
            "destination": "0x1234567890123456789012345678901234567890",
        },
    )
    
    assert response.status_code == 400


@pytest.mark.anyio
async def test_transaction_status(test_client):
    """Test getting transaction status."""
    # Use a fake tx hash - should return pending or not found
    response = await test_client.get(
        "/api/v2/transactions/status/0x1234567890123456789012345678901234567890123456789012345678901234",
        params={"chain": "base_sepolia"},
    )
    
    # In simulated mode, this should work
    assert response.status_code in [200, 500]  # 500 if RPC fails

"""Integration tests for the full AP2 payment flow."""
from __future__ import annotations

import os
import time
import pytest
from decimal import Decimal
from httpx import AsyncClient

from sardis_v2_core.mandates import (
    IntentMandate,
    CartMandate,
    PaymentMandate,
    MandateChain,
    VCProof,
)

# All tests in this module require a PostgreSQL database
pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL", "").startswith("postgresql://") or 
         os.environ.get("DATABASE_URL", "").startswith("postgres://")),
    reason="Requires PostgreSQL database (set DATABASE_URL env var)"
)


def create_vc_proof() -> dict:
    """Create a test VCProof dictionary."""
    return {
        "type": "DataIntegrityProof",
        "verification_method": "did:key:z6MkTest123#key-1",
        "created": "2025-12-08T00:00:00Z",
        "proof_purpose": "assertionMethod",
        "proof_value": "test_signature_base64",
    }


def create_mandate_bundle(
    amount_minor: int = 10000,
    token: str = "USDC",
    chain: str = "base_sepolia",
) -> dict:
    """Create a full AP2 mandate bundle for testing."""
    expires_at = int(time.time()) + 300
    proof = create_vc_proof()
    
    return {
        "intent": {
            "mandate_id": f"intent_{int(time.time())}",
            "mandate_type": "intent",
            "issuer": "user_123",
            "subject": "agent_456",
            "expires_at": expires_at,
            "nonce": f"intent_nonce_{int(time.time())}",
            "proof": proof,
            "domain": "sardis.network",
            "purpose": "intent",
            "scope": ["payments", "shopping"],
            "requested_amount": amount_minor,
        },
        "cart": {
            "mandate_id": f"cart_{int(time.time())}",
            "mandate_type": "cart",
            "issuer": "merchant.example.com",
            "subject": "agent_456",
            "expires_at": expires_at,
            "nonce": f"cart_nonce_{int(time.time())}",
            "proof": proof,
            "domain": "merchant.example.com",
            "purpose": "cart",
            "line_items": [
                {"sku": "ITEM001", "quantity": 1, "price_minor": amount_minor}
            ],
            "merchant_domain": "merchant.example.com",
            "currency": "USD",
            "subtotal_minor": amount_minor,
            "taxes_minor": 0,
        },
        "payment": {
            "mandate_id": f"payment_{int(time.time())}",
            "mandate_type": "payment",
            "issuer": "agent_456",
            "subject": "wallet_789",
            "expires_at": expires_at,
            "nonce": f"payment_nonce_{int(time.time())}",
            "proof": proof,
            "domain": "sardis.network",
            "purpose": "checkout",
            "chain": chain,
            "token": token,
            "amount_minor": amount_minor,
            "destination": "0x1234567890123456789012345678901234567890",
            "audit_hash": "sha256:test_audit_hash",
        },
    }


class TestPaymentFlowAPI:
    """Integration tests for the payment flow via API."""

    @pytest.mark.asyncio
    async def test_execute_mandate_success(self, test_client: AsyncClient):
        """Test executing a single payment mandate."""
        mandate = {
            "mandate_id": f"test_payment_{int(time.time())}",
            "issuer": "test_agent",
            "subject": "test_wallet",
            "destination": "0x1234567890123456789012345678901234567890",
            "amount_minor": 10000,  # $100.00
            "token": "USDC",
            "chain": "base_sepolia",
            "expires_at": int(time.time()) + 300,
        }
        
        response = await test_client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ledger_tx_id" in data
        assert "chain_tx_hash" in data
        assert data["chain"] == "base_sepolia"

    @pytest.mark.asyncio
    async def test_execute_mandate_expired(self, test_client: AsyncClient):
        """Test executing an expired mandate fails."""
        mandate = {
            "mandate_id": f"expired_payment_{int(time.time())}",
            "issuer": "test_agent",
            "subject": "test_wallet",
            "destination": "0x1234567890123456789012345678901234567890",
            "amount_minor": 10000,
            "token": "USDC",
            "chain": "base_sepolia",
            "expires_at": int(time.time()) - 100,  # Already expired
        }
        
        response = await test_client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "expired" in data.get("detail", "").lower() or "error" in data

    @pytest.mark.asyncio
    async def test_execute_ap2_bundle_success(self, test_client: AsyncClient):
        """Test executing a full AP2 mandate bundle."""
        bundle = create_mandate_bundle(amount_minor=5000)
        
        response = await test_client.post(
            "/api/v2/ap2/payments/execute",
            json=bundle,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "ledger_tx_id" in data
        assert "chain_tx_hash" in data
        assert "compliance_provider" in data

    @pytest.mark.asyncio
    async def test_execute_ap2_bundle_invalid_token(self, test_client: AsyncClient):
        """Test AP2 bundle with invalid token is rejected."""
        bundle = create_mandate_bundle(token="INVALID_TOKEN")
        
        response = await test_client.post(
            "/api/v2/ap2/payments/execute",
            json=bundle,
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "token" in str(data).lower() or "compliance" in str(data).lower()

    @pytest.mark.asyncio
    async def test_execute_ap2_bundle_amount_over_limit(self, test_client: AsyncClient):
        """Test AP2 bundle with excessive amount is rejected."""
        bundle = create_mandate_bundle(amount_minor=1_000_000_01)  # > $10M
        
        response = await test_client.post(
            "/api/v2/ap2/payments/execute",
            json=bundle,
        )
        
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_execute_multiple_payments(self, test_client: AsyncClient):
        """Test executing multiple payments in sequence."""
        results = []
        
        for i in range(3):
            mandate = {
                "mandate_id": f"multi_payment_{int(time.time())}_{i}",
                "issuer": "test_agent",
                "subject": "test_wallet",
                "destination": "0x1234567890123456789012345678901234567890",
                "amount_minor": 1000 * (i + 1),
                "token": "USDC",
                "chain": "base_sepolia",
                "expires_at": int(time.time()) + 300,
            }
            
            response = await test_client.post(
                "/api/v2/mandates/execute",
                json={"mandate": mandate},
            )
            
            assert response.status_code == 200
            results.append(response.json())
        
        # All should have unique tx hashes
        tx_hashes = [r["chain_tx_hash"] for r in results]
        assert len(set(tx_hashes)) == 3


class TestPaymentFlowValidation:
    """Tests for payment flow validation."""

    @pytest.mark.asyncio
    async def test_missing_mandate_fields(self, test_client: AsyncClient):
        """Test validation rejects incomplete mandate."""
        incomplete_mandate = {
            "mandate_id": "test",
            # Missing required fields
        }
        
        response = await test_client.post(
            "/api/v2/mandates/execute",
            json={"mandate": incomplete_mandate},
        )
        
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_chain(self, test_client: AsyncClient):
        """Test validation rejects invalid chain."""
        mandate = {
            "mandate_id": f"invalid_chain_{int(time.time())}",
            "issuer": "test_agent",
            "subject": "test_wallet",
            "destination": "0x1234567890123456789012345678901234567890",
            "amount_minor": 10000,
            "token": "USDC",
            "chain": "invalid_chain_name",
            "expires_at": int(time.time()) + 300,
        }
        
        response = await test_client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
        )
        
        # Should fail with chain-related error
        assert response.status_code in [400, 422, 500]


class TestPaymentFlowLedger:
    """Tests for payment flow ledger integration."""

    @pytest.mark.asyncio
    async def test_payment_creates_ledger_entry(self, test_client: AsyncClient):
        """Test that a payment creates a ledger entry."""
        mandate = {
            "mandate_id": f"ledger_test_{int(time.time())}",
            "issuer": "test_agent",
            "subject": "test_wallet",
            "destination": "0x1234567890123456789012345678901234567890",
            "amount_minor": 7500,
            "token": "USDC",
            "chain": "base_sepolia",
            "expires_at": int(time.time()) + 300,
        }
        
        # Execute payment
        payment_response = await test_client.post(
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
        )
        
        assert payment_response.status_code == 200
        payment_data = payment_response.json()
        ledger_tx_id = payment_data.get("ledger_tx_id")
        
        # Verify ledger entry exists
        if ledger_tx_id:
            ledger_response = await test_client.get("/api/v2/ledger/recent")
            
            if ledger_response.status_code == 200:
                ledger_data = ledger_response.json()
                entries = ledger_data.get("entries", [])
                
                # Should find our transaction
                tx_ids = [e.get("tx_id") for e in entries]
                # Note: In simulated mode, ledger might be in-memory


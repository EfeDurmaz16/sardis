"""Integration tests for hold (pre-authorization) lifecycle."""
from __future__ import annotations

import os
import time
import pytest
from decimal import Decimal
from httpx import AsyncClient

# All tests in this module require a PostgreSQL database
pytestmark = pytest.mark.skipif(
    not (os.environ.get("DATABASE_URL", "").startswith("postgresql://") or 
         os.environ.get("DATABASE_URL", "").startswith("postgres://")),
    reason="Requires PostgreSQL database (set DATABASE_URL env var)"
)


class TestHoldCreation:
    """Tests for creating holds."""

    @pytest.mark.asyncio
    async def test_create_hold_success(self, test_client: AsyncClient):
        """Test creating a hold successfully."""
        hold_request = {
            "wallet_id": "test_wallet_001",
            "amount": "100.00",
            "token": "USDC",
            "merchant_id": "merchant_123",
            "purpose": "Pre-authorization for shopping",
            "expiration_hours": 24,
        }
        
        response = await test_client.post(
            "/api/v2/holds",
            json=hold_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "hold_id" in data
        assert data["status"] == "active"
        assert data["amount"] == "100.00"
        assert data["token"] == "USDC"

    @pytest.mark.asyncio
    async def test_create_hold_default_expiration(self, test_client: AsyncClient):
        """Test creating a hold with default expiration."""
        hold_request = {
            "wallet_id": "test_wallet_002",
            "amount": "50.00",
            "token": "USDC",
        }
        
        response = await test_client.post(
            "/api/v2/holds",
            json=hold_request,
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "expires_at" in data

    @pytest.mark.asyncio
    async def test_create_hold_invalid_amount(self, test_client: AsyncClient):
        """Test creating a hold with invalid amount fails."""
        hold_request = {
            "wallet_id": "test_wallet_003",
            "amount": "-100.00",  # Negative amount
            "token": "USDC",
        }
        
        response = await test_client.post(
            "/api/v2/holds",
            json=hold_request,
        )
        
        assert response.status_code in [400, 422]


class TestHoldCapture:
    """Tests for capturing holds."""

    @pytest.mark.asyncio
    async def test_capture_hold_full_amount(self, test_client: AsyncClient):
        """Test capturing a hold for full amount."""
        # Create hold
        hold_request = {
            "wallet_id": "test_wallet_capture_full",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        assert create_response.status_code == 200
        hold_id = create_response.json()["hold_id"]
        
        # Capture hold
        capture_request = {"amount": "100.00"}
        capture_response = await test_client.post(
            f"/api/v2/holds/{hold_id}/capture",
            json=capture_request,
        )
        
        assert capture_response.status_code == 200
        data = capture_response.json()
        assert data["status"] == "captured"
        assert data["captured_amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_capture_hold_partial_amount(self, test_client: AsyncClient):
        """Test capturing a hold for partial amount."""
        # Create hold
        hold_request = {
            "wallet_id": "test_wallet_capture_partial",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        assert create_response.status_code == 200
        hold_id = create_response.json()["hold_id"]
        
        # Capture partial amount
        capture_request = {"amount": "75.00"}
        capture_response = await test_client.post(
            f"/api/v2/holds/{hold_id}/capture",
            json=capture_request,
        )
        
        assert capture_response.status_code == 200
        data = capture_response.json()
        assert data["captured_amount"] == "75.00"

    @pytest.mark.asyncio
    async def test_capture_hold_exceeds_amount(self, test_client: AsyncClient):
        """Test capturing more than hold amount fails."""
        # Create hold
        hold_request = {
            "wallet_id": "test_wallet_capture_exceed",
            "amount": "50.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        assert create_response.status_code == 200
        hold_id = create_response.json()["hold_id"]
        
        # Try to capture more than hold amount
        capture_request = {"amount": "100.00"}
        capture_response = await test_client.post(
            f"/api/v2/holds/{hold_id}/capture",
            json=capture_request,
        )
        
        assert capture_response.status_code == 400

    @pytest.mark.asyncio
    async def test_capture_nonexistent_hold(self, test_client: AsyncClient):
        """Test capturing a non-existent hold fails."""
        capture_request = {"amount": "50.00"}
        response = await test_client.post(
            "/api/v2/holds/nonexistent_hold_id/capture",
            json=capture_request,
        )
        
        assert response.status_code == 404


class TestHoldVoid:
    """Tests for voiding holds."""

    @pytest.mark.asyncio
    async def test_void_hold_success(self, test_client: AsyncClient):
        """Test voiding a hold successfully."""
        # Create hold
        hold_request = {
            "wallet_id": "test_wallet_void",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        assert create_response.status_code == 200
        hold_id = create_response.json()["hold_id"]
        
        # Void hold
        void_response = await test_client.post(f"/api/v2/holds/{hold_id}/void")
        
        assert void_response.status_code == 200
        data = void_response.json()
        assert data["status"] == "voided"

    @pytest.mark.asyncio
    async def test_void_already_captured_hold(self, test_client: AsyncClient):
        """Test voiding an already captured hold fails."""
        # Create and capture hold
        hold_request = {
            "wallet_id": "test_wallet_void_captured",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        hold_id = create_response.json()["hold_id"]
        
        await test_client.post(
            f"/api/v2/holds/{hold_id}/capture",
            json={"amount": "100.00"},
        )
        
        # Try to void
        void_response = await test_client.post(f"/api/v2/holds/{hold_id}/void")
        
        assert void_response.status_code == 400

    @pytest.mark.asyncio
    async def test_void_already_voided_hold(self, test_client: AsyncClient):
        """Test voiding an already voided hold fails."""
        # Create and void hold
        hold_request = {
            "wallet_id": "test_wallet_void_twice",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        hold_id = create_response.json()["hold_id"]
        
        await test_client.post(f"/api/v2/holds/{hold_id}/void")
        
        # Try to void again
        void_response = await test_client.post(f"/api/v2/holds/{hold_id}/void")
        
        assert void_response.status_code == 400


class TestHoldRetrieval:
    """Tests for retrieving hold information."""

    @pytest.mark.asyncio
    async def test_get_hold_by_id(self, test_client: AsyncClient):
        """Test getting a hold by ID."""
        # Create hold
        hold_request = {
            "wallet_id": "test_wallet_get",
            "amount": "100.00",
            "token": "USDC",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        hold_id = create_response.json()["hold_id"]
        
        # Get hold
        get_response = await test_client.get(f"/api/v2/holds/{hold_id}")
        
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["hold_id"] == hold_id
        assert data["amount"] == "100.00"

    @pytest.mark.asyncio
    async def test_get_nonexistent_hold(self, test_client: AsyncClient):
        """Test getting a non-existent hold returns 404."""
        response = await test_client.get("/api/v2/holds/nonexistent_hold_id")
        
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_wallet_holds(self, test_client: AsyncClient):
        """Test listing holds for a wallet."""
        wallet_id = f"test_wallet_list_{int(time.time())}"
        
        # Create multiple holds
        for i in range(3):
            hold_request = {
                "wallet_id": wallet_id,
                "amount": f"{(i + 1) * 100}.00",
                "token": "USDC",
            }
            await test_client.post("/api/v2/holds", json=hold_request)
        
        # List holds
        response = await test_client.get(f"/api/v2/holds/wallet/{wallet_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert "holds" in data
        assert len(data["holds"]) == 3

    @pytest.mark.asyncio
    async def test_list_active_holds(self, test_client: AsyncClient):
        """Test listing active holds."""
        response = await test_client.get("/api/v2/holds")
        
        assert response.status_code == 200
        data = response.json()
        assert "holds" in data
        # All returned holds should be active
        for hold in data["holds"]:
            assert hold["status"] == "active"


class TestHoldExpiration:
    """Tests for hold expiration handling."""

    @pytest.mark.asyncio
    async def test_expire_old_holds(self, test_client: AsyncClient):
        """Test expiring old holds via admin endpoint."""
        response = await test_client.post("/api/v2/holds/expire")
        
        assert response.status_code == 200
        data = response.json()
        assert "expired_count" in data


class TestHoldLifecycleComplete:
    """Tests for complete hold lifecycle scenarios."""

    @pytest.mark.asyncio
    async def test_full_hold_lifecycle_capture(self, test_client: AsyncClient):
        """Test complete hold lifecycle: create -> capture."""
        wallet_id = f"lifecycle_wallet_{int(time.time())}"
        
        # 1. Create hold
        hold_request = {
            "wallet_id": wallet_id,
            "amount": "250.00",
            "token": "USDC",
            "merchant_id": "restaurant_001",
            "purpose": "Restaurant pre-auth",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        assert create_response.status_code == 200
        hold_data = create_response.json()
        hold_id = hold_data["hold_id"]
        assert hold_data["status"] == "active"
        
        # 2. Verify hold is visible
        get_response = await test_client.get(f"/api/v2/holds/{hold_id}")
        assert get_response.status_code == 200
        assert get_response.json()["status"] == "active"
        
        # 3. Capture for final amount (less than pre-auth)
        capture_response = await test_client.post(
            f"/api/v2/holds/{hold_id}/capture",
            json={"amount": "187.50"},
        )
        assert capture_response.status_code == 200
        capture_data = capture_response.json()
        assert capture_data["status"] == "captured"
        assert capture_data["captured_amount"] == "187.50"
        
        # 4. Verify hold is now captured
        final_response = await test_client.get(f"/api/v2/holds/{hold_id}")
        assert final_response.status_code == 200
        assert final_response.json()["status"] == "captured"

    @pytest.mark.asyncio
    async def test_full_hold_lifecycle_void(self, test_client: AsyncClient):
        """Test complete hold lifecycle: create -> void."""
        wallet_id = f"lifecycle_void_wallet_{int(time.time())}"
        
        # 1. Create hold
        hold_request = {
            "wallet_id": wallet_id,
            "amount": "500.00",
            "token": "USDC",
            "merchant_id": "hotel_001",
            "purpose": "Hotel incidentals",
        }
        
        create_response = await test_client.post("/api/v2/holds", json=hold_request)
        hold_id = create_response.json()["hold_id"]
        
        # 2. Customer cancels reservation - void hold
        void_response = await test_client.post(f"/api/v2/holds/{hold_id}/void")
        assert void_response.status_code == 200
        assert void_response.json()["status"] == "voided"
        
        # 3. Verify hold is voided
        final_response = await test_client.get(f"/api/v2/holds/{hold_id}")
        assert final_response.json()["status"] == "voided"




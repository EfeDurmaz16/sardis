"""
Tests for HoldsResource
"""
import pytest
from decimal import Decimal
from sardis_sdk import SardisClient


class TestCreateHold:
    """Tests for hold creation."""

    async def test_create_hold_successfully(self, client, httpx_mock, mock_responses):
        """Should create a hold."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds",
            method="POST",
            json={"hold_id": "hold_xyz789", "status": "active", "expires_at": "2025-01-21T00:00:00Z"},
        )

        result = await client.holds.create(
            wallet_id="wallet_test123",
            amount=Decimal("100.00"),
            token="USDC",
        )

        assert result.hold_id == "hold_xyz789"
        assert result.status == "active"


class TestGetHold:
    """Tests for getting hold by ID."""

    async def test_get_hold_successfully(self, client, httpx_mock, mock_responses):
        """Should get hold by ID."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/hold_xyz789",
            method="GET",
            json=mock_responses["hold"],
        )

        result = await client.holds.get("hold_xyz789")

        assert result.hold_id == "hold_xyz789"

    async def test_handle_hold_not_found(self, client, httpx_mock):
        """Should handle hold not found."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/nonexistent",
            method="GET",
            status_code=404,
            json={"error": "Hold not found"},
        )

        with pytest.raises(Exception):
            await client.holds.get("nonexistent")


class TestCaptureHold:
    """Tests for capturing holds."""

    async def test_capture_hold_successfully(self, client, httpx_mock, mock_responses):
        """Should capture a hold."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/hold_xyz789/capture",
            method="POST",
            json={**mock_responses["hold"], "status": "captured"},
        )

        result = await client.holds.capture("hold_xyz789")

        assert result.status == "captured"

    async def test_capture_with_partial_amount(self, client, httpx_mock, mock_responses):
        """Should capture with partial amount."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/hold_xyz789/capture",
            method="POST",
            json={**mock_responses["hold"], "status": "captured", "amount": "50.00"},
        )

        result = await client.holds.capture("hold_xyz789", amount=Decimal("50.00"))

        assert result.status == "captured"


class TestVoidHold:
    """Tests for voiding holds."""

    async def test_void_hold_successfully(self, client, httpx_mock, mock_responses):
        """Should void a hold."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/hold_xyz789/void",
            method="POST",
            json={**mock_responses["hold"], "status": "voided"},
        )

        result = await client.holds.void("hold_xyz789")

        assert result.status == "voided"

    async def test_handle_void_of_captured_hold(self, client, httpx_mock):
        """Should handle void of already captured hold."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/hold_captured/void",
            method="POST",
            status_code=409,
            json={"error": "Hold already captured"},
        )

        with pytest.raises(Exception):
            await client.holds.void("hold_captured")


class TestListHolds:
    """Tests for listing holds."""

    async def test_list_holds_by_wallet(self, client, httpx_mock, mock_responses):
        """Should list holds for a wallet."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/wallet/wallet_test123",
            method="GET",
            json={"holds": [mock_responses["hold"], {**mock_responses["hold"], "id": "hold_2"}]},
        )

        result = await client.holds.list_by_wallet("wallet_test123")

        assert len(result) == 2

    async def test_return_empty_list_when_no_holds(self, client, httpx_mock):
        """Should return empty list when no holds."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds/wallet/wallet_empty",
            method="GET",
            json={"holds": []},
        )

        result = await client.holds.list_by_wallet("wallet_empty")

        assert result == []

    async def test_list_active_holds(self, client, httpx_mock, mock_responses):
        """Should list all active holds."""
        httpx_mock.add_response(
            url="https://api.sardis.sh/api/v2/holds",
            method="GET",
            json={"holds": [mock_responses["hold"]]},
        )

        result = await client.holds.list_active()

        assert len(result) == 1

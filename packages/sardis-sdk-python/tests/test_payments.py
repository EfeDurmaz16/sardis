"""
Tests for PaymentsResource
"""
import pytest
from sardis_sdk import SardisClient


class TestExecuteMandate:
    """Tests for execute_mandate method."""

    async def test_execute_mandate_successfully(self, client, httpx_mock, mock_responses):
        """Should execute a payment mandate."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/mandates/execute",
            method="POST",
            json=mock_responses["mandate"],
        )

        mandate = {
            "mandate_id": "test-mandate",
            "subject": "wallet_123",
            "destination": "merchant_456",
            "amount_minor": 1000000,
            "token": "USDC",
            "chain": "base_sepolia",
        }

        result = await client.payments.execute_mandate(mandate)

        assert result.id == "mandate_abc123"
        assert result.status == "completed"

    async def test_handle_mandate_failure(self, client, httpx_mock):
        """Should handle mandate execution failure."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/mandates/execute",
            method="POST",
            status_code=403,
            json={"error": "Policy violation", "code": "POLICY_VIOLATION"},
        )

        mandate = {
            "mandate_id": "test-mandate",
            "subject": "wallet_123",
            "destination": "blocked_merchant",
            "amount_minor": 1000000,
            "token": "USDC",
            "chain": "base_sepolia",
        }

        with pytest.raises(Exception):
            await client.payments.execute_mandate(mandate)


class TestExecuteAP2:
    """Tests for execute_ap2 method."""

    async def test_execute_ap2_successfully(self, client, httpx_mock, mock_responses):
        """Should execute an AP2 payment."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/ap2/payments/execute",
            method="POST",
            json=mock_responses["mandate"],
        )

        intent = {"type": "subscription", "service": "OpenAI"}
        cart = {"items": [{"name": "API Credits", "quantity": 1, "price": 20}]}
        payment = {"wallet_id": "wallet_123", "amount_minor": 2000000000}

        result = await client.payments.execute_ap2(intent, cart, payment)

        assert result.status == "completed"


class TestExecuteAP2Bundle:
    """Tests for execute_ap2_bundle method."""

    async def test_execute_ap2_bundle_successfully(self, client, httpx_mock, mock_responses):
        """Should execute a pre-built AP2 bundle."""
        httpx_mock.add_response(
            url="https://api.sardis.network/api/v2/ap2/payments/execute",
            method="POST",
            json=mock_responses["mandate"],
        )

        bundle = {
            "intent": {"type": "service_payment"},
            "cart": {"items": []},
            "payment": {"wallet_id": "wallet_123", "amount_minor": 5000000000},
        }

        result = await client.payments.execute_ap2_bundle(bundle)

        assert result.status == "completed"

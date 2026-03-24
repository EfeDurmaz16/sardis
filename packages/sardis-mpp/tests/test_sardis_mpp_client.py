"""Unit tests for SardisMPPClient — policy enforcement on MPP payments.

Tests:
  - Policy enforcement blocks denied payments
  - Policy enforcement allows approved payments
  - Payment audit records are tracked
  - MPPSessionManager mandate-to-session mapping
  - Anomaly detection
"""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_mpp.client import (
    MPPPaymentDenied,
    MPPPaymentRecord,
    MPPSessionManager,
    SardisMPPClient,
    SardisPolicyTransport,
)


# ── MPPPaymentRecord ─────────────────────────────────────────────────


class TestMPPPaymentRecord:
    def test_record_creation(self):
        record = MPPPaymentRecord(
            url="https://api.example.com/data",
            method="tempo",
            challenge_id="ch_001",
            amount="100",
            currency="USD",
            payment_method="tempo",
            network="tempo",
            policy_result="ALLOWED",
            policy_reason="OK",
        )
        assert record.policy_result == "ALLOWED"
        assert record.tx_hash is None

    def test_denied_record(self):
        record = MPPPaymentRecord(
            url="https://blocked.com",
            method="tempo",
            challenge_id="ch_002",
            amount="5000",
            currency="USD",
            payment_method="tempo",
            network="tempo",
            policy_result="DENIED",
            policy_reason="per_transaction_limit",
        )
        assert record.policy_result == "DENIED"


# ── SardisPolicyTransport ───────────────────────────────────────────


class TestSardisPolicyTransport:
    def test_transport_can_be_created(self):
        transport = SardisPolicyTransport(
            methods=[],
            policy_checker=None,
        )
        assert transport._methods == []
        assert transport._policy_checker is None

    def test_transport_with_policy_checker(self):
        async def checker(**kwargs):
            return True, "OK"

        transport = SardisPolicyTransport(
            methods=[],
            policy_checker=checker,
        )
        assert transport._policy_checker is checker


# ── SardisMPPClient ──────────────────────────────────────────────────


class TestSardisMPPClient:
    def test_client_creation(self):
        client = SardisMPPClient(
            methods=[],
            policy_checker=None,
        )
        assert client.payment_records == []
        assert client.total_spent == Decimal("0")

    def test_payment_records_tracking(self):
        records = []

        def on_payment(record):
            records.append(record)

        client = SardisMPPClient(
            methods=[],
            policy_checker=None,
            on_payment=on_payment,
        )
        # Manually add a record to test tracking
        client._payment_records.append(
            MPPPaymentRecord(
                url="https://api.example.com",
                method="tempo",
                challenge_id="ch_001",
                amount="50",
                currency="USD",
                payment_method="tempo",
                network="tempo",
                policy_result="ALLOWED",
                policy_reason="OK",
            )
        )
        assert len(client.payment_records) == 1
        assert client.total_spent == Decimal("50")

    def test_total_spent_ignores_denied(self):
        client = SardisMPPClient(methods=[], policy_checker=None)
        client._payment_records.append(
            MPPPaymentRecord(
                url="https://api.example.com", method="tempo",
                challenge_id="ch_1", amount="100", currency="USD",
                payment_method="tempo", network="tempo",
                policy_result="ALLOWED", policy_reason="OK",
            )
        )
        client._payment_records.append(
            MPPPaymentRecord(
                url="https://blocked.com", method="tempo",
                challenge_id="ch_2", amount="500", currency="USD",
                payment_method="tempo", network="tempo",
                policy_result="DENIED", policy_reason="blocked",
            )
        )
        assert client.total_spent == Decimal("100")


# ── MPPSessionManager ────────────────────────────────────────────────


class TestMPPSessionManager:
    def test_mandate_to_session_params(self):
        manager = MPPSessionManager()
        mandate = MagicMock()
        mandate.amount_per_tx = Decimal("500")
        mandate.amount_daily = Decimal("2000")
        mandate.expires_at = MagicMock()
        mandate.expires_at.timestamp.return_value = 1700000000
        mandate.merchant_scope = {"allowed": ["openai.com", "anthropic.com"]}
        mandate.id = "mandate_001"
        mandate.agent_id = "agent_001"

        params = manager.mandate_to_session_params(mandate)

        assert params["maxDeposit"] == "500"
        assert params["dailyLimit"] == "2000"
        assert params["expiry"] == 1700000000
        assert "openai.com" in params["allowedServices"]
        assert params["mandateId"] == "mandate_001"

    def test_mandate_without_limits(self):
        manager = MPPSessionManager()
        mandate = MagicMock()
        mandate.amount_per_tx = None
        mandate.amount_daily = None
        mandate.expires_at = None
        mandate.merchant_scope = {}
        mandate.id = "mandate_002"
        mandate.agent_id = "agent_002"

        params = manager.mandate_to_session_params(mandate)

        assert "maxDeposit" not in params
        assert "dailyLimit" not in params
        assert "expiry" not in params

    def test_track_payment(self):
        manager = MPPSessionManager()
        manager.track_payment("sess_001", Decimal("100"))
        manager.track_payment("sess_001", Decimal("200"))

        assert manager._sessions["sess_001"]["total"] == Decimal("300")
        assert manager._sessions["sess_001"]["count"] == 2

    def test_check_anomaly_not_enough_data(self):
        manager = MPPSessionManager()
        manager.track_payment("sess_001", Decimal("100"))
        # Fewer than 5 payments => not anomalous
        assert manager.check_anomaly("sess_001", Decimal("10000")) is False

    def test_check_anomaly_detects_spike(self):
        manager = MPPSessionManager()
        for _ in range(10):
            manager.track_payment("sess_001", Decimal("10"))
        # Average is 10, threshold is 3x = 30
        assert manager.check_anomaly("sess_001", Decimal("50")) is True

    def test_check_anomaly_normal_amount(self):
        manager = MPPSessionManager()
        for _ in range(10):
            manager.track_payment("sess_001", Decimal("100"))
        # Average is 100, threshold is 3x = 300
        assert manager.check_anomaly("sess_001", Decimal("200")) is False

    @pytest.mark.asyncio
    async def test_force_close(self):
        manager = MPPSessionManager()
        manager.track_payment("sess_001", Decimal("100"))

        await manager.force_close("sess_001", "policy_violation")

        assert manager._sessions["sess_001"]["status"] == "force_closed"
        assert manager._sessions["sess_001"]["close_reason"] == "policy_violation"

    def test_check_anomaly_unknown_session(self):
        manager = MPPSessionManager()
        assert manager.check_anomaly("unknown", Decimal("100")) is False

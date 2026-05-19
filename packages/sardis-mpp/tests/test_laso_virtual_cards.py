"""Unit tests for LasoMPPService — Laso Finance virtual card integration.

Tests:
  - Card issuance with amount validation
  - Daily limit enforcement
  - Card data retrieval returns typed LasoCard
  - Balance retrieval returns typed LasoBalance
  - Session token extraction from x402 response
  - Payment method validation (Venmo/PayPal)
  - _request routing through SardisMPPClient (not _http directly)
  - LasoCard helper methods (masked_number, is_ready)
  - Error class construction
"""
from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_mpp.services.laso import (
    LASO_MAX_DAILY_CARDS,
    LasoBalance,
    LasoCard,
    LasoCardNotReady,
    LasoLimitExceeded,
    LasoMPPService,
    LasoPayment,
    LasoPaymentRequired,
)

# ── LasoCard dataclass ──────────────────────────────────────────────


class TestLasoCard:
    def test_card_creation(self):
        card = LasoCard(
            card_id="card_001",
            card_number="4111111111111234",
            cvv="456",
            expiry="12/27",
            amount=Decimal("100"),
            currency="USD",
            status="ready",
        )
        assert card.card_id == "card_001"
        assert card.card_number == "4111111111111234"
        assert card.cvv == "456"
        assert card.amount == Decimal("100")

    def test_masked_number(self):
        card = LasoCard(
            card_id="c1", card_number="4111111111111234",
            cvv="123", expiry="12/27", amount=Decimal("50"),
            currency="USD", status="ready",
        )
        assert card.masked_number() == "************1234"

    def test_masked_number_short(self):
        card = LasoCard(
            card_id="c2", card_number="12",
            cvv="1", expiry="", amount=Decimal("5"),
            currency="USD", status="ready",
        )
        # Short numbers returned as-is
        assert card.masked_number() == "12"

    def test_is_ready_true(self):
        for s in ("ready", "active", "funded"):
            card = LasoCard(
                card_id="c", card_number="", cvv="", expiry="",
                amount=Decimal("10"), currency="USD", status=s,
            )
            assert card.is_ready is True, f"status={s} should be ready"

    def test_is_ready_false(self):
        for s in ("processing", "used", "expired", "unknown"):
            card = LasoCard(
                card_id="c", card_number="", cvv="", expiry="",
                amount=Decimal("10"), currency="USD", status=s,
            )
            assert card.is_ready is False, f"status={s} should not be ready"

    def test_default_fields(self):
        card = LasoCard(
            card_id="c", card_number="", cvv="", expiry="",
            amount=Decimal("10"), currency="USD", status="ready",
        )
        assert card.card_type == "single_use"
        assert card.billing_address == {}
        assert card.created_at == ""


# ── LasoBalance dataclass ───────────────────────────────────────────


class TestLasoBalance:
    def test_balance_creation(self):
        balance = LasoBalance(
            available=Decimal("500.50"),
            pending=Decimal("10.00"),
            currency="USD",
        )
        assert balance.available == Decimal("500.50")
        assert balance.pending == Decimal("10.00")
        assert balance.currency == "USD"


# ── Exception classes ───────────────────────────────────────────────


class TestExceptions:
    def test_payment_required(self):
        exc = LasoPaymentRequired(
            challenge="Bearer realm=\"test\"",
            amount=Decimal("0.001"),
        )
        assert exc.amount == Decimal("0.001")
        assert "test" in exc.challenge
        assert "0.001" in str(exc)

    def test_limit_exceeded(self):
        exc = LasoLimitExceeded("Daily card limit reached")
        assert "Daily card limit" in str(exc)

    def test_card_not_ready(self):
        exc = LasoCardNotReady(card_id="card_123", status="processing")
        assert exc.card_id == "card_123"
        assert exc.status == "processing"
        assert "card_123" in str(exc)


# ── LasoMPPService init ────────────────────────────────────────────


class TestLasoMPPServiceInit:
    def test_default_base_url(self):
        svc = LasoMPPService()
        assert "paywithlocus.com" in svc.base_url
        assert svc.session_token is None
        assert svc._mpp_client is None

    def test_custom_base_url(self):
        svc = LasoMPPService(base_url="https://custom.api.com/mpp/")
        assert svc.base_url == "https://custom.api.com/mpp"

    def test_with_session_token(self):
        svc = LasoMPPService(session_token="tok_abc")
        assert svc.session_token == "tok_abc"

    def test_with_policy_checker(self):
        checker = AsyncMock(return_value=(True, "OK"))
        svc = LasoMPPService(policy_checker=checker)
        assert svc._policy_checker is checker


# ── Amount validation ───────────────────────────────────────────────


class TestAmountValidation:
    @pytest.mark.asyncio
    async def test_issue_card_below_minimum(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="between"):
            await svc.issue_card(amount=Decimal("4"))

    @pytest.mark.asyncio
    async def test_issue_card_above_maximum(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="between"):
            await svc.issue_card(amount=Decimal("1001"))

    @pytest.mark.asyncio
    async def test_issue_card_invalid_type(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="card_type"):
            await svc.issue_card(amount=Decimal("100"), card_type="invalid")

    @pytest.mark.asyncio
    async def test_send_payment_below_minimum(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="between"):
            await svc.send_payment(
                amount=Decimal("4"), method="venmo", recipient="+1234567890"
            )

    @pytest.mark.asyncio
    async def test_send_payment_above_maximum(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="between"):
            await svc.send_payment(
                amount=Decimal("1001"), method="paypal", recipient="a@b.com"
            )

    @pytest.mark.asyncio
    async def test_send_payment_invalid_method(self):
        svc = LasoMPPService()
        with pytest.raises(ValueError, match="Method"):
            await svc.send_payment(
                amount=Decimal("50"), method="bitcoin", recipient="addr"
            )


# ── Daily limit enforcement ─────────────────────────────────────────


class TestDailyLimits:
    @staticmethod
    def _today() -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d")

    def test_check_daily_limits_fresh(self):
        svc = LasoMPPService()
        # Should not raise
        svc._check_daily_limits(Decimal("500"))

    def test_check_daily_limits_card_count(self):
        svc = LasoMPPService()
        svc._cards_issued_today = LASO_MAX_DAILY_CARDS
        svc._last_reset = self._today()
        with pytest.raises(LasoLimitExceeded, match="card limit"):
            svc._check_daily_limits(Decimal("100"))

    def test_check_daily_limits_amount(self):
        svc = LasoMPPService()
        svc._daily_amount = Decimal("5500")
        svc._last_reset = self._today()
        with pytest.raises(LasoLimitExceeded, match="amount limit"):
            svc._check_daily_limits(Decimal("600"))

    def test_daily_limits_reset_on_new_day(self):
        svc = LasoMPPService()
        svc._cards_issued_today = 10
        svc._daily_amount = Decimal("9999")
        svc._last_reset = "2026-03-24"  # Yesterday
        # Should not raise — limits reset on new day
        svc._check_daily_limits(Decimal("100"))
        assert svc._cards_issued_today == 0
        assert svc._daily_amount == Decimal("0")


# ── _request routing ────────────────────────────────────────────────


class TestRequestRouting:
    """Verify that _request goes through SardisMPPClient.post()/get()
    (not _http directly) so the SardisPolicyTransport can handle x402.
    """

    @pytest.mark.asyncio
    async def test_request_uses_mpp_client_post(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        result = await svc._request("POST", "/get-card", json_data={"amount": "100"})

        # Verify we called mpp_client.post(), not mpp_client._http.post()
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "/get-card" in call_args[0][0]
        assert result == {"ok": True}

    @pytest.mark.asyncio
    async def test_request_uses_mpp_client_get(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"balance": "100"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        result = await svc._request("GET", "/get-account-balance")

        mock_client.get.assert_called_once()
        assert result == {"balance": "100"}

    @pytest.mark.asyncio
    async def test_request_extracts_session_token(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "sess_xyz", "ok": True}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        await svc._request("POST", "/get-card", json_data={})

        assert svc.session_token == "sess_xyz"

    @pytest.mark.asyncio
    async def test_request_sends_session_token_in_header(self):
        svc = LasoMPPService(session_token="sess_existing")
        mock_response = MagicMock()
        mock_response.json.return_value = {"ok": True}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        await svc._request("POST", "/get-card-data", json_data={"card_id": "c1"})

        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["headers"]["Authorization"] == "Bearer sess_existing"

    @pytest.mark.asyncio
    async def test_request_raises_on_402_after_transport(self):
        """If transport cannot fulfill the 402, LasoPaymentRequired is raised."""
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {}
        mock_response.status_code = 402
        mock_response.headers = {"WWW-Authenticate": "Bearer realm=\"test\""}
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        with pytest.raises(LasoPaymentRequired):
            await svc._request("POST", "/get-card", json_data={})


# ── issue_card integration ──────────────────────────────────────────


class TestIssueCard:
    @pytest.mark.asyncio
    async def test_issue_card_success(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "card_id": "card_abc",
            "card_number": "4111111111111111",
            "cvv": "789",
            "expiry": "03/28",
            "amount": "100",
            "currency": "USD",
            "status": "ready",
            "billing_address": {"zip": "10001"},
            "created_at": "2026-03-25T12:00:00Z",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        card = await svc.issue_card(amount=Decimal("100"))

        assert card.card_id == "card_abc"
        assert card.card_number == "4111111111111111"
        assert card.cvv == "789"
        assert card.expiry == "03/28"
        assert card.amount == Decimal("100")
        assert card.status == "ready"
        assert card.billing_address == {"zip": "10001"}
        assert svc._cards_issued_today == 1
        assert svc._daily_amount == Decimal("100")

    @pytest.mark.asyncio
    async def test_issue_card_polls_when_processing(self):
        svc = LasoMPPService()

        # First response: processing
        processing_resp = MagicMock()
        processing_resp.json.return_value = {
            "card_id": "card_poll",
            "status": "processing",
        }
        processing_resp.status_code = 200
        processing_resp.raise_for_status = MagicMock()

        # Poll responses: ready on second attempt
        ready_resp = MagicMock()
        ready_resp.json.return_value = {
            "card_id": "card_poll",
            "card_number": "4222222222222222",
            "cvv": "321",
            "expiry": "06/28",
            "amount": "50",
            "currency": "USD",
            "status": "ready",
        }
        ready_resp.status_code = 200
        ready_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[processing_resp, ready_resp]
        )
        svc._mpp_client = mock_client

        # Patch asyncio.sleep to avoid real delay
        with patch("sardis_mpp.services.laso.asyncio.sleep", new_callable=AsyncMock):
            card = await svc.issue_card(amount=Decimal("50"))

        assert card.card_id == "card_poll"
        assert card.status == "ready"
        assert card.card_number == "4222222222222222"

    @pytest.mark.asyncio
    async def test_issue_card_multi_use(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "card_id": "card_mu",
            "card_number": "4333333333333333",
            "cvv": "111",
            "expiry": "09/28",
            "amount": "200",
            "currency": "USD",
            "status": "ready",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        card = await svc.issue_card(amount=Decimal("200"), card_type="multi_use")

        assert card.card_type == "multi_use"


# ── get_card_data ───────────────────────────────────────────────────


class TestGetCardData:
    @pytest.mark.asyncio
    async def test_get_card_data_returns_laso_card(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "card_number": "4444555566667777",
            "cvv": "999",
            "expiry": "01/29",
            "amount": "75",
            "currency": "USD",
            "status": "active",
            "type": "single_use",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        card = await svc.get_card_data("card_test")

        assert isinstance(card, LasoCard)
        assert card.card_id == "card_test"
        assert card.card_number == "4444555566667777"
        assert card.status == "active"
        assert card.is_ready is True


# ── get_balance ─────────────────────────────────────────────────────


class TestGetBalance:
    @pytest.mark.asyncio
    async def test_get_balance_returns_typed(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "available": "250.50",
            "pending": "10",
            "currency": "USD",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        balance = await svc.get_balance()

        assert isinstance(balance, LasoBalance)
        assert balance.available == Decimal("250.50")
        assert balance.pending == Decimal("10")

    @pytest.mark.asyncio
    async def test_get_balance_fallback_field(self):
        """Some Laso responses use 'balance' instead of 'available'."""
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "balance": "100",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        balance = await svc.get_balance()
        assert balance.available == Decimal("100")


# ── send_payment ────────────────────────────────────────────────────


class TestSendPayment:
    @pytest.mark.asyncio
    async def test_send_venmo(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "payment_id": "pay_001",
            "amount": "25",
            "status": "pending_confirmation",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        payment = await svc.send_payment(
            amount=Decimal("25"), method="venmo", recipient="+15551234567"
        )

        assert isinstance(payment, LasoPayment)
        assert payment.method == "venmo"
        assert payment.recipient == "+15551234567"

    @pytest.mark.asyncio
    async def test_send_paypal(self):
        svc = LasoMPPService()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "payment_id": "pay_002",
            "amount": "50",
            "status": "pending_confirmation",
        }
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        payment = await svc.send_payment(
            amount=Decimal("50"), method="paypal", recipient="user@example.com"
        )

        assert payment.method == "paypal"
        assert payment.recipient == "user@example.com"


# ── refresh_session ─────────────────────────────────────────────────


class TestRefreshSession:
    @pytest.mark.asyncio
    async def test_refresh_session(self):
        svc = LasoMPPService(session_token="old_token")
        mock_response = MagicMock()
        mock_response.json.return_value = {"token": "new_token"}
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        svc._mpp_client = mock_client

        new_token = await svc.refresh_session()

        assert new_token == "new_token"
        assert svc.session_token == "new_token"


# ── close ───────────────────────────────────────────────────────────


class TestClose:
    @pytest.mark.asyncio
    async def test_close_cleans_up(self):
        svc = LasoMPPService()
        mock_client = AsyncMock()
        mock_client.close = AsyncMock()
        svc._mpp_client = mock_client

        await svc.close()

        mock_client.close.assert_called_once()
        assert svc._mpp_client is None

    @pytest.mark.asyncio
    async def test_close_noop_when_no_client(self):
        svc = LasoMPPService()
        # Should not raise
        await svc.close()

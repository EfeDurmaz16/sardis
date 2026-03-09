"""Tests for Bridge multi-rail support and BridgeCardFundingAdapter.

Coverage:
- BridgeProvider.get_available_rails() with various constructor flag combinations
- BridgeProvider.create_offramp() routed to different rails (ach, sepa)
- BridgeProvider.create_offramp() raises on unsupported / disabled rails
- BridgeCardFundingAdapter.fund() with respx-mocked HTTP
- BridgeCardFundingAdapter.quote() — synthetic quote computation
- BridgeCardFundingAdapter.status() — GET status endpoint
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
import respx

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_bridge_provider(**kwargs):
    """Construct a BridgeProvider with mocked SardisFiatRamp internals."""
    from sardis_ramp.providers.bridge_provider import BridgeProvider

    provider = BridgeProvider(
        sardis_api_key="sk_test",
        bridge_api_key="bridge_test",
        **kwargs,
    )
    # Inject a mock ramp so HTTP calls don't escape
    mock_ramp = AsyncMock()
    provider._ramp = mock_ramp
    return provider, mock_ramp


def _withdrawal_result(payout_id: str = "payout_001", tx_hash: str = "0xabc") -> MagicMock:
    result = MagicMock()
    result.payout_id = payout_id
    result.tx_hash = tx_hash
    return result


BANK = {
    "account_holder_name": "Alice Smith",
    "account_number": "1234567890",
    "routing_number": "021000021",
    "account_type": "checking",
}

# ── BridgeProvider.get_available_rails ───────────────────────────────────────


class TestGetAvailableRails:
    def test_default_is_ach_only(self):
        provider, _ = _make_bridge_provider()
        assert provider.get_available_rails() == ["ach"]

    def test_all_disabled_except_sepa(self):
        provider, _ = _make_bridge_provider(ach_enabled=False, sepa_enabled=True)
        assert provider.get_available_rails() == ["sepa"]

    def test_all_enabled(self):
        provider, _ = _make_bridge_provider(
            ach_enabled=True, sepa_enabled=True, pix_enabled=True, wire_enabled=True
        )
        rails = provider.get_available_rails()
        assert rails == ["ach", "sepa", "pix", "wire"]

    def test_pix_only(self):
        provider, _ = _make_bridge_provider(ach_enabled=False, pix_enabled=True)
        assert provider.get_available_rails() == ["pix"]

    def test_ach_and_wire(self):
        provider, _ = _make_bridge_provider(wire_enabled=True)
        rails = provider.get_available_rails()
        assert "ach" in rails
        assert "wire" in rails
        assert "sepa" not in rails
        assert "pix" not in rails

    def test_all_disabled_returns_empty(self):
        provider, _ = _make_bridge_provider(ach_enabled=False)
        assert provider.get_available_rails() == []


# ── BridgeProvider.create_offramp ────────────────────────────────────────────


class TestCreateOfframpRails:
    @pytest.mark.asyncio
    async def test_default_rail_is_ach(self):
        provider, mock_ramp = _make_bridge_provider()
        mock_ramp.withdraw_to_bank = AsyncMock(return_value=_withdrawal_result())

        session = await provider.create_offramp(
            amount_crypto=Decimal("100"),
            crypto_currency="USDC",
            chain="base",
            fiat_currency="USD",
            bank_account=BANK,
            wallet_id="wal_001",
        )

        assert session.metadata["rail"] == "ach"
        mock_ramp.withdraw_to_bank.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_sepa_rail_stored_in_metadata(self):
        provider, mock_ramp = _make_bridge_provider(sepa_enabled=True)
        mock_ramp.withdraw_to_bank = AsyncMock(return_value=_withdrawal_result("payout_sepa"))

        session = await provider.create_offramp(
            amount_crypto=Decimal("250"),
            crypto_currency="USDC",
            chain="base",
            fiat_currency="EUR",
            bank_account=BANK,
            wallet_id="wal_002",
            rail="sepa",
        )

        assert session.metadata["rail"] == "sepa"
        assert session.session_id == "payout_sepa"
        assert session.fiat_currency == "EUR"

    @pytest.mark.asyncio
    async def test_extra_metadata_is_preserved(self):
        provider, mock_ramp = _make_bridge_provider()
        mock_ramp.withdraw_to_bank = AsyncMock(return_value=_withdrawal_result())

        session = await provider.create_offramp(
            amount_crypto=Decimal("50"),
            crypto_currency="USDC",
            chain="base",
            fiat_currency="USD",
            bank_account=BANK,
            wallet_id="wal_003",
            metadata={"order_id": "ord_999"},
            rail="ach",
        )

        assert session.metadata["rail"] == "ach"
        assert session.metadata["order_id"] == "ord_999"

    @pytest.mark.asyncio
    async def test_raises_when_rail_not_enabled(self):
        provider, mock_ramp = _make_bridge_provider(sepa_enabled=False)

        with pytest.raises(ValueError, match="Rail 'sepa' is not enabled"):
            await provider.create_offramp(
                amount_crypto=Decimal("100"),
                crypto_currency="USDC",
                chain="base",
                fiat_currency="EUR",
                bank_account=BANK,
                wallet_id="wal_004",
                rail="sepa",
            )
        mock_ramp.withdraw_to_bank.assert_not_called()

    @pytest.mark.asyncio
    async def test_raises_on_unknown_rail(self):
        provider, mock_ramp = _make_bridge_provider()

        with pytest.raises(ValueError, match="Unknown rail 'swift'"):
            await provider.create_offramp(
                amount_crypto=Decimal("100"),
                crypto_currency="USDC",
                chain="base",
                fiat_currency="USD",
                bank_account=BANK,
                wallet_id="wal_005",
                rail="swift",  # not a supported rail name
            )

    @pytest.mark.asyncio
    async def test_raises_without_wallet_id(self):
        provider, _ = _make_bridge_provider()

        with pytest.raises(ValueError, match="wallet_id required"):
            await provider.create_offramp(
                amount_crypto=Decimal("100"),
                crypto_currency="USDC",
                chain="base",
                fiat_currency="USD",
                bank_account=BANK,
            )

    @pytest.mark.asyncio
    async def test_wire_rail(self):
        provider, mock_ramp = _make_bridge_provider(wire_enabled=True)
        mock_ramp.withdraw_to_bank = AsyncMock(return_value=_withdrawal_result("payout_wire"))

        session = await provider.create_offramp(
            amount_crypto=Decimal("5000"),
            crypto_currency="USDC",
            chain="ethereum",
            fiat_currency="USD",
            bank_account=BANK,
            wallet_id="wal_006",
            rail="wire",
        )

        assert session.metadata["rail"] == "wire"


# ── BridgeCardFundingAdapter ─────────────────────────────────────────────────


BASE_URL = "https://api.bridge.xyz/v0"
FUND_PATH = "/transfers"
FUND_URL = f"{BASE_URL}/transfers"
STATUS_URL = f"{BASE_URL}/transfers/txn_abc123"


def _make_adapter(**kwargs) -> BridgeCardFundingAdapter:  # noqa: F821
    from sardis_v2_core.delegated_adapters.bridge_cards import BridgeCardFundingAdapter

    defaults = {
        "api_key": "bridge_api_key_test",
        "base_url": BASE_URL,
        "funding_path": FUND_PATH,
    }
    defaults.update(kwargs)
    return BridgeCardFundingAdapter(**defaults)


def _funding_request(**overrides) -> FundingRequest:  # noqa: F821
    from sardis_v2_core.funding import FundingRequest

    defaults = {
        "amount": Decimal("500.00"),
        "currency": "USD",
        "description": "Card pre-fund",
        "metadata": {"wallet_id": "wal_card_001"},
    }
    defaults.update(overrides)
    return FundingRequest(**defaults)


class TestBridgeCardFundingAdapterProperties:
    def test_provider_name(self):
        adapter = _make_adapter()
        assert adapter.provider == "bridge_cards"

    def test_rail_is_fiat(self):
        adapter = _make_adapter()
        assert adapter.rail == "fiat"

    def test_missing_api_key_raises(self):
        from sardis_v2_core.delegated_adapters.bridge_cards import BridgeCardFundingAdapter

        with pytest.raises(ValueError, match="api_key is required"):
            BridgeCardFundingAdapter(api_key="", base_url=BASE_URL)

    def test_missing_base_url_raises(self):
        from sardis_v2_core.delegated_adapters.bridge_cards import BridgeCardFundingAdapter

        with pytest.raises(ValueError, match="base_url is required"):
            BridgeCardFundingAdapter(api_key="key", base_url="")


class TestBridgeCardFundingAdapterFund:
    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_success(self):
        respx.post(FUND_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "txn_abc123",
                    "amount": "500.00",
                    "currency": "USD",
                    "status": "processing",
                },
            )
        )

        adapter = _make_adapter()
        result = await adapter.fund(_funding_request())

        assert result.provider == "bridge_cards"
        assert result.rail == "fiat"
        assert result.transfer_id == "txn_abc123"
        assert result.amount == Decimal("500.00")
        assert result.currency == "USD"
        assert result.status == "processing"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_uses_transfer_id_fallback_fields(self):
        """Adapter should accept ``transfer_id`` or ``payout_id`` response keys."""
        respx.post(FUND_URL).mock(
            return_value=httpx.Response(
                200,
                json={"transfer_id": "txn_fallback", "status": "pending"},
            )
        )

        adapter = _make_adapter()
        result = await adapter.fund(_funding_request(amount=Decimal("100")))
        assert result.transfer_id == "txn_fallback"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_sends_correct_payload(self):
        route = respx.post(FUND_URL).mock(
            return_value=httpx.Response(
                201,
                json={"id": "txn_pay_001", "status": "processing"},
            )
        )

        adapter = _make_adapter()
        req = _funding_request(
            amount=Decimal("750.00"),
            currency="USD",
            description="Test pre-fund",
            connected_account_id="acct_stripe_001",
        )
        await adapter.fund(req)

        sent = route.calls[0].request
        import json

        body = json.loads(sent.content)
        assert body["amount"] == "750.00"
        assert body["currency"] == "USD"
        assert body["connected_account_id"] == "acct_stripe_001"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_sends_auth_header(self):
        route = respx.post(FUND_URL).mock(
            return_value=httpx.Response(200, json={"id": "txn_hdr_test", "status": "ok"})
        )

        adapter = _make_adapter(api_key="my_bridge_key", api_secret="my_secret", program_id="prog_1")
        await adapter.fund(_funding_request())

        sent = route.calls[0].request
        assert sent.headers["authorization"] == "Bearer my_bridge_key"
        assert sent.headers["x-api-secret"] == "my_secret"
        assert sent.headers["x-program-id"] == "prog_1"

    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_raises_on_4xx(self):
        respx.post(FUND_URL).mock(
            return_value=httpx.Response(400, json={"error": "bad_request"})
        )

        adapter = _make_adapter()
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fund(_funding_request())

    @pytest.mark.asyncio
    @respx.mock
    async def test_fund_raises_on_5xx(self):
        respx.post(FUND_URL).mock(
            return_value=httpx.Response(503, json={"error": "service_unavailable"})
        )

        adapter = _make_adapter()
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.fund(_funding_request())


class TestBridgeCardFundingAdapterQuote:
    @pytest.mark.asyncio
    async def test_quote_returns_synthetic_dict(self):
        adapter = _make_adapter()
        req = _funding_request(amount=Decimal("1000.00"))
        quote = await adapter.quote(req)

        assert quote["provider"] == "bridge_cards"
        assert quote["rail"] == "fiat"
        assert quote["input_amount"] == "1000.00"
        assert quote["input_currency"] == "USD"

    @pytest.mark.asyncio
    async def test_quote_fee_is_0_5_percent(self):
        adapter = _make_adapter()
        req = _funding_request(amount=Decimal("1000.00"))
        quote = await adapter.quote(req)

        # 0.5 % fee on $1000 = $5.00
        assert quote["fee_amount"] == "5.00"
        assert quote["net_amount"] == "995.00"

    @pytest.mark.asyncio
    async def test_quote_small_amount(self):
        adapter = _make_adapter()
        req = _funding_request(amount=Decimal("20.00"))
        quote = await adapter.quote(req)

        # $20 * 0.005 = $0.10 fee
        assert quote["fee_amount"] == "0.10"
        assert quote["net_amount"] == "19.90"

    @pytest.mark.asyncio
    async def test_quote_currency_passthrough(self):
        adapter = _make_adapter()
        req = _funding_request(amount=Decimal("500"), currency="EUR")
        quote = await adapter.quote(req)

        assert quote["input_currency"] == "EUR"
        assert quote["output_currency"] == "EUR"


class TestBridgeCardFundingAdapterStatus:
    @pytest.mark.asyncio
    @respx.mock
    async def test_status_returns_normalised_dict(self):
        respx.get(STATUS_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "id": "txn_abc123",
                    "status": "completed",
                    "amount": "500.00",
                    "currency": "USD",
                },
            )
        )

        adapter = _make_adapter()
        result = await adapter.status("txn_abc123")

        assert result["transfer_id"] == "txn_abc123"
        assert result["status"] == "completed"
        assert result["amount"] == "500.00"
        assert result["currency"] == "USD"

    @pytest.mark.asyncio
    @respx.mock
    async def test_status_includes_raw_response(self):
        raw = {"id": "txn_abc123", "status": "processing", "extra_field": "value"}
        respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json=raw))

        adapter = _make_adapter()
        result = await adapter.status("txn_abc123")

        assert result["raw"] == raw

    @pytest.mark.asyncio
    @respx.mock
    async def test_status_raises_on_404(self):
        respx.get(STATUS_URL).mock(return_value=httpx.Response(404, json={"error": "not_found"}))

        adapter = _make_adapter()
        with pytest.raises(httpx.HTTPStatusError):
            await adapter.status("txn_abc123")

    @pytest.mark.asyncio
    @respx.mock
    async def test_status_unknown_when_body_missing_status(self):
        respx.get(STATUS_URL).mock(return_value=httpx.Response(200, json={"id": "txn_abc123"}))

        adapter = _make_adapter()
        result = await adapter.status("txn_abc123")

        assert result["status"] == "unknown"

"""Tests for Circle Cross-Currency API integration and Coinbase Offramp completion."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_chain.circle_cross_currency import (
    CircleCrossCurrencyClient,
    CircleCrossCurrencyError,
    CrossCurrencyQuote,
    CrossCurrencyTrade,
    CrossCurrencyService,
    QuoteType,
    TradeStatus,
    SettlementBatch,
    SettlementDetail,
    SettlementStatus,
    FiatAccount,
)


# ── CrossCurrencyQuote ───────────────────────────────────────────────


class TestCrossCurrencyQuote:
    def test_crypto_to_crypto(self):
        quote = CrossCurrencyQuote(
            quote_id="q1",
            from_currency="USDC",
            from_amount=Decimal("100"),
            to_currency="EURC",
            to_amount=Decimal("91.5"),
            rate=Decimal("0.915"),
        )
        assert quote.is_crypto_to_crypto is True

    def test_fiat_to_crypto(self):
        quote = CrossCurrencyQuote(
            quote_id="q2",
            from_currency="MXN",
            from_amount=Decimal("2000"),
            to_currency="USDC",
            to_amount=Decimal("100"),
            rate=Decimal("0.05"),
        )
        assert quote.is_crypto_to_crypto is False


# ── CircleCrossCurrencyClient ────────────────────────────────────────


class TestCircleCrossCurrencyClient:
    @pytest.fixture
    def client(self):
        return CircleCrossCurrencyClient(api_key="test-key", sandbox=True)

    @pytest.mark.asyncio
    async def test_get_quote_usdc_to_eurc(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "id": "quote_001",
                "rate": 0.915,
                "from": {"currency": "USDC", "amount": 100.0},
                "to": {"currency": "EURC", "amount": 91.5},
                "expiry": "2026-03-02T12:00:03Z",
                "type": "tradable",
            }
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            quote = await client.get_quote(
                from_currency="USDC",
                from_amount=Decimal("100"),
                to_currency="EURC",
            )
            assert quote.quote_id == "quote_001"
            assert quote.from_currency == "USDC"
            assert quote.to_currency == "EURC"
            assert quote.to_amount == Decimal("91.5")
            assert quote.rate == Decimal("0.915")

    @pytest.mark.asyncio
    async def test_get_quote_eurc_to_usdc(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "id": "quote_002",
                "rate": 1.1,
                "from": {"currency": "EURC", "amount": 100.0},
                "to": {"currency": "USDC", "amount": 110.0},
                "expiry": "2026-03-02T12:00:03Z",
                "type": "tradable",
            }
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            quote = await client.get_quote(
                from_currency="EURC",
                from_amount=Decimal("100"),
                to_currency="USDC",
            )
            assert quote.to_amount == Decimal("110")
            assert quote.rate == Decimal("1.1")

    @pytest.mark.asyncio
    async def test_get_quote_to_side_amount(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "id": "quote_003",
                "rate": 0.915,
                "from": {"currency": "USDC", "amount": 109.29},
                "to": {"currency": "EURC", "amount": 100.0},
                "expiry": "2026-03-02T12:00:03Z",
                "type": "tradable",
            }
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            quote = await client.get_quote(
                from_currency="USDC",
                to_currency="EURC",
                to_amount=Decimal("100"),
            )
            assert quote.to_amount == Decimal("100")

    @pytest.mark.asyncio
    async def test_get_quote_no_amount_raises(self, client):
        with pytest.raises(CircleCrossCurrencyError, match="Must specify"):
            await client.get_quote("USDC", to_currency="EURC")

    @pytest.mark.asyncio
    async def test_get_quote_both_amounts_raises(self, client):
        with pytest.raises(CircleCrossCurrencyError, match="Cannot specify both"):
            await client.get_quote(
                "USDC",
                from_amount=Decimal("100"),
                to_currency="EURC",
                to_amount=Decimal("90"),
            )

    @pytest.mark.asyncio
    async def test_execute_trade(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {
                "id": "trade_001",
                "from": {"currency": "USDC", "amount": 100.0},
                "to": {"currency": "EURC", "amount": 91.5},
                "status": "pending",
                "createDate": "2026-03-02T12:00:01Z",
                "updateDate": "2026-03-02T12:00:01Z",
                "quoteId": "quote_001",
            }
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "post", new_callable=AsyncMock, return_value=mock_resp):
            trade = await client.execute_trade("quote_001")
            assert trade.trade_id == "trade_001"
            assert trade.status == TradeStatus.PENDING
            assert trade.from_amount == Decimal("100")
            assert trade.to_amount == Decimal("91.5")

    @pytest.mark.asyncio
    async def test_get_settlements(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "batch_001",
                    "entityId": "entity_001",
                    "status": "settled",
                    "createDate": "2026-03-01T10:00:00Z",
                    "updateDate": "2026-03-01T10:05:00Z",
                    "details": [
                        {
                            "id": "detail_001",
                            "type": "receivable",
                            "status": "completed",
                            "amount": {"currency": "EURC", "amount": "91.5"},
                        },
                        {
                            "id": "detail_002",
                            "type": "payable",
                            "status": "completed",
                            "amount": {"currency": "USDC", "amount": "100"},
                        },
                    ],
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            batches = await client.get_settlements()
            assert len(batches) == 1
            assert batches[0].status == SettlementStatus.SETTLED
            assert len(batches[0].details) == 2
            assert batches[0].details[0].currency == "EURC"

    @pytest.mark.asyncio
    async def test_list_fiat_accounts(self, client):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {
                    "id": "acct_001",
                    "type": "wire",
                    "status": "complete",
                    "description": "Bank of Test ****1234",
                    "bankAddress": {"bankName": "Bank of Test"},
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        with patch.object(client._client, "get", new_callable=AsyncMock, return_value=mock_resp):
            accounts = await client.list_fiat_accounts()
            assert len(accounts) == 1
            assert accounts[0].account_id == "acct_001"
            assert accounts[0].bank_name == "Bank of Test"


# ── CrossCurrencyService ─────────────────────────────────────────────


class TestCrossCurrencyService:
    @pytest.fixture
    def mock_client(self):
        return MagicMock(spec=CircleCrossCurrencyClient)

    @pytest.mark.asyncio
    async def test_swap_usdc_to_eurc(self, mock_client):
        mock_client.get_quote = AsyncMock(return_value=CrossCurrencyQuote(
            quote_id="q_swap",
            from_currency="USDC",
            from_amount=Decimal("100"),
            to_currency="EURC",
            to_amount=Decimal("91.5"),
            rate=Decimal("0.915"),
        ))
        mock_client.execute_trade = AsyncMock(return_value=CrossCurrencyTrade(
            trade_id="t_swap",
            quote_id="q_swap",
            from_currency="USDC",
            from_amount=Decimal("100"),
            to_currency="EURC",
            to_amount=Decimal("91.5"),
            status=TradeStatus.SETTLED,
        ))

        service = CrossCurrencyService(mock_client)
        trade = await service.swap_usdc_to_eurc(Decimal("100"))

        assert trade.status == TradeStatus.SETTLED
        assert trade.to_currency == "EURC"
        mock_client.get_quote.assert_called_once()
        mock_client.execute_trade.assert_called_once_with("q_swap")

    @pytest.mark.asyncio
    async def test_swap_eurc_to_usdc(self, mock_client):
        mock_client.get_quote = AsyncMock(return_value=CrossCurrencyQuote(
            quote_id="q_reverse",
            from_currency="EURC",
            from_amount=Decimal("100"),
            to_currency="USDC",
            to_amount=Decimal("110"),
            rate=Decimal("1.1"),
        ))
        mock_client.execute_trade = AsyncMock(return_value=CrossCurrencyTrade(
            trade_id="t_reverse",
            quote_id="q_reverse",
            from_currency="EURC",
            from_amount=Decimal("100"),
            to_currency="USDC",
            to_amount=Decimal("110"),
            status=TradeStatus.SETTLED,
        ))

        service = CrossCurrencyService(mock_client)
        trade = await service.swap_eurc_to_usdc(Decimal("100"))

        assert trade.to_amount == Decimal("110")
        assert trade.to_currency == "USDC"

    @pytest.mark.asyncio
    async def test_get_indicative_rate(self, mock_client):
        mock_client.get_quote = AsyncMock(return_value=CrossCurrencyQuote(
            quote_id="q_ind",
            from_currency="MXN",
            from_amount=Decimal("2000"),
            to_currency="USDC",
            to_amount=Decimal("100"),
            rate=Decimal("0.05"),
            quote_type=QuoteType.INDICATIVE,
        ))

        service = CrossCurrencyService(mock_client)
        quote = await service.get_indicative_rate("MXN", "USDC", Decimal("2000"))

        assert quote.rate == Decimal("0.05")
        assert not quote.is_crypto_to_crypto


# ── API Models ───────────────────────────────────────────────────────


class TestSwapAPIModels:
    def test_cross_currency_quote_request(self):
        from sardis_api.routers.swap import CrossCurrencyQuoteRequest

        req = CrossCurrencyQuoteRequest(
            from_currency="USDC",
            to_currency="EURC",
            amount=Decimal("100"),
        )
        assert req.side == "from"

    def test_cross_currency_trade_request(self):
        from sardis_api.routers.swap import CrossCurrencyTradeRequest

        req = CrossCurrencyTradeRequest(quote_id="q_test")
        assert req.quote_id == "q_test"

"""Tests for Stripe Stablecoin-Backed Card Issuing integration."""
from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_cards.providers.stripe_stablecoin import (
    USDC_BASE_CONTRACT,
    DepositStatus,
    FundingTransferStatus,
    StablecoinAccountStatus,
    StablecoinCardService,
    StablecoinDeposit,
    StablecoinFinancialAccount,
    StripeStablecoinClient,
    StripeStablecoinError,
)

# ── Data Models ───────────────────────────────────────────────────────


class TestStablecoinFinancialAccount:
    def test_defaults(self):
        fa = StablecoinFinancialAccount(
            account_id="fa_test123",
            connected_account_id="acct_test456",
        )
        assert fa.status == StablecoinAccountStatus.OPEN
        assert fa.usdc_balance == Decimal("0")
        assert fa.usd_balance == Decimal("0")
        assert fa.deposit_chain == "base"
        assert "usdc" in fa.supported_currencies
        assert "usd" in fa.supported_currencies

    def test_with_balances(self):
        fa = StablecoinFinancialAccount(
            account_id="fa_test123",
            connected_account_id="acct_test456",
            usdc_balance=Decimal("1000.50"),
            usd_balance=Decimal("250.00"),
            deposit_address="0xABCDEF1234567890abcdef1234567890abcdef12",
        )
        assert fa.usdc_balance == Decimal("1000.50")
        assert fa.usd_balance == Decimal("250.00")
        assert fa.deposit_address.startswith("0x")


class TestStablecoinDeposit:
    def test_pending_deposit(self):
        deposit = StablecoinDeposit(
            deposit_id="rc_test001",
            financial_account_id="fa_test123",
            amount=Decimal("500"),
            currency="usdc",
            chain="base",
        )
        assert deposit.status == DepositStatus.PENDING
        assert deposit.tx_hash is None

    def test_confirmed_deposit(self):
        deposit = StablecoinDeposit(
            deposit_id="rc_test002",
            financial_account_id="fa_test123",
            amount=Decimal("1000"),
            currency="usdc",
            chain="base",
            tx_hash="0xabc123def456",
            status=DepositStatus.CONFIRMED,
        )
        assert deposit.status == DepositStatus.CONFIRMED
        assert deposit.tx_hash == "0xabc123def456"


class TestEnums:
    def test_account_status_values(self):
        assert StablecoinAccountStatus.OPEN == "open"
        assert StablecoinAccountStatus.CLOSED == "closed"

    def test_deposit_status_values(self):
        assert DepositStatus.PENDING == "pending"
        assert DepositStatus.CONFIRMED == "confirmed"
        assert DepositStatus.FAILED == "failed"

    def test_funding_transfer_status(self):
        assert FundingTransferStatus.POSTED == "posted"


# ── StripeStablecoinClient ────────────────────────────────────────────


class TestStripeStablecoinClient:
    @pytest.fixture
    def mock_stripe(self):
        with patch.dict("sys.modules", {"stripe": MagicMock()}) as modules:
            stripe_mock = modules["stripe"]
            stripe_mock.api_key = None
            yield stripe_mock

    @pytest.fixture
    def client(self, mock_stripe):
        c = StripeStablecoinClient(api_key="test_key_abc123")
        c._stripe = mock_stripe
        return c

    @pytest.mark.asyncio
    async def test_create_connected_account(self, client, mock_stripe):
        mock_stripe.Account.create.return_value = MagicMock(id="acct_test789")

        result = await client.create_connected_account(
            "Agent Corp", email="agent@test.com"
        )

        assert result["account_id"] == "acct_test789"
        assert result["business_name"] == "Agent Corp"
        assert "card_issuing" in result["capabilities_requested"]
        assert "treasury" in result["capabilities_requested"]

    @pytest.mark.asyncio
    async def test_create_connected_account_error(self, client, mock_stripe):
        mock_stripe.Account.create.side_effect = Exception("API error")

        with pytest.raises(StripeStablecoinError, match="Failed to create connected account"):
            await client.create_connected_account("Agent Corp")

    @pytest.mark.asyncio
    async def test_create_financial_account(self, client, mock_stripe):
        fa_mock = MagicMock()
        fa_mock.id = "fa_stablecoin_001"
        mock_stripe.treasury.FinancialAccount.create.return_value = fa_mock

        # Mock deposit address retrieval
        fa_detail = MagicMock()
        fa_detail.to_dict.return_value = {
            "financial_addresses": {
                "data": [
                    {
                        "type": "crypto",
                        "network": "base",
                        "address": "0x1234567890abcdef1234567890abcdef12345678",
                    }
                ]
            }
        }
        mock_stripe.treasury.FinancialAccount.retrieve.return_value = fa_detail

        result = await client.create_financial_account("acct_test789")

        assert result.account_id == "fa_stablecoin_001"
        assert result.connected_account_id == "acct_test789"
        assert result.deposit_address == "0x1234567890abcdef1234567890abcdef12345678"
        assert result.deposit_chain == "base"
        assert result.status == StablecoinAccountStatus.OPEN

    @pytest.mark.asyncio
    async def test_get_financial_account_balances(self, client, mock_stripe):
        fa_mock = MagicMock()
        fa_mock.to_dict.return_value = {
            "id": "fa_test001",
            "status": "open",
            "balance": {
                "cash": {
                    "usdc": 100050,  # $1000.50 in cents
                    "usd": 25000,   # $250.00 in cents
                },
            },
            "financial_addresses": {
                "data": [
                    {"type": "crypto", "network": "base", "address": "0xDEPOSIT"}
                ]
            },
        }
        mock_stripe.treasury.FinancialAccount.retrieve.return_value = fa_mock

        result = await client.get_financial_account("fa_test001", "acct_test789")

        assert result.usdc_balance == Decimal("1000.5")
        assert result.usd_balance == Decimal("250")
        assert result.deposit_address == "0xDEPOSIT"

    @pytest.mark.asyncio
    async def test_get_stablecoin_balance(self, client, mock_stripe):
        fa_mock = MagicMock()
        fa_mock.to_dict.return_value = {
            "id": "fa_test001",
            "status": "open",
            "balance": {"cash": {"usdc": 50000, "usd": 10000}},
            "financial_addresses": {"data": []},
        }
        mock_stripe.treasury.FinancialAccount.retrieve.return_value = fa_mock

        balance = await client.get_stablecoin_balance("fa_test001", "acct_test789")

        assert balance["usdc"] == Decimal("500")
        assert balance["usd"] == Decimal("100")
        assert balance["total_usd_equivalent"] == Decimal("600")

    @pytest.mark.asyncio
    async def test_create_stablecoin_card(self, client, mock_stripe):
        card_mock = MagicMock()
        card_mock.id = "ic_stablecoin_001"
        card_mock.last4 = "4242"
        card_mock.exp_month = 12
        card_mock.exp_year = 2028
        card_mock.status = "active"
        mock_stripe.issuing.Card.create.return_value = card_mock

        result = await client.create_stablecoin_card(
            "acct_test789",
            "ich_test001",
            spending_limits=[{"amount": 50000, "interval": "per_authorization"}],
        )

        assert result["card_id"] == "ic_stablecoin_001"
        assert result["last4"] == "4242"
        assert result["funding_source"] == "stablecoin"
        assert result["connected_account_id"] == "acct_test789"

    @pytest.mark.asyncio
    async def test_create_cardholder(self, client, mock_stripe):
        ch_mock = MagicMock()
        ch_mock.id = "ich_stablecoin_001"
        mock_stripe.issuing.Cardholder.create.return_value = ch_mock

        result = await client.create_cardholder(
            "acct_test789",
            name="Jane Doe",
            email="jane@test.com",
        )

        assert result == "ich_stablecoin_001"

    @pytest.mark.asyncio
    async def test_list_received_credits(self, client, mock_stripe):
        credit_mock = MagicMock()
        credit_mock.to_dict.return_value = {
            "id": "rc_001",
            "amount": 100000,  # $1000
            "currency": "usdc",
            "status": "succeeded",
            "created": 1709395200,
            "network_details": {"tx_hash": "0xabc123"},
        }
        list_mock = MagicMock()
        list_mock.data = [credit_mock]
        mock_stripe.treasury.ReceivedCredit.list.return_value = list_mock

        deposits = await client.list_received_credits("fa_test001", "acct_test789")

        assert len(deposits) == 1
        assert deposits[0].amount == Decimal("1000")
        assert deposits[0].currency == "usdc"
        assert deposits[0].tx_hash == "0xabc123"
        assert deposits[0].status == DepositStatus.CONFIRMED

    @pytest.mark.asyncio
    async def test_is_test_mode(self, mock_stripe):
        prefix_test = "sk_" + "test_placeholder"
        test_client = StripeStablecoinClient(api_key=prefix_test)
        assert test_client._is_test_mode is True

        prefix_live = "sk_" + "live_placeholder"
        live_client = StripeStablecoinClient(api_key=prefix_live)
        assert live_client._is_test_mode is False


# ── StablecoinCardService ─────────────────────────────────────────────


class TestStablecoinCardService:
    @pytest.fixture
    def mock_client(self):
        client = MagicMock(spec=StripeStablecoinClient)
        client.close = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_onboard_agent(self, mock_client):
        mock_client.create_connected_account = AsyncMock(return_value={
            "account_id": "acct_agent001",
            "business_name": "Agent X",
            "country": "US",
            "capabilities_requested": ["card_issuing", "treasury"],
        })
        mock_client.create_financial_account = AsyncMock(
            return_value=StablecoinFinancialAccount(
                account_id="fa_agent001",
                connected_account_id="acct_agent001",
                deposit_address="0xDEPOSIT_ADDR",
                deposit_chain="base",
            )
        )

        service = StablecoinCardService(mock_client)
        fa = await service.onboard_agent(
            agent_name="Agent X",
            email="agent@sardis.sh",
            wallet_id="w_test001",
        )

        assert fa.account_id == "fa_agent001"
        assert fa.deposit_address == "0xDEPOSIT_ADDR"
        assert fa.deposit_chain == "base"
        mock_client.create_connected_account.assert_called_once()
        mock_client.create_financial_account.assert_called_once()

    @pytest.mark.asyncio
    async def test_issue_card(self, mock_client):
        mock_client.create_cardholder = AsyncMock(return_value="ich_agent001")
        mock_client.create_stablecoin_card = AsyncMock(return_value={
            "card_id": "ic_agent001",
            "last4": "1234",
            "exp_month": 6,
            "exp_year": 2029,
            "status": "active",
            "type": "virtual",
            "funding_source": "stablecoin",
            "connected_account_id": "acct_agent001",
        })

        service = StablecoinCardService(mock_client)
        card = await service.issue_card(
            connected_account_id="acct_agent001",
            cardholder_name="Agent X",
            cardholder_email="agent@sardis.sh",
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
            wallet_id="w_test001",
        )

        assert card["card_id"] == "ic_agent001"
        assert card["cardholder_id"] == "ich_agent001"
        assert card["limits"]["per_tx"] == "500"
        assert card["limits"]["daily"] == "2000"

    @pytest.mark.asyncio
    async def test_get_deposit_info(self, mock_client):
        mock_client.get_financial_account = AsyncMock(
            return_value=StablecoinFinancialAccount(
                account_id="fa_agent001",
                connected_account_id="acct_agent001",
                deposit_address="0xDEPOSIT_ADDR",
                usdc_balance=Decimal("500"),
                usd_balance=Decimal("100"),
            )
        )

        service = StablecoinCardService(mock_client)
        info = await service.get_deposit_info("fa_agent001", "acct_agent001")

        assert info["deposit_address"] == "0xDEPOSIT_ADDR"
        assert info["chain"] == "base"
        assert info["token"] == "USDC"
        assert info["token_contract"] == USDC_BASE_CONTRACT
        assert info["usdc_balance"] == "500"
        assert info["usd_balance"] == "100"


# ── API Models ────────────────────────────────────────────────────────


sardis_api_available = True
try:
    from sardis_api.routers.stablecoin_cards import (
        BalanceResponse,
        IssueCardRequest,
        OnboardAgentRequest,
    )
except ImportError:
    sardis_api_available = False


@pytest.mark.skipif(not sardis_api_available, reason="sardis_api deps not available")
class TestStablecoinCardAPIModels:
    def test_onboard_request(self):
        req = OnboardAgentRequest(
            agent_name="Agent Corp",
            email="agent@test.com",
            wallet_id="w_123",
        )
        assert req.agent_name == "Agent Corp"
        assert req.wallet_id == "w_123"

    def test_issue_card_request_defaults(self):
        req = IssueCardRequest(
            connected_account_id="acct_test",
            cardholder_name="Test Agent",
            cardholder_email="test@sardis.sh",
        )
        assert req.limit_per_tx == Decimal("500")
        assert req.limit_daily == Decimal("2000")
        assert req.limit_monthly == Decimal("10000")

    def test_balance_response(self):
        resp = BalanceResponse(
            usdc="1000.50",
            usd="250.00",
            total_usd_equivalent="1250.50",
        )
        assert resp.usdc == "1000.50"
        assert resp.total_usd_equivalent == "1250.50"

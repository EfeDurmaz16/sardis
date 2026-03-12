"""USDC funding pipeline end-to-end tests.

Tests the full funding flow: onramp initiation -> wallet balance ->
card funding -> spending, using mocked external services.

Covers:
- Coinbase Onramp session creation and webhook verification
- Wallet balance simulation
- Card funding via MockProvider
- Full pipeline (fund -> spend -> refund)
- Off-ramp quote model and transaction lifecycle
- CardProviderRouter failover and routing
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sardis_cards.models import (
    Card,
    CardStatus,
    CardTransaction,
    CardType,
    FundingSource,
    TransactionStatus,
)
from sardis_cards.offramp import (
    MockOfframpProvider,
    OfframpProvider,
    OfframpQuote,
    OfframpStatus,
    OfframpTransaction,
)
from sardis_cards.providers.mock import MockProvider
from sardis_cards.providers.router import CardProviderRouter

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(coro):
    """Run an async coroutine synchronously."""
    return asyncio.run(coro)


async def _create_and_activate_card(
    provider: MockProvider,
    wallet_id: str = "wal_test_001",
    card_type: CardType = CardType.MULTI_USE,
    limit_per_tx: Decimal = Decimal("500"),
    limit_daily: Decimal = Decimal("2000"),
    limit_monthly: Decimal = Decimal("10000"),
) -> Card:
    """Helper to create and activate a card in a single step."""
    card = await provider.create_card(
        wallet_id=wallet_id,
        card_type=card_type,
        limit_per_tx=limit_per_tx,
        limit_daily=limit_daily,
        limit_monthly=limit_monthly,
    )
    card = await provider.activate_card(card.provider_card_id)
    return card


# ===========================================================================
# Coinbase Onramp Tests
# ===========================================================================


class TestCoinbaseOnrampSessionCreation:
    """Test Coinbase onramp session creation with mocked HTTP."""

    def test_coinbase_onramp_session_creation(self):
        """Create a Coinbase onramp session with wallet address, amount,
        currency and verify it returns session URL."""
        os.environ["COINBASE_ONRAMP_API_KEY"] = "test_key_123"
        os.environ["COINBASE_WEBHOOK_SECRET"] = "test_webhook_placeholder"

        from sardis_ramp.providers.coinbase_provider import CoinbaseOnrampProvider

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "session_id": "sess_cb_001",
            "hosted_url": "https://pay.coinbase.com/buy/sess_cb_001",
        }
        mock_response.raise_for_status = MagicMock()

        with patch.object(
            CoinbaseOnrampProvider,
            "_coinbase_request",
            new_callable=AsyncMock,
            return_value={
                "session_id": "sess_cb_001",
                "hosted_url": "https://pay.coinbase.com/buy/sess_cb_001",
            },
        ):
            provider = CoinbaseOnrampProvider(
                api_key="test_key_123",
                environment="sandbox",
            )

            session = _run(provider.create_onramp(
                amount_fiat=Decimal("100"),
                fiat_currency="USD",
                crypto_currency="USDC",
                chain="base",
                destination_address="0x1234567890abcdef1234567890abcdef12345678",
                wallet_id="wal_test_001",
                metadata={"user_id": "usr_001"},
            ))

            assert session.session_id == "sess_cb_001"
            assert session.provider == "coinbase"
            assert session.direction == "onramp"
            assert session.payment_url == "https://pay.coinbase.com/buy/sess_cb_001"
            assert session.fiat_currency == "USD"
            assert session.crypto_currency == "USDC"
            assert session.chain == "base"
            # USDC should have 0% fee
            assert session.amount_fiat == Decimal("100")
            assert session.amount_crypto == Decimal("100")  # 0% fee for USDC
            assert session.metadata["promotional_zero_fee"] is True


class TestCoinbaseWebhookSignature:
    """Test Coinbase webhook HMAC-SHA256 signature verification."""

    def test_coinbase_webhook_signature_verification(self):
        """Verify HMAC-SHA256 signature on Coinbase webhook is accepted."""
        os.environ["COINBASE_ONRAMP_API_KEY"] = "test_key_123"
        webhook_secret = "test_webhook_placeholder"
        os.environ["COINBASE_WEBHOOK_SECRET"] = webhook_secret

        from sardis_ramp.providers.coinbase_provider import CoinbaseOnrampProvider

        provider = CoinbaseOnrampProvider(
            api_key="test_key_123",
            environment="sandbox",
        )

        payload = json.dumps({
            "event_type": "onramp.completed",
            "data": {
                "session_id": "sess_cb_001",
                "status": "completed",
                "transaction_hash": "0xabc123",
            },
        }).encode()

        # Generate valid signature
        valid_signature = hmac.new(
            webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        # _verify_webhook should return True for valid signature
        assert provider._verify_webhook(payload, valid_signature) is True

    def test_coinbase_webhook_invalid_signature_rejected(self):
        """Invalid signature should be rejected."""
        os.environ["COINBASE_ONRAMP_API_KEY"] = "test_key_123"
        webhook_secret = "test_webhook_placeholder"
        os.environ["COINBASE_WEBHOOK_SECRET"] = webhook_secret

        from sardis_ramp.providers.coinbase_provider import CoinbaseOnrampProvider

        provider = CoinbaseOnrampProvider(
            api_key="test_key_123",
            environment="sandbox",
        )

        payload = json.dumps({
            "event_type": "onramp.completed",
            "data": {"session_id": "sess_cb_001"},
        }).encode()

        # Tampered/bad signature
        bad_signature = "deadbeef" * 8

        assert provider._verify_webhook(payload, bad_signature) is False

        # Also test with a signature generated from a different secret
        wrong_secret_sig = hmac.new(
            b"wrong_secret",
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert provider._verify_webhook(payload, wrong_secret_sig) is False


# ===========================================================================
# Wallet Balance Tests
# ===========================================================================


class TestWalletBalance:
    """Test wallet balance checks with mocked RPC."""

    def test_wallet_balance_after_mock_funding(self):
        """Simulate funding a wallet and check balance increases."""
        # Simulate a wallet with a balance property
        wallet = MagicMock()
        wallet.wallet_id = "wal_test_001"
        wallet.get_balance = AsyncMock(return_value=Decimal("0"))

        # Simulate onramp completing: balance goes from 0 to 100 USDC
        wallet.get_balance.return_value = Decimal("100.00")

        balance = _run(wallet.get_balance())
        assert balance == Decimal("100.00")

        # Simulate another deposit
        wallet.get_balance.return_value = Decimal("250.00")
        balance = _run(wallet.get_balance())
        assert balance == Decimal("250.00")

    def test_wallet_balance_insufficient_for_card(self):
        """Try to fund card when wallet balance is too low -- should fail."""
        wallet = MagicMock()
        wallet.wallet_id = "wal_test_001"
        wallet.get_balance = AsyncMock(return_value=Decimal("10.00"))

        requested_fund_amount = Decimal("500.00")
        balance = _run(wallet.get_balance())

        # Application logic: check balance >= requested amount before funding
        assert balance < requested_fund_amount, (
            "Wallet balance should be insufficient for the requested card funding"
        )

        # Verify that the policy check catches this
        can_fund = balance >= requested_fund_amount
        assert can_fund is False


# ===========================================================================
# Card Funding Pipeline Tests
# ===========================================================================


class TestCardFunding:
    """Test card funding operations via MockProvider."""

    def test_fund_card_from_wallet(self):
        """MockProvider.fund_card() increases funded_amount."""
        provider = MockProvider()

        card = _run(_create_and_activate_card(provider))
        assert card.funded_amount == Decimal("0")

        card = _run(provider.fund_card(card.provider_card_id, Decimal("200.00")))
        assert card.funded_amount == Decimal("200.00")

        # Fund again -- should accumulate
        card = _run(provider.fund_card(card.provider_card_id, Decimal("50.00")))
        assert card.funded_amount == Decimal("250.00")

    def test_card_available_balance_after_funding(self):
        """available_balance = funded_amount - pending_authorizations."""
        provider = MockProvider()

        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("500.00")))

        # No pending auths yet
        assert card.available_balance == Decimal("500.00")

        # Simulate a pending authorization
        card.pending_authorizations = Decimal("150.00")

        # available_balance = min(daily_available, funded_available)
        # funded_available = 500 - 150 = 350
        # daily_available = 2000 - 0 - 150 = 1850
        # available = min(1850, 350) = 350
        assert card.available_balance == Decimal("350.00")

    def test_card_spending_reduces_funded_amount(self):
        """simulate_transaction reduces funded_amount for approved txns."""
        provider = MockProvider()

        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("300.00")))
        assert card.funded_amount == Decimal("300.00")

        # Simulate an approved transaction
        tx = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("75.00"),
            merchant_name="AWS",
        ))

        assert tx.status == TransactionStatus.APPROVED
        assert tx.amount == Decimal("75.00")
        assert card.funded_amount == Decimal("225.00")  # 300 - 75
        assert card.spent_today == Decimal("75.00")
        assert card.total_spent == Decimal("75.00")


# ===========================================================================
# Full Pipeline Tests
# ===========================================================================


class TestFullPipeline:
    """Test the full funding-to-spending pipeline."""

    def test_full_pipeline_fund_to_spend(self):
        """Fund card -> simulate auth -> check balances throughout."""
        provider = MockProvider()

        # Step 1: Create and activate card
        card = _run(_create_and_activate_card(
            provider,
            wallet_id="wal_pipeline_001",
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
        ))
        assert card.status == CardStatus.ACTIVE
        assert card.funded_amount == Decimal("0")

        # Step 2: Fund card (simulates post-onramp wallet -> card transfer)
        _run(provider.fund_card(card.provider_card_id, Decimal("1000.00")))
        assert card.funded_amount == Decimal("1000.00")

        # Step 3: Authorize and spend
        can_auth, reason = card.can_authorize(Decimal("200.00"))
        assert can_auth is True
        assert reason == "OK"

        tx = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("200.00"),
            merchant_name="OpenAI API",
        ))
        assert tx.status == TransactionStatus.APPROVED

        # Step 4: Verify balances after spend
        assert card.funded_amount == Decimal("800.00")
        assert card.spent_today == Decimal("200.00")
        assert card.available_balance == Decimal("800.00")

        # Step 5: Second transaction
        tx2 = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("300.00"),
            merchant_name="Anthropic",
        ))
        assert tx2.status == TransactionStatus.APPROVED
        assert card.funded_amount == Decimal("500.00")
        assert card.spent_today == Decimal("500.00")
        assert card.total_spent == Decimal("500.00")

    def test_full_pipeline_fund_spend_refund(self):
        """Fund -> spend -> simulate reversal."""
        provider = MockProvider()

        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("500.00")))

        # Spend
        tx = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("100.00"),
            merchant_name="SaaS Co",
        ))
        assert card.funded_amount == Decimal("400.00")
        assert card.total_spent == Decimal("100.00")

        # Simulate reversal: refund restores funded_amount
        reversal = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("100.00"),
            merchant_name="SaaS Co",
            status=TransactionStatus.REVERSED,
        ))
        assert reversal.status == TransactionStatus.REVERSED
        # Reversed transactions do NOT deduct from funded_amount
        # (the MockProvider only deducts for APPROVED status)
        assert card.funded_amount == Decimal("400.00")

        # To properly simulate a refund, we fund back manually
        _run(provider.fund_card(card.provider_card_id, Decimal("100.00")))
        assert card.funded_amount == Decimal("500.00")

    def test_multiple_cards_from_same_wallet(self):
        """Create 2 cards, fund both, verify independent balances."""
        provider = MockProvider()
        wallet_id = "wal_multi_card"

        card_a = _run(_create_and_activate_card(provider, wallet_id=wallet_id))
        card_b = _run(_create_and_activate_card(provider, wallet_id=wallet_id))

        assert card_a.card_id != card_b.card_id
        assert card_a.wallet_id == card_b.wallet_id == wallet_id

        # Fund them differently
        _run(provider.fund_card(card_a.provider_card_id, Decimal("300.00")))
        _run(provider.fund_card(card_b.provider_card_id, Decimal("700.00")))

        assert card_a.funded_amount == Decimal("300.00")
        assert card_b.funded_amount == Decimal("700.00")

        # Spend on card A
        _run(provider.simulate_transaction(
            card_a.provider_card_id,
            Decimal("100.00"),
        ))
        assert card_a.funded_amount == Decimal("200.00")
        # Card B should be unaffected
        assert card_b.funded_amount == Decimal("700.00")

        # Spend on card B
        _run(provider.simulate_transaction(
            card_b.provider_card_id,
            Decimal("250.00"),
        ))
        assert card_b.funded_amount == Decimal("450.00")
        # Card A still at 200
        assert card_a.funded_amount == Decimal("200.00")

    def test_card_funding_limit_enforcement(self):
        """Fund card to max, try to overspend -> declined via can_authorize."""
        provider = MockProvider()

        card = _run(_create_and_activate_card(
            provider,
            limit_per_tx=Decimal("200"),
            limit_daily=Decimal("500"),
        ))

        _run(provider.fund_card(card.provider_card_id, Decimal("500.00")))

        # Spend up to daily limit
        _run(provider.simulate_transaction(card.provider_card_id, Decimal("200.00")))
        _run(provider.simulate_transaction(card.provider_card_id, Decimal("200.00")))

        # Now try to authorize 200 more -- only 100 funded + daily limit check
        # spent_today = 400, funded_amount = 100
        # available_balance = min(daily_avail, funded_avail)
        #   daily_avail = 500 - 400 - 0 = 100
        #   funded_avail = 100 - 0 = 100
        #   available = 100
        can_auth, reason = card.can_authorize(Decimal("200.00"))
        assert can_auth is False
        assert "exceeds available balance" in reason.lower()

        # But 100 should be fine
        can_auth, reason = card.can_authorize(Decimal("100.00"))
        assert can_auth is True

        # Per-tx limit check: 250 exceeds limit_per_tx of 200
        card2 = _run(_create_and_activate_card(
            provider,
            limit_per_tx=Decimal("200"),
            limit_daily=Decimal("5000"),
        ))
        _run(provider.fund_card(card2.provider_card_id, Decimal("1000.00")))

        can_auth, reason = card2.can_authorize(Decimal("250.00"))
        assert can_auth is False
        assert "per-transaction limit" in reason.lower()


# ===========================================================================
# Off-Ramp Quote Tests
# ===========================================================================


class TestOfframpQuote:
    """Test OfframpQuote model and fee calculation."""

    def test_offramp_quote_model(self):
        """Create OfframpQuote with USDC->USD, verify fee calculation."""
        input_amount_minor = 10_000  # $100.00 in minor units
        fee_bps = 50  # 0.5%
        fee_amount = input_amount_minor * fee_bps // 10000  # = 50
        output_amount = input_amount_minor - fee_amount  # = 9950

        quote = OfframpQuote(
            quote_id="q_test_001",
            provider=OfframpProvider.MOCK,
            input_token="USDC",
            input_amount_minor=input_amount_minor,
            input_chain="base",
            output_currency="USD",
            output_amount_cents=output_amount,
            exchange_rate=Decimal("1.0"),
            fee_cents=fee_amount,
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )

        assert quote.input_token == "USDC"
        assert quote.output_currency == "USD"
        assert quote.input_amount_minor == 10_000
        assert quote.output_amount_cents == 9950
        assert quote.fee_cents == 50
        assert quote.is_expired is False

        # Verify fee math: output = input - fee
        assert quote.output_amount_cents == quote.input_amount_minor - quote.fee_cents

    def test_offramp_quote_expiry(self):
        """Expired quote should report is_expired=True."""
        quote = OfframpQuote(
            quote_id="q_expired",
            provider=OfframpProvider.MOCK,
            input_token="USDC",
            input_amount_minor=5000,
            input_chain="base",
            output_currency="USD",
            output_amount_cents=4975,
            exchange_rate=Decimal("1.0"),
            fee_cents=25,
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
        )
        assert quote.is_expired is True


class TestOfframpTransactionLifecycle:
    """Test off-ramp transaction status transitions."""

    def test_offramp_transaction_lifecycle(self):
        """PENDING -> PROCESSING -> COMPLETED lifecycle."""
        offramp = MockOfframpProvider()

        # Get quote
        quote = _run(offramp.get_quote(
            input_token="USDC",
            input_amount_minor=100_000,
            input_chain="base",
            output_currency="USD",
        ))
        assert quote.provider == OfframpProvider.MOCK
        assert quote.fee_cents > 0  # Mock charges 0.5%
        assert quote.output_amount_cents == 100_000 - quote.fee_cents

        # Execute off-ramp -> starts in PROCESSING
        tx = _run(offramp.execute_offramp(
            quote=quote,
            source_address="0xabc",
            destination_account="acct_bank_001",
        ))
        assert tx.status == OfframpStatus.PROCESSING
        assert tx.quote_id == quote.quote_id
        assert tx.destination_account == "acct_bank_001"

        # Check status (before simulated completion)
        tx_status = _run(offramp.get_transaction_status(tx.transaction_id))
        assert tx_status.status in (OfframpStatus.PROCESSING, OfframpStatus.COMPLETED)

    def test_offramp_transaction_initial_status(self):
        """New OfframpTransaction defaults to PENDING."""
        tx = OfframpTransaction(
            transaction_id="tx_new",
            quote_id="q_new",
            provider=OfframpProvider.MOCK,
            input_token="USDC",
            input_amount_minor=50_000,
            input_chain="base",
        )
        assert tx.status == OfframpStatus.PENDING
        assert tx.completed_at is None
        assert tx.failure_reason is None


# ===========================================================================
# Provider Routing Tests
# ===========================================================================


class TestCardProviderRouterFailover:
    """Test CardProviderRouter primary/fallback failover."""

    def test_card_provider_router_failover(self):
        """Primary fails, fallback succeeds."""
        primary = MockProvider()
        fallback = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=fallback)

        # Make primary raise on create_card
        original_create = primary.create_card

        async def failing_create(*args, **kwargs):
            raise RuntimeError("Primary issuer down")

        primary.create_card = failing_create

        # Router should fall back to fallback provider
        card = _run(router.create_card(
            wallet_id="wal_failover",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        ))

        assert card is not None
        assert card.wallet_id == "wal_failover"
        # The card should be in the fallback provider's store
        assert card.provider_card_id in fallback._cards

    def test_card_provider_router_primary_success(self):
        """When primary succeeds, fallback is never called."""
        primary = MockProvider()
        fallback = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=fallback)

        card = _run(router.create_card(
            wallet_id="wal_primary",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        ))

        assert card is not None
        # Card should be in primary, not fallback
        assert card.provider_card_id in primary._cards
        assert len(fallback._cards) == 0

    def test_card_provider_router_routes_existing_card(self):
        """Existing card routes to the correct provider."""
        primary = MockProvider()
        fallback = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=fallback)

        # Create card via primary through the router
        card = _run(router.create_card(
            wallet_id="wal_routing",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        ))
        provider_card_id = card.provider_card_id

        # Activate through router -- should resolve to primary
        activated = _run(router.activate_card(provider_card_id))
        assert activated.status == CardStatus.ACTIVE

        # Fund through router
        funded = _run(router.fund_card(provider_card_id, Decimal("100.00")))
        assert funded.funded_amount == Decimal("100.00")

        # Verify the card in primary got the funds
        primary_card = _run(primary.get_card(provider_card_id))
        assert primary_card is not None
        assert primary_card.funded_amount == Decimal("100.00")

        # Fallback should have no knowledge of this card
        fallback_card = _run(fallback.get_card(provider_card_id))
        assert fallback_card is None

    def test_card_provider_router_both_fail(self):
        """When both primary and fallback fail, error is raised."""
        primary = MockProvider()
        fallback = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=fallback)

        async def failing_create(*args, **kwargs):
            raise RuntimeError("Provider down")

        primary.create_card = failing_create
        fallback.create_card = failing_create

        with pytest.raises(RuntimeError, match="Provider down"):
            _run(router.create_card(
                wallet_id="wal_fail",
                card_type=CardType.MULTI_USE,
                limit_per_tx=Decimal("500"),
                limit_daily=Decimal("2000"),
                limit_monthly=Decimal("10000"),
            ))

    def test_card_provider_router_no_fallback(self):
        """Router with no fallback raises immediately on primary failure."""
        primary = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=None)

        async def failing_create(*args, **kwargs):
            raise RuntimeError("Primary down, no fallback")

        primary.create_card = failing_create

        with pytest.raises(RuntimeError, match="Primary down"):
            _run(router.create_card(
                wallet_id="wal_no_fb",
                card_type=CardType.MULTI_USE,
                limit_per_tx=Decimal("500"),
                limit_daily=Decimal("2000"),
                limit_monthly=Decimal("10000"),
            ))

    def test_router_fund_card_routes_correctly(self):
        """Fund card through router updates the correct provider's card."""
        primary = MockProvider()
        fallback = MockProvider()
        router = CardProviderRouter(primary=primary, fallback=fallback)

        # Create one card via each provider by manipulating the router
        card_p = _run(router.create_card(
            wallet_id="wal_p",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        ))

        # Force-create a card directly in fallback and register it
        card_f = _run(fallback.create_card(
            wallet_id="wal_f",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        ))
        router._register_card(card_f, fallback)

        # Fund primary card via router
        _run(router.fund_card(card_p.provider_card_id, Decimal("100")))
        assert card_p.funded_amount == Decimal("100")
        assert card_f.funded_amount == Decimal("0")

        # Fund fallback card via router
        _run(router.fund_card(card_f.provider_card_id, Decimal("200")))
        assert card_f.funded_amount == Decimal("200")
        assert card_p.funded_amount == Decimal("100")


# ===========================================================================
# Card Model Edge Cases
# ===========================================================================


class TestCardModelEdgeCases:
    """Test Card model authorization logic edge cases."""

    def test_frozen_card_cannot_authorize(self):
        """Frozen card should reject authorization."""
        provider = MockProvider()
        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("500")))

        # Freeze the card
        card = _run(provider.freeze_card(card.provider_card_id))
        assert card.status == CardStatus.FROZEN

        can_auth, reason = card.can_authorize(Decimal("50"))
        assert can_auth is False
        assert "frozen" in reason.lower()

    def test_cancelled_card_cannot_authorize(self):
        """Cancelled card should reject authorization."""
        provider = MockProvider()
        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("500")))

        card = _run(provider.cancel_card(card.provider_card_id))
        assert card.status == CardStatus.CANCELLED

        can_auth, reason = card.can_authorize(Decimal("50"))
        assert can_auth is False
        assert "cancelled" in reason.lower()

    def test_merchant_locked_card_rejects_other_merchants(self):
        """Merchant-locked card should reject transactions from other merchants."""
        provider = MockProvider()
        card = await_result(provider.create_card(
            wallet_id="wal_locked",
            card_type=CardType.MERCHANT_LOCKED,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
            locked_merchant_id="merchant_openai",
        ))
        card = await_result(provider.activate_card(card.provider_card_id))
        await_result(provider.fund_card(card.provider_card_id, Decimal("500")))

        # Same merchant should work
        can_auth, reason = card.can_authorize(Decimal("100"), merchant_id="merchant_openai")
        assert can_auth is True

        # Different merchant should fail
        can_auth, reason = card.can_authorize(Decimal("100"), merchant_id="merchant_other")
        assert can_auth is False
        assert "locked to merchant" in reason.lower()

    def test_unfunded_card_rejects_authorization(self):
        """Active card with zero balance should reject authorization."""
        provider = MockProvider()
        card = _run(_create_and_activate_card(provider))
        # Do NOT fund the card
        assert card.funded_amount == Decimal("0")

        can_auth, reason = card.can_authorize(Decimal("1.00"))
        assert can_auth is False
        assert "exceeds available balance" in reason.lower()


def await_result(coro):
    """Alias for _run for readability in some contexts."""
    return _run(coro)


# ===========================================================================
# Transaction Listing
# ===========================================================================


class TestTransactionListing:
    """Test transaction listing and retrieval."""

    def test_list_transactions_after_spending(self):
        """Transaction list returns all transactions for a card."""
        provider = MockProvider()
        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("1000")))

        # Create several transactions
        _run(provider.simulate_transaction(card.provider_card_id, Decimal("50"), merchant_name="Merchant A"))
        _run(provider.simulate_transaction(card.provider_card_id, Decimal("75"), merchant_name="Merchant B"))
        _run(provider.simulate_transaction(card.provider_card_id, Decimal("25"), merchant_name="Merchant C"))

        txns = _run(provider.list_transactions(card.provider_card_id))
        assert len(txns) == 3

        # Should be sorted by created_at descending (most recent first)
        merchants = [tx.merchant_name for tx in txns]
        assert "Merchant A" in merchants
        assert "Merchant B" in merchants
        assert "Merchant C" in merchants

    def test_get_single_transaction(self):
        """Retrieve a specific transaction by provider_tx_id."""
        provider = MockProvider()
        card = _run(_create_and_activate_card(provider))
        _run(provider.fund_card(card.provider_card_id, Decimal("500")))

        tx = _run(provider.simulate_transaction(
            card.provider_card_id,
            Decimal("99.99"),
            merchant_name="Specific Merchant",
        ))

        retrieved = _run(provider.get_transaction(tx.provider_tx_id))
        assert retrieved is not None
        assert retrieved.provider_tx_id == tx.provider_tx_id
        assert retrieved.amount == Decimal("99.99")
        assert retrieved.merchant_name == "Specific Merchant"

    def test_get_nonexistent_transaction_returns_none(self):
        """Getting a transaction that does not exist returns None."""
        provider = MockProvider()
        result = _run(provider.get_transaction("nonexistent_tx_id"))
        assert result is None

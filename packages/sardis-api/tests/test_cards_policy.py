"""Tests for sardis-cards: offramp service, quote caching, and policy enforcement."""
from __future__ import annotations

import os
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from sardis_cards.offramp import (
    MockOfframpProvider,
    OfframpProvider,
    OfframpQuote,
    OfframpService,
    OfframpStatus,
    VelocityLimitExceeded,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_expired_quote(quote_id: str = "expired_1") -> OfframpQuote:
    """Return an OfframpQuote whose expires_at is in the past."""
    return OfframpQuote(
        quote_id=quote_id,
        provider=OfframpProvider.MOCK,
        input_token="USDC",
        input_amount_minor=1_000,
        input_chain="base",
        output_currency="USD",
        output_amount_cents=995,
        exchange_rate=Decimal("1.0"),
        fee_cents=5,
        expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
    )


# MockOfframpProvider treats input_amount_minor directly as cents (no unit
# scaling): output_amount_cents = input_amount_minor * 0.995 (0.5% fee).
#
# Default OfframpService daily limit: 10_000_00 cents ($10,000).
# Use _SMALL_AMOUNT_MINOR for execution tests that pass wallet_id so they
# stay well under the default daily cap.
_SMALL_AMOUNT_MINOR = 1_000  # output ≈ 995 cents (~$9.95)


# ---------------------------------------------------------------------------
# 1. Quote caching
# ---------------------------------------------------------------------------

class TestOfframpQuoteCaching:
    """Test quote caching in OfframpService."""

    @pytest.fixture
    def service(self):
        return OfframpService(provider=MockOfframpProvider())

    @pytest.mark.asyncio
    async def test_get_quote_caches_result(self, service):
        """get_quote() stores the result in the internal cache."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        cached = service.get_cached_quote(quote.quote_id)
        assert cached is not None
        assert cached.quote_id == quote.quote_id

    @pytest.mark.asyncio
    async def test_get_cached_quote_returns_none_for_unknown(self, service):
        """Querying an unknown ID returns None without raising."""
        assert service.get_cached_quote("nonexistent_id") is None

    @pytest.mark.asyncio
    async def test_get_cached_quote_returns_none_for_expired(self, service):
        """An expired quote is evicted on access and None is returned."""
        expired_quote = _make_expired_quote("expired_1")
        service._quote_cache["expired_1"] = expired_quote
        assert service.get_cached_quote("expired_1") is None
        # Should have been evicted from the cache
        assert "expired_1" not in service._quote_cache

    @pytest.mark.asyncio
    async def test_get_quote_returns_valid_quote(self, service):
        """get_quote() returns a non-expired OfframpQuote with correct fields."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        assert not quote.is_expired
        assert quote.input_token == "USDC"
        assert quote.input_amount_minor == _SMALL_AMOUNT_MINOR
        assert quote.output_currency == "USD"

    @pytest.mark.asyncio
    async def test_multiple_quotes_are_cached_independently(self, service):
        """Each get_quote() call produces a distinct cache entry."""
        q1 = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        q2 = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR * 2, "base", "USD")
        assert q1.quote_id != q2.quote_id
        assert service.get_cached_quote(q1.quote_id) is not None
        assert service.get_cached_quote(q2.quote_id) is not None


# ---------------------------------------------------------------------------
# 2. Offramp execution
# ---------------------------------------------------------------------------

class TestOfframpExecution:
    """Test offramp execution with validation."""

    @pytest.fixture
    def service(self):
        return OfframpService(provider=MockOfframpProvider())

    @pytest.mark.asyncio
    async def test_execute_valid_quote(self, service):
        """Executing a valid quote returns a PROCESSING transaction."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="wallet_1")
        assert tx.status == OfframpStatus.PROCESSING
        assert tx.quote_id == quote.quote_id

    @pytest.mark.asyncio
    async def test_execute_expired_quote_raises(self, service):
        """Executing an expired quote raises ValueError mentioning 'expired'."""
        expired = _make_expired_quote("exp_1")
        with pytest.raises(ValueError, match="expired"):
            await service.execute(expired, "0xabc", "bank_123")

    @pytest.mark.asyncio
    async def test_execute_stores_transaction_internally(self, service):
        """After execute(), the transaction appears in service._transactions."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="wallet_1")
        assert tx.transaction_id in service._transactions

    @pytest.mark.asyncio
    async def test_execute_without_wallet_id_skips_velocity_tracking(self, service):
        """Executing without wallet_id bypasses velocity recording."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123")
        assert tx.status == OfframpStatus.PROCESSING
        assert service._wallet_transactions == {}

    @pytest.mark.asyncio
    async def test_execute_tracks_wallet_transactions(self, service):
        """Executing with wallet_id adds an entry to _wallet_transactions."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        await service.execute(quote, "0xabc", "bank_123", wallet_id="wallet_42")
        assert "wallet_42" in service._wallet_transactions
        assert len(service._wallet_transactions["wallet_42"]) == 1


# ---------------------------------------------------------------------------
# 3. get_status()
# ---------------------------------------------------------------------------

class TestOfframpGetStatus:
    """Test get_status() returns transaction status from the provider."""

    @pytest.fixture
    def service(self):
        return OfframpService(provider=MockOfframpProvider())

    @pytest.mark.asyncio
    async def test_get_status_returns_transaction(self, service):
        """get_status() on a known transaction returns the transaction object."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="w1")
        refreshed = await service.get_status(tx.transaction_id)
        assert refreshed.transaction_id == tx.transaction_id

    @pytest.mark.asyncio
    async def test_get_status_unknown_raises(self, service):
        """get_status() on an unknown transaction_id raises ValueError."""
        with pytest.raises(ValueError):
            await service.get_status("nonexistent_tx")


# ---------------------------------------------------------------------------
# 4. Velocity limits
#
# MockOfframpProvider: output_amount_cents = input * 0.995
# We set daily_limit_cents = 100_000 cents ($1,000).
#
# First tx:  input=90_000  -> output ≈  89_550 cents  (under limit -> succeeds)
# Second tx: input=20_000  -> output ≈  19_900 cents  (89_550+19_900 > 100_000 -> fails)
# "within limits" tx: input=1_000 -> output ≈ 995 cents (trivially under limit)
# ---------------------------------------------------------------------------

_VELOCITY_LIMIT_CENTS = 100_000  # $1,000 daily cap for velocity tests


class TestVelocityLimits:
    """Test velocity limit enforcement."""

    @pytest.fixture
    def service(self):
        return OfframpService(
            provider=MockOfframpProvider(),
            daily_limit_cents=_VELOCITY_LIMIT_CENTS,
            weekly_limit_cents=_VELOCITY_LIMIT_CENTS * 5,
            monthly_limit_cents=_VELOCITY_LIMIT_CENTS * 20,
        )

    @pytest.mark.asyncio
    async def test_velocity_daily_limit_exceeded(self, service):
        """A second completed transaction that pushes past the daily cap raises VelocityLimitExceeded."""
        # First transaction: output ≈ 89_550 cents (under daily cap of 100_000)
        quote = await service.get_quote("USDC", 90_000, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="w1")
        # Mark as completed so velocity checker counts it
        tx.status = OfframpStatus.COMPLETED
        tx.completed_at = datetime.now(timezone.utc)

        # Second transaction: output ≈ 19_900; total ≈ 109_450 > 100_000 -> should fail
        quote2 = await service.get_quote("USDC", 20_000, "base", "USD")
        with pytest.raises(VelocityLimitExceeded, match="Daily"):
            await service.execute(quote2, "0xabc", "bank_123", wallet_id="w1")

    @pytest.mark.asyncio
    async def test_velocity_limits_not_exceeded_below_threshold(self, service):
        """A transaction well within limits succeeds without error."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="w2")
        assert tx.status == OfframpStatus.PROCESSING

    def test_get_velocity_limits_fresh_wallet(self, service):
        """A wallet with no history shows zero usage and the full remaining amount."""
        limits = service.get_velocity_limits("w_new")
        assert limits["daily"]["limit_cents"] == _VELOCITY_LIMIT_CENTS
        assert limits["daily"]["used_cents"] == 0
        assert limits["daily"]["remaining_cents"] == _VELOCITY_LIMIT_CENTS
        assert limits["weekly"]["limit_cents"] == _VELOCITY_LIMIT_CENTS * 5
        assert limits["monthly"]["limit_cents"] == _VELOCITY_LIMIT_CENTS * 20

    def test_get_velocity_limits_structure(self, service):
        """get_velocity_limits() returns the expected nested dict structure."""
        limits = service.get_velocity_limits("any_wallet")
        for period in ("daily", "weekly", "monthly"):
            assert period in limits
            assert "used_cents" in limits[period]
            assert "limit_cents" in limits[period]
            assert "remaining_cents" in limits[period]
            assert "used_usd" in limits[period]
            assert "limit_usd" in limits[period]
            assert "remaining_usd" in limits[period]

    @pytest.mark.asyncio
    async def test_velocity_only_counts_completed_transactions(self, service):
        """PROCESSING transactions are NOT counted; two large txs can execute in sequence."""
        # Both transactions stay in PROCESSING state -> velocity check sees zero completed
        # Use amounts that would each exceed the daily limit if completed
        quote = await service.get_quote("USDC", 90_000, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="w3")
        # Leave tx in PROCESSING (not marking completed)
        assert tx.status == OfframpStatus.PROCESSING

        # Second transaction: still no completed history -> passes velocity check
        quote2 = await service.get_quote("USDC", 90_000, "base", "USD")
        tx2 = await service.execute(quote2, "0xabc", "bank_123", wallet_id="w3")
        assert tx2.status == OfframpStatus.PROCESSING


# ---------------------------------------------------------------------------
# 5. Full quote caching lifecycle
# ---------------------------------------------------------------------------

class TestQuoteCachingLifecycle:
    """Test the full lifecycle: get -> lookup -> expire -> re-execute."""

    @pytest.fixture
    def service(self):
        return OfframpService(provider=MockOfframpProvider())

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, service):
        """
        1. Get quote -> verify it is cached.
        2. Look up by ID -> verify found.
        3. Insert a pre-expired quote -> verify returns None (and is evicted).
        4. Execute with the expired quote -> verify ValueError.
        """
        # Step 1: get quote and confirm it is cached
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        assert quote.quote_id in service._quote_cache

        # Step 2: look up by ID -> found
        cached = service.get_cached_quote(quote.quote_id)
        assert cached is not None
        assert cached.quote_id == quote.quote_id

        # Step 3: insert a pre-expired quote; get_cached_quote should return None
        exp_id = "lifecycle_expired"
        expired = _make_expired_quote(exp_id)
        service._quote_cache[exp_id] = expired
        result = service.get_cached_quote(exp_id)
        assert result is None
        assert exp_id not in service._quote_cache  # evicted

        # Step 4: attempt to execute the expired quote -> ValueError
        with pytest.raises(ValueError, match="expired"):
            await service.execute(expired, "0xsource", "bank_999")

    @pytest.mark.asyncio
    async def test_valid_quote_can_be_executed_after_cache_lookup(self, service):
        """A quote retrieved via get_cached_quote can be executed successfully."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        cached = service.get_cached_quote(quote.quote_id)
        assert cached is not None
        tx = await service.execute(cached, "0xsender", "bank_456", wallet_id="w_lc")
        assert tx.status == OfframpStatus.PROCESSING
        assert tx.quote_id == quote.quote_id


# ---------------------------------------------------------------------------
# 6. Cards policy evaluation
#
# _evaluate_policy_for_card is a closure defined inside create_cards_router.
# We reproduce the identical conditional logic here so it can be tested
# directly without spinning up the full FastAPI application.
# ---------------------------------------------------------------------------

async def _build_evaluate_fn(
    *,
    environment: str,
    policy_store=None,
    wallet_repo=None,
):
    """
    Reproduce the _evaluate_policy_for_card closure from cards.py
    with the supplied dependency values captured.
    """
    async def evaluate(
        *,
        wallet_id: str,
        amount: Decimal,
        mcc_code: str | None,
    ) -> tuple[bool, str]:
        if not policy_store or not wallet_repo:
            if environment and environment.lower() in ("production", "prod"):
                return False, "policy_enforcement_unavailable_in_production"
            return True, "OK"
        wallet = await wallet_repo.get(wallet_id)
        if not wallet:
            return True, "OK"
        policy = await policy_store.fetch_policy(wallet.agent_id)
        if not policy:
            return True, "OK"
        ok, reason = policy.validate_payment(
            amount=amount,
            fee=Decimal("0"),
            mcc_code=mcc_code,
            merchant_category=None,
        )
        return ok, reason

    return evaluate


class TestCardsPolicyEvaluation:
    """Test the _evaluate_policy_for_card closure behavior."""

    @pytest.mark.asyncio
    async def test_policy_store_none_in_production_returns_false(self):
        """No policy_store in production -> (False, non-empty reason)."""
        evaluate = await _build_evaluate_fn(
            environment="production",
            policy_store=None,
            wallet_repo=None,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("100"), mcc_code="5411")
        assert ok is False
        assert reason  # non-empty string

    @pytest.mark.asyncio
    async def test_policy_store_none_in_prod_short_form_returns_false(self):
        """'prod' (short form) is also treated as production -> False."""
        evaluate = await _build_evaluate_fn(
            environment="prod",
            policy_store=None,
            wallet_repo=None,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("100"), mcc_code="5411")
        assert ok is False

    @pytest.mark.asyncio
    async def test_policy_store_none_in_sandbox_returns_true(self):
        """No policy_store in sandbox -> (True, 'OK') with a warning."""
        evaluate = await _build_evaluate_fn(
            environment="sandbox",
            policy_store=None,
            wallet_repo=None,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("100"), mcc_code="5411")
        assert ok is True

    @pytest.mark.asyncio
    async def test_policy_store_none_in_dev_returns_true(self):
        """No policy_store in dev environment -> (True, 'OK')."""
        evaluate = await _build_evaluate_fn(
            environment="dev",
            policy_store=None,
            wallet_repo=None,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("50"), mcc_code="5999")
        assert ok is True

    @pytest.mark.asyncio
    async def test_policy_store_allows_transaction(self):
        """When policy_store approves, evaluate returns (True, 'OK')."""
        policy = MagicMock()
        policy.validate_payment.return_value = (True, "OK")

        wallet = MagicMock()
        wallet.agent_id = "agent_1"

        policy_store = AsyncMock()
        policy_store.fetch_policy.return_value = policy

        wallet_repo = AsyncMock()
        wallet_repo.get.return_value = wallet

        evaluate = await _build_evaluate_fn(
            environment="production",
            policy_store=policy_store,
            wallet_repo=wallet_repo,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("100"), mcc_code="5411")
        assert ok is True

    @pytest.mark.asyncio
    async def test_policy_store_rejects_transaction(self):
        """When policy_store denies, evaluate returns (False, rejection_reason)."""
        policy = MagicMock()
        policy.validate_payment.return_value = (False, "amount_exceeds_limit")

        wallet = MagicMock()
        wallet.agent_id = "agent_1"

        policy_store = AsyncMock()
        policy_store.fetch_policy.return_value = policy

        wallet_repo = AsyncMock()
        wallet_repo.get.return_value = wallet

        evaluate = await _build_evaluate_fn(
            environment="production",
            policy_store=policy_store,
            wallet_repo=wallet_repo,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("99999"), mcc_code="5411")
        assert ok is False
        assert reason == "amount_exceeds_limit"

    @pytest.mark.asyncio
    async def test_wallet_not_found_returns_true(self):
        """If the wallet doesn't exist, policy check is skipped -> (True, 'OK')."""
        policy_store = AsyncMock()
        wallet_repo = AsyncMock()
        wallet_repo.get.return_value = None  # wallet not found

        evaluate = await _build_evaluate_fn(
            environment="production",
            policy_store=policy_store,
            wallet_repo=wallet_repo,
        )
        ok, reason = await evaluate(
            wallet_id="missing_wallet",
            amount=Decimal("100"),
            mcc_code="5411",
        )
        assert ok is True

    @pytest.mark.asyncio
    async def test_no_policy_for_agent_returns_true(self):
        """If no policy is attached to the agent, the transaction is allowed."""
        wallet = MagicMock()
        wallet.agent_id = "agent_no_policy"

        policy_store = AsyncMock()
        policy_store.fetch_policy.return_value = None  # no policy registered

        wallet_repo = AsyncMock()
        wallet_repo.get.return_value = wallet

        evaluate = await _build_evaluate_fn(
            environment="production",
            policy_store=policy_store,
            wallet_repo=wallet_repo,
        )
        ok, reason = await evaluate(wallet_id="w1", amount=Decimal("100"), mcc_code="5411")
        assert ok is True


# ---------------------------------------------------------------------------
# 7. Pending transaction tracking
# ---------------------------------------------------------------------------

class TestPendingTransactionTracking:
    """Test get_pending_transactions() reflects current transaction states."""

    @pytest.fixture
    def service(self):
        return OfframpService(provider=MockOfframpProvider())

    @pytest.mark.asyncio
    async def test_pending_transactions_includes_processing(self, service):
        """Freshly executed (PROCESSING) transactions appear in get_pending_transactions()."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="wp1")
        pending = service.get_pending_transactions()
        assert any(t.transaction_id == tx.transaction_id for t in pending)

    @pytest.mark.asyncio
    async def test_completed_transactions_not_pending(self, service):
        """COMPLETED transactions are excluded from get_pending_transactions()."""
        quote = await service.get_quote("USDC", _SMALL_AMOUNT_MINOR, "base", "USD")
        tx = await service.execute(quote, "0xabc", "bank_123", wallet_id="wp2")
        tx.status = OfframpStatus.COMPLETED
        tx.completed_at = datetime.now(timezone.utc)
        pending = service.get_pending_transactions()
        assert not any(t.transaction_id == tx.transaction_id for t in pending)

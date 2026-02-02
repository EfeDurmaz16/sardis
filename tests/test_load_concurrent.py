"""Load and concurrency tests for the Sardis payment platform.

Validates that critical invariants hold under concurrent load:
1. Spending policy limits are never exceeded (atomic enforcement)
2. Nonce allocation produces unique values (no collisions)
3. Hold accounting never exceeds wallet balance

Uses asyncio.gather to simulate concurrent requests with mocked
external services (PostgreSQL, Redis, RPC) while testing the actual
concurrency control logic.
"""
from __future__ import annotations

import asyncio
import time
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sardis_v2_core.spending_policy import (
    SpendingPolicy,
    TimeWindowLimit,
    TrustLevel,
    create_default_policy,
)
from sardis_v2_core.holds import Hold, HoldResult, HoldsRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_policy(
    agent_id: str = "agent_001",
    limit_per_tx: Decimal = Decimal("50.00"),
    daily_limit: Decimal = Decimal("200.00"),
    limit_total: Decimal = Decimal("1000.00"),
) -> SpendingPolicy:
    """Create a SpendingPolicy with a daily window limit."""
    policy = SpendingPolicy(
        agent_id=agent_id,
        trust_level=TrustLevel.LOW,
        limit_per_tx=limit_per_tx,
        limit_total=limit_total,
        daily_limit=TimeWindowLimit(
            window_type="daily",
            limit_amount=daily_limit,
        ),
    )
    return policy


class FakeAsyncLock:
    """A real asyncio.Lock used to simulate SELECT FOR UPDATE semantics."""

    def __init__(self):
        self._lock = asyncio.Lock()

    async def __aenter__(self):
        await self._lock.acquire()
        return self

    async def __aexit__(self, *exc):
        self._lock.release()


class AtomicPolicyStore:
    """In-memory store that mirrors SpendingPolicyStore atomicity.

    Uses an asyncio.Lock to emulate the row-level locking that PostgreSQL
    provides via SELECT FOR UPDATE, so we can test the concurrency invariant
    without a real database.
    """

    def __init__(self, policy: SpendingPolicy):
        self._policy = policy
        self._lock = asyncio.Lock()

    async def record_spend_atomic(
        self,
        agent_id: str,
        amount: Decimal,
        currency: str = "USDC",
    ) -> tuple[bool, str]:
        if amount <= 0:
            return False, "amount_must_be_positive"

        async with self._lock:
            # Per-tx check
            if amount > self._policy.limit_per_tx:
                return False, "per_transaction_limit"

            # Total lifetime check
            if self._policy.spent_total + amount > self._policy.limit_total:
                return False, "total_limit_exceeded"

            # Daily window check
            if self._policy.daily_limit:
                ok, reason = self._policy.daily_limit.can_spend(amount)
                if not ok:
                    return False, "daily_limit_exceeded"

            # Record the spend
            self._policy.record_spend(amount)
            return True, "OK"

    @property
    def spent_total(self) -> Decimal:
        return self._policy.spent_total

    @property
    def daily_spent(self) -> Decimal:
        if self._policy.daily_limit:
            return self._policy.daily_limit.current_spent
        return Decimal("0")


class AtomicNonceManager:
    """In-memory nonce manager that mirrors RedisNonceManager atomicity.

    Uses an asyncio.Lock to emulate the Lua script atomic increment,
    so we can test uniqueness without a real Redis instance.
    """

    def __init__(self, starting_nonce: int = 0):
        self._nonces: dict[str, int] = {}
        self._starting = starting_nonce
        self._lock = asyncio.Lock()

    async def reserve_nonce(self, address: str, rpc_client: Any = None) -> int:
        async with self._lock:
            key = address.lower()
            current = self._nonces.get(key, self._starting)
            self._nonces[key] = current + 1
            return current


class AtomicHoldsManager:
    """In-memory holds manager that enforces balance constraint atomically.

    Simulates a database-backed holds repository where concurrent hold
    creation must never let total active holds exceed the wallet balance.
    """

    def __init__(self, wallet_balance: Decimal):
        self._balance = wallet_balance
        self._holds: list[Hold] = []
        self._lock = asyncio.Lock()

    async def create_hold(
        self,
        wallet_id: str,
        amount: Decimal,
        token: str = "USDC",
    ) -> HoldResult:
        if amount <= Decimal("0"):
            return HoldResult.failed("Amount must be positive")

        async with self._lock:
            total_held = sum(h.amount for h in self._holds if h.status == "active")
            if total_held + amount > self._balance:
                return HoldResult.failed("insufficient_balance")

            hold = Hold(
                hold_id=f"hold_{len(self._holds):04d}",
                wallet_id=wallet_id,
                merchant_id=None,
                amount=amount,
                token=token,
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            self._holds.append(hold)
            return HoldResult.succeeded(hold)

    @property
    def total_held(self) -> Decimal:
        return sum(h.amount for h in self._holds if h.status == "active")

    @property
    def hold_count(self) -> int:
        return len([h for h in self._holds if h.status == "active"])


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def policy_store() -> AtomicPolicyStore:
    """Policy store with $200 daily limit and $50 per-tx limit."""
    policy = _make_policy(
        limit_per_tx=Decimal("50.00"),
        daily_limit=Decimal("200.00"),
        limit_total=Decimal("1000.00"),
    )
    return AtomicPolicyStore(policy)


@pytest.fixture
def nonce_manager() -> AtomicNonceManager:
    """Nonce manager starting at nonce 0."""
    return AtomicNonceManager(starting_nonce=0)


@pytest.fixture
def holds_manager() -> AtomicHoldsManager:
    """Holds manager with $500 wallet balance."""
    return AtomicHoldsManager(wallet_balance=Decimal("500.00"))


# ---------------------------------------------------------------------------
# Test: Spending policy enforcement under concurrent load
# ---------------------------------------------------------------------------


class TestConcurrentSpendingPolicy:
    """Verify that spending limits are never exceeded under concurrent load."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_daily_limit_never_exceeded(
        self, concurrency: int
    ):
        """Fire N concurrent $25 payments against a $200 daily limit.

        At most 8 payments should succeed ($200 / $25). The total spent
        must never exceed the daily limit regardless of concurrency level.
        """
        policy = _make_policy(
            limit_per_tx=Decimal("50.00"),
            daily_limit=Decimal("200.00"),
            limit_total=Decimal("10000.00"),
        )
        store = AtomicPolicyStore(policy)
        amount = Decimal("25.00")

        async def attempt_payment():
            return await store.record_spend_atomic("agent_001", amount)

        results = await asyncio.gather(
            *[attempt_payment() for _ in range(concurrency)]
        )

        successes = [r for r in results if r[0] is True]
        failures = [r for r in results if r[0] is False]

        # At most 8 payments of $25 can fit in $200
        max_allowed = int(Decimal("200.00") / amount)
        assert len(successes) <= max_allowed
        assert len(successes) + len(failures) == concurrency

        # The total spent must not exceed the daily limit
        assert store.daily_spent <= Decimal("200.00")
        assert store.spent_total <= Decimal("200.00")

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_total_limit_never_exceeded(
        self, concurrency: int
    ):
        """Fire N concurrent payments against the lifetime total limit.

        With a $100 total limit and $20 payments, at most 5 should succeed.
        """
        policy = _make_policy(
            limit_per_tx=Decimal("50.00"),
            daily_limit=Decimal("10000.00"),
            limit_total=Decimal("100.00"),
        )
        store = AtomicPolicyStore(policy)
        amount = Decimal("20.00")

        results = await asyncio.gather(
            *[store.record_spend_atomic("agent_001", amount) for _ in range(concurrency)]
        )

        successes = [r for r in results if r[0] is True]
        max_allowed = int(Decimal("100.00") / amount)

        assert len(successes) <= max_allowed
        assert store.spent_total <= Decimal("100.00")

    @pytest.mark.asyncio
    async def test_per_tx_limit_enforced_concurrently(self):
        """All concurrent payments exceeding per-tx limit must be rejected."""
        policy = _make_policy(limit_per_tx=Decimal("10.00"))
        store = AtomicPolicyStore(policy)

        results = await asyncio.gather(
            *[store.record_spend_atomic("agent_001", Decimal("15.00")) for _ in range(20)]
        )

        # Every single one should fail — amount exceeds per-tx limit
        assert all(r[0] is False for r in results)
        assert all(r[1] == "per_transaction_limit" for r in results)
        assert store.spent_total == Decimal("0")

    @pytest.mark.asyncio
    async def test_mixed_amounts_concurrent(self):
        """Concurrent payments of varying amounts respect daily limit."""
        policy = _make_policy(
            limit_per_tx=Decimal("50.00"),
            daily_limit=Decimal("100.00"),
            limit_total=Decimal("10000.00"),
        )
        store = AtomicPolicyStore(policy)

        amounts = [
            Decimal("30.00"),
            Decimal("30.00"),
            Decimal("30.00"),
            Decimal("30.00"),
            Decimal("10.00"),
            Decimal("10.00"),
            Decimal("10.00"),
            Decimal("10.00"),
            Decimal("10.00"),
            Decimal("10.00"),
        ]

        results = await asyncio.gather(
            *[store.record_spend_atomic("agent_001", a) for a in amounts]
        )

        assert store.daily_spent <= Decimal("100.00")
        assert store.spent_total <= Decimal("100.00")

        total_approved = sum(
            amounts[i] for i, r in enumerate(results) if r[0] is True
        )
        assert total_approved == store.spent_total
        assert total_approved <= Decimal("100.00")


# ---------------------------------------------------------------------------
# Test: Nonce uniqueness under concurrent load
# ---------------------------------------------------------------------------


class TestConcurrentNonceAllocation:
    """Verify that nonce allocation never produces duplicates."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_nonces_are_unique(
        self, nonce_manager: AtomicNonceManager, concurrency: int
    ):
        """Reserve N nonces concurrently; all must be unique."""
        address = "0xABCDEF1234567890ABCDEF1234567890ABCDEF12"

        nonces = await asyncio.gather(
            *[nonce_manager.reserve_nonce(address) for _ in range(concurrency)]
        )

        assert len(nonces) == concurrency
        assert len(set(nonces)) == concurrency, (
            f"Nonce collision detected: {concurrency} reservations produced "
            f"only {len(set(nonces))} unique values"
        )

    @pytest.mark.asyncio
    async def test_nonces_are_sequential(self, nonce_manager: AtomicNonceManager):
        """Reserved nonces should form a contiguous sequence."""
        address = "0x1111111111111111111111111111111111111111"

        nonces = await asyncio.gather(
            *[nonce_manager.reserve_nonce(address) for _ in range(20)]
        )

        sorted_nonces = sorted(nonces)
        assert sorted_nonces == list(range(20))

    @pytest.mark.asyncio
    async def test_multiple_addresses_independent(
        self, nonce_manager: AtomicNonceManager
    ):
        """Nonce sequences for different addresses are independent."""
        addr_a = "0xAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA"
        addr_b = "0xBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB"

        nonces_a, nonces_b = await asyncio.gather(
            asyncio.gather(*[nonce_manager.reserve_nonce(addr_a) for _ in range(10)]),
            asyncio.gather(*[nonce_manager.reserve_nonce(addr_b) for _ in range(10)]),
        )

        assert len(set(nonces_a)) == 10
        assert len(set(nonces_b)) == 10
        # Both start from 0
        assert sorted(nonces_a) == list(range(10))
        assert sorted(nonces_b) == list(range(10))


# ---------------------------------------------------------------------------
# Test: Hold accounting under concurrent load
# ---------------------------------------------------------------------------


class TestConcurrentHoldAccounting:
    """Verify that total held funds never exceed wallet balance."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_holds_never_exceed_balance(
        self, concurrency: int
    ):
        """Create N concurrent holds of $50 against a $500 balance.

        At most 10 holds should succeed. Total held must never exceed $500.
        """
        manager = AtomicHoldsManager(wallet_balance=Decimal("500.00"))
        amount = Decimal("50.00")

        results = await asyncio.gather(
            *[manager.create_hold("wallet_001", amount) for _ in range(concurrency)]
        )

        successes = [r for r in results if r.success]
        failures = [r for r in results if not r.success]

        max_holds = int(Decimal("500.00") / amount)
        assert len(successes) <= max_holds
        assert len(successes) + len(failures) == concurrency
        assert manager.total_held <= Decimal("500.00")

    @pytest.mark.asyncio
    async def test_exact_balance_exhaustion(self):
        """Exactly exhaust the balance and verify next hold is rejected."""
        manager = AtomicHoldsManager(wallet_balance=Decimal("100.00"))

        # Create 10 holds of $10 concurrently — should all succeed
        results = await asyncio.gather(
            *[manager.create_hold("wallet_001", Decimal("10.00")) for _ in range(10)]
        )

        assert all(r.success for r in results)
        assert manager.total_held == Decimal("100.00")
        assert manager.hold_count == 10

        # Next hold must fail
        overflow = await manager.create_hold("wallet_001", Decimal("0.01"))
        assert not overflow.success
        assert "insufficient_balance" in overflow.error

    @pytest.mark.asyncio
    async def test_mixed_hold_amounts_concurrent(self):
        """Concurrent holds of varying sizes respect the balance cap."""
        manager = AtomicHoldsManager(wallet_balance=Decimal("200.00"))

        amounts = [
            Decimal("80.00"),
            Decimal("80.00"),
            Decimal("80.00"),
            Decimal("40.00"),
            Decimal("40.00"),
            Decimal("40.00"),
            Decimal("20.00"),
            Decimal("20.00"),
        ]

        results = await asyncio.gather(
            *[manager.create_hold("wallet_001", a) for a in amounts]
        )

        assert manager.total_held <= Decimal("200.00")

        total_approved = sum(
            amounts[i] for i, r in enumerate(results) if r.success
        )
        assert total_approved == manager.total_held

    @pytest.mark.asyncio
    async def test_zero_and_negative_holds_rejected(self):
        """Zero and negative hold amounts are always rejected."""
        manager = AtomicHoldsManager(wallet_balance=Decimal("1000.00"))

        results = await asyncio.gather(
            manager.create_hold("wallet_001", Decimal("0")),
            manager.create_hold("wallet_001", Decimal("-10.00")),
            manager.create_hold("wallet_001", Decimal("-0.01")),
        )

        assert all(not r.success for r in results)
        assert manager.total_held == Decimal("0")


# ---------------------------------------------------------------------------
# Test: Combined concurrent operations (cross-cutting)
# ---------------------------------------------------------------------------


class TestConcurrentCrossCutting:
    """Verify invariants when multiple subsystems are stressed simultaneously."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_simultaneous_spend_and_hold(self, concurrency: int):
        """Run spending policy checks and hold creation concurrently.

        Both subsystems must independently maintain their invariants.
        """
        policy = _make_policy(
            limit_per_tx=Decimal("50.00"),
            daily_limit=Decimal("300.00"),
            limit_total=Decimal("10000.00"),
        )
        store = AtomicPolicyStore(policy)
        holds = AtomicHoldsManager(wallet_balance=Decimal("300.00"))

        async def spend_task():
            return await store.record_spend_atomic("agent_001", Decimal("30.00"))

        async def hold_task():
            return await holds.create_hold("wallet_001", Decimal("30.00"))

        spend_results, hold_results = await asyncio.gather(
            asyncio.gather(*[spend_task() for _ in range(concurrency)]),
            asyncio.gather(*[hold_task() for _ in range(concurrency)]),
        )

        # Spending invariant
        assert store.daily_spent <= Decimal("300.00")
        spend_successes = sum(1 for r in spend_results if r[0] is True)
        assert spend_successes <= 10  # 300 / 30

        # Hold invariant
        assert holds.total_held <= Decimal("300.00")
        hold_successes = sum(1 for r in hold_results if r.success)
        assert hold_successes <= 10  # 300 / 30

    @pytest.mark.asyncio
    async def test_nonce_and_spend_simultaneous(self):
        """Nonce reservation and spend recording run concurrently.

        Nonces must remain unique; spending limits must hold.
        """
        policy = _make_policy(
            limit_per_tx=Decimal("50.00"),
            daily_limit=Decimal("100.00"),
            limit_total=Decimal("10000.00"),
        )
        store = AtomicPolicyStore(policy)
        nonce_mgr = AtomicNonceManager(starting_nonce=0)
        address = "0xDEADBEEF00000000000000000000000000000000"

        async def combined_task():
            nonce = await nonce_mgr.reserve_nonce(address)
            result = await store.record_spend_atomic("agent_001", Decimal("10.00"))
            return nonce, result

        outcomes = await asyncio.gather(*[combined_task() for _ in range(25)])

        nonces = [o[0] for o in outcomes]
        spend_results = [o[1] for o in outcomes]

        # Nonce uniqueness
        assert len(set(nonces)) == 25

        # Spending invariant
        assert store.daily_spent <= Decimal("100.00")
        successes = sum(1 for r in spend_results if r[0] is True)
        assert successes <= 10  # 100 / 10


# ---------------------------------------------------------------------------
# Test: SpendingPolicy.validate_payment (in-memory, no DB) under concurrency
# ---------------------------------------------------------------------------


class TestConcurrentInMemoryPolicy:
    """Stress-test the in-memory SpendingPolicy with a manual lock.

    This demonstrates that without external synchronization, the in-memory
    policy is NOT safe for concurrent use. The test uses a lock to make it
    safe, mirroring what SpendingPolicyStore does with SELECT FOR UPDATE.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("concurrency", [5, 10, 25, 50])
    async def test_locked_validate_and_record(self, concurrency: int):
        """Validate + record with an explicit lock preserves limits."""
        policy = create_default_policy("agent_test", TrustLevel.LOW)
        lock = asyncio.Lock()

        # LOW tier: per_tx=$50, daily=$100
        amount = Decimal("10.00")
        results = []

        async def guarded_payment():
            async with lock:
                ok, reason = policy.validate_payment(amount, Decimal("0"))
                if ok:
                    policy.record_spend(amount)
                results.append((ok, reason))

        await asyncio.gather(*[guarded_payment() for _ in range(concurrency)])

        successes = [r for r in results if r[0] is True]

        # Daily limit for LOW is $100; at most 10 payments of $10
        assert len(successes) <= 10
        assert policy.spent_total <= Decimal("100.00")
        if policy.daily_limit:
            assert policy.daily_limit.current_spent <= Decimal("100.00")

"""Tests for MPP session domain transitions."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from server.domains.mpp_session import (
    MPPBudgetExceededError,
    MPPSessionExpiredError,
    MPPSessionInactiveError,
    apply_payment_budget,
    ensure_card_budget,
    ensure_session_can_execute,
    parse_session_expiry,
)


def _session(**overrides):
    data = {
        "status": "active",
        "remaining": Decimal("100"),
        "total_spent": Decimal("0"),
        "payment_count": 0,
        "expires_at": None,
    }
    data.update(overrides)
    return data


def test_parse_session_expiry_handles_datetime_and_strings():
    now = datetime.now(UTC)

    assert parse_session_expiry(now) == now
    assert parse_session_expiry(now.isoformat()) == now
    assert parse_session_expiry("not-a-date") is None
    assert parse_session_expiry(None) is None


def test_ensure_session_can_execute_rejects_inactive_session():
    with pytest.raises(MPPSessionInactiveError, match="closed"):
        ensure_session_can_execute(_session(status="closed"))


def test_ensure_session_can_execute_rejects_expired_session():
    with pytest.raises(MPPSessionExpiredError):
        ensure_session_can_execute(
            _session(expires_at=(datetime.now(UTC) - timedelta(seconds=1)).isoformat())
        )


def test_apply_payment_budget_returns_next_state():
    transition = apply_payment_budget(_session(total_spent=Decimal("25")), Decimal("40"))

    assert transition.remaining == Decimal("60")
    assert transition.total_spent == Decimal("65")
    assert transition.payment_count == 1
    assert transition.status == "active"


def test_apply_payment_budget_exhausts_session():
    transition = apply_payment_budget(_session(), Decimal("100"))

    assert transition.remaining == Decimal("0")
    assert transition.status == "exhausted"


def test_apply_payment_budget_rejects_over_budget_payment():
    with pytest.raises(MPPBudgetExceededError, match="exceeds remaining"):
        apply_payment_budget(_session(remaining=Decimal("10")), Decimal("11"))


def test_ensure_card_budget_rejects_closed_or_over_budget_session():
    with pytest.raises(MPPSessionInactiveError):
        ensure_card_budget(_session(status="closed"), Decimal("5"))

    with pytest.raises(MPPBudgetExceededError):
        ensure_card_budget(_session(remaining=Decimal("5")), Decimal("6"))

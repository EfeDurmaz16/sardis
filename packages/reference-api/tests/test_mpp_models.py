"""Tests for MPP API model helpers."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from server.models.mpp import mpp_session_response_from_record


def test_mpp_session_response_from_record_normalizes_values():
    created_at = datetime.now(UTC)
    response = mpp_session_response_from_record(
        {
            "session_id": "mpp_sess_123",
            "mandate_id": None,
            "wallet_id": "wallet_123",
            "agent_id": "agent_123",
            "method": "tempo",
            "chain": "tempo",
            "currency": "USDC",
            "spending_limit": Decimal("100"),
            "remaining": Decimal("75.5"),
            "total_spent": Decimal("24.5"),
            "payment_count": 2,
            "status": "active",
            "created_at": created_at,
            "closed_at": None,
            "expires_at": None,
        },
        next_steps=["next"],
    )

    assert response.session_id == "mpp_sess_123"
    assert response.wallet_id == "wallet_123"
    assert response.spending_limit == "100"
    assert response.remaining == "75.5"
    assert response.total_spent == "24.5"
    assert response.created_at == str(created_at)
    assert response.closed_at is None
    assert response.expires_at is None
    assert response.next_steps == ["next"]

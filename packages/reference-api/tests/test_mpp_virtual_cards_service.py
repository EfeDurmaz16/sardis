"""Tests for MPP virtual card helpers."""

from __future__ import annotations

from decimal import Decimal

from server.models.mpp import IssueCardRequest
from server.services.mpp_virtual_cards import issue_sandbox_card, should_issue_sandbox_card


def test_should_issue_sandbox_card_by_default(monkeypatch):
    monkeypatch.delenv("SARDIS_CHAIN_MODE", raising=False)
    monkeypatch.delenv("SARDIS_VIRTUAL_CARDS_SANDBOX", raising=False)

    assert should_issue_sandbox_card() is True


def test_should_issue_sandbox_card_when_override_is_enabled(monkeypatch):
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "live")
    monkeypatch.setenv("SARDIS_VIRTUAL_CARDS_SANDBOX", "true")

    assert should_issue_sandbox_card() is True


def test_should_not_issue_sandbox_card_in_live_mode(monkeypatch):
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "live")
    monkeypatch.delenv("SARDIS_VIRTUAL_CARDS_SANDBOX", raising=False)

    assert should_issue_sandbox_card() is False


def test_issue_sandbox_card_returns_redacted_test_card_shape():
    response = issue_sandbox_card(
        IssueCardRequest(amount=Decimal("25.50"), currency="USD")
    )

    assert response.card_id.startswith("sandbox_card_")
    assert response.card_number.startswith("4000 00")
    assert len(response.cvv) == 3
    assert response.amount == "25.50"
    assert response.currency == "USD"
    assert response.status == "ready"
    assert response.card_type == "single_use"
    assert response.sandbox is True

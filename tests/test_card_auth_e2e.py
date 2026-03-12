"""
End-to-End Card Authorization Tests for Sardis

Tests the FULL card authorization flow:
  agent creates card -> simulated purchase -> webhook arrives ->
  policy engine checks -> approve/decline decision.

Run with: pytest tests/test_card_auth_e2e.py -v
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from dataclasses import dataclass
from decimal import Decimal

import pytest
from sardis_cards.models import (
    Card,
    CardStatus,
    CardTransaction,
    CardType,
    FundingSource,
    TransactionStatus,
)
from sardis_cards.providers.mock import MockProvider
from sardis_cards.webhooks import (
    ASADecision,
    ASAHandler,
    ASAResponse,
    AutoConversionWebhookHandler,
    CardWebhookHandler,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SECRET = "test_secret"


def _signed_payload(secret: str, payload: dict) -> tuple[bytes, str]:
    """Create a valid HMAC-SHA256-signed payload for the ASA handler."""
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, signature


def _asa_payload(
    *,
    token: str = "auth_1",
    card_token: str = "card_1",
    amount: int = 4999,
    merchant_descriptor: str = "Amazon Marketplace",
    mcc: str = "5734",
    acceptor_id: str = "merchant_1",
    currency: str = "USD",
) -> dict:
    """Build an ASA authorization payload."""
    return {
        "payload": {
            "token": token,
            "card_token": card_token,
            "amount": amount,
            "merchant": {
                "descriptor": merchant_descriptor,
                "mcc": mcc,
                "acceptor_id": acceptor_id,
                "currency": currency,
            },
        }
    }


def _make_card_lookup(cards: dict[str, Card]):
    """Return an async card_lookup callable backed by an in-memory dict."""

    async def _lookup(card_token: str) -> Card | None:
        return cards.get(card_token)

    return _lookup


def _make_policy_check(allowed: bool = True, reason: str = "OK"):
    """Return a simple async policy_check callable."""

    async def _check(wallet_id, amount, mcc, merchant_name):
        return allowed, reason

    return _check


# ---------------------------------------------------------------------------
# 1. Full card auth — APPROVE
# ---------------------------------------------------------------------------


def test_full_card_auth_approve(monkeypatch):
    """Create card with MockProvider, wire up ASA handler, send valid auth -> APPROVE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
            policy_check=_make_policy_check(allowed=True, reason="OK"),
        )

        payload_dict = _asa_payload(
            token="auth_approve_1",
            card_token=card.card_id,
            amount=2500,  # $25.00
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.APPROVE
        assert result.reason == "approved"
        assert result.token == "auth_approve_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 2. Blocked MCC — gambling (7995)
# ---------------------------------------------------------------------------


def test_card_auth_blocked_mcc_gambling(monkeypatch):
    """Auth request with MCC 7995 (gambling) -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
    )

    payload_dict = _asa_payload(
        token="auth_gambling_1",
        mcc="7995",
        merchant_descriptor="Online Casino",
    )
    body, sig = _signed_payload(SECRET, payload_dict)
    result = asyncio.run(handler.handle_authorization(body, sig))

    assert result.decision == ASADecision.DECLINE
    assert result.reason == "blocked_merchant_category_7995"
    assert result.token == "auth_gambling_1"


# ---------------------------------------------------------------------------
# 3. Blocked MCC — ATM (6011)
# ---------------------------------------------------------------------------


def test_card_auth_blocked_mcc_atm(monkeypatch):
    """Auth request with MCC 6011 (ATM cash withdrawal) -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
    )

    payload_dict = _asa_payload(
        token="auth_atm_1",
        mcc="6011",
        merchant_descriptor="ATM Withdrawal",
    )
    body, sig = _signed_payload(SECRET, payload_dict)
    result = asyncio.run(handler.handle_authorization(body, sig))

    assert result.decision == ASADecision.DECLINE
    assert result.reason == "blocked_merchant_category_6011"
    assert result.token == "auth_atm_1"


# ---------------------------------------------------------------------------
# 4. Over per-transaction limit
# ---------------------------------------------------------------------------


def test_card_auth_over_per_tx_limit(monkeypatch):
    """Card has $500 per-tx limit, auth for $600 -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("5000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
        )

        payload_dict = _asa_payload(
            token="auth_over_tx_1",
            card_token=card.card_id,
            amount=60000,  # $600.00 in cents
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert "exceeds per-transaction limit" in result.reason
        assert result.token == "auth_over_tx_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 5. Over daily limit
# ---------------------------------------------------------------------------


def test_card_auth_over_daily_limit(monkeypatch):
    """Card has $100 daily limit, already spent $90, auth for $20 -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("100"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        # Simulate $90 already spent today
        card.spent_today = Decimal("90")

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
        )

        payload_dict = _asa_payload(
            token="auth_over_daily_1",
            card_token=card.card_id,
            amount=2000,  # $20.00 in cents -> $90 + $20 = $110 > $100 limit
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert "exceeds available balance" in result.reason
        assert result.token == "auth_over_daily_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 6. Frozen card
# ---------------------------------------------------------------------------


def test_card_auth_frozen_card(monkeypatch):
    """Frozen card -> DECLINE with 'Card is frozen'."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        # Freeze the card
        card = await provider.freeze_card(card.provider_card_id)
        assert card.status == CardStatus.FROZEN

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
        )

        payload_dict = _asa_payload(
            token="auth_frozen_1",
            card_token=card.card_id,
            amount=500,
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert "frozen" in result.reason.lower()
        assert result.token == "auth_frozen_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 7. Policy deny
# ---------------------------------------------------------------------------


def test_card_auth_policy_deny(monkeypatch):
    """Policy check returns (False, 'daily_limit_exceeded') -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
            policy_check=_make_policy_check(allowed=False, reason="daily_limit_exceeded"),
        )

        payload_dict = _asa_payload(
            token="auth_policy_deny_1",
            card_token=card.card_id,
            amount=1000,  # $10.00
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert result.reason == "daily_limit_exceeded"
        assert result.token == "auth_policy_deny_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 8. Policy engine failure — fail-closed
# ---------------------------------------------------------------------------


def test_card_auth_policy_engine_failure_fail_closed(monkeypatch):
    """Policy check raises exception -> DECLINE with 'policy_check_failed'."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")

    async def _policy_explodes(wallet_id, amount, mcc, merchant_name):
        raise RuntimeError("policy engine unavailable")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
            policy_check=_policy_explodes,
        )

        payload_dict = _asa_payload(
            token="auth_policy_fail_1",
            card_token=card.card_id,
            amount=500,
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert result.reason == "policy_check_failed"
        assert result.token == "auth_policy_fail_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 9. Invalid signature
# ---------------------------------------------------------------------------


def test_card_auth_invalid_signature(monkeypatch):
    """Wrong signature -> DECLINE with 'invalid_signature'."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
    )

    payload_dict = _asa_payload(token="auth_bad_sig_1")
    body = json.dumps(payload_dict, separators=(",", ":"), sort_keys=True).encode("utf-8")
    wrong_signature = hmac.new(
        b"wrong_secret", body, hashlib.sha256
    ).hexdigest()

    result = asyncio.run(handler.handle_authorization(body, wrong_signature))

    assert result.decision == ASADecision.DECLINE
    assert result.reason == "invalid_signature"
    assert result.token == ""


# ---------------------------------------------------------------------------
# 10. Idempotency — same auth token twice
# ---------------------------------------------------------------------------


def test_card_auth_idempotency(monkeypatch):
    """Same auth token sent twice -> second returns APPROVE with 'duplicate_approved'."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
            policy_check=_make_policy_check(allowed=True, reason="OK"),
        )

        payload_dict = _asa_payload(
            token="auth_idemp_1",
            card_token=card.card_id,
            amount=1500,  # $15.00
        )
        body, sig = _signed_payload(SECRET, payload_dict)

        # First call — should APPROVE normally
        result1 = await handler.handle_authorization(body, sig)
        assert result1.decision == ASADecision.APPROVE
        assert result1.reason == "approved"

        # Second call with same token — should APPROVE as duplicate
        result2 = await handler.handle_authorization(body, sig)
        assert result2.decision == ASADecision.APPROVE
        assert result2.reason == "duplicate_approved"
        assert result2.token == "auth_idemp_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 11. Subscription auto-approve
# ---------------------------------------------------------------------------


def test_card_auth_subscription_auto_approve(monkeypatch):
    """Subscription matcher returns match -> APPROVE with 'subscription_matched'."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    @dataclass
    class FakeSubscription:
        id: str = "sub_netflix_1"
        merchant_descriptor: str = "Netflix"

    async def _subscription_matcher(card_token, merchant_descriptor, amount_cents):
        if "Netflix" in merchant_descriptor:
            return FakeSubscription()
        return None

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            subscription_matcher=_subscription_matcher,
        )

        payload_dict = _asa_payload(
            token="auth_sub_1",
            card_token=card.card_id,
            amount=1599,  # $15.99
            merchant_descriptor="Netflix Monthly",
            mcc="4899",
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.APPROVE
        assert result.reason == "subscription_matched"
        assert result.token == "auth_sub_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 12. Merchant-locked card — wrong merchant
# ---------------------------------------------------------------------------


def test_card_auth_merchant_locked_wrong_merchant(monkeypatch):
    """Merchant-locked card auth from different merchant -> DECLINE."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_1",
            card_type=CardType.MERCHANT_LOCKED,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
            locked_merchant_id="merchant_allowed",
        )
        card = await provider.activate_card(card.provider_card_id)
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))

        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
        )

        payload_dict = _asa_payload(
            token="auth_locked_1",
            card_token=card.card_id,
            amount=1000,
            acceptor_id="merchant_different",  # not the locked merchant
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.DECLINE
        assert "locked to merchant" in result.reason
        assert result.token == "auth_locked_1"

    asyncio.run(_run())


# ---------------------------------------------------------------------------
# 13. AutoConversionWebhookHandler — triggers callback on auth
# ---------------------------------------------------------------------------


def test_auto_conversion_webhook(monkeypatch):
    """AutoConversionWebhookHandler triggers on_conversion_needed callback on auth."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    conversions_triggered: list[tuple[str, int, str]] = []

    def _on_conversion(wallet_id: str, amount_cents: int, tx_id: str):
        conversions_triggered.append((wallet_id, amount_cents, tx_id))

    webhook_handler = CardWebhookHandler(secret=SECRET, provider="lithic")

    card_wallet_map = {"card_conv_1": "wallet_conv_1"}

    auto_handler = AutoConversionWebhookHandler(
        webhook_handler=webhook_handler,
        card_to_wallet_map=card_wallet_map,
        on_conversion_needed=_on_conversion,
    )

    # Build a Lithic-style transaction.created webhook payload
    webhook_payload = {
        "type": "transaction.created",
        "token": "evt_conv_1",
        "payload": {
            "token": "txn_conv_1",
            "card_token": "card_conv_1",
            "amount": 2500,  # $25.00 in cents
            "merchant": {
                "descriptor": "AWS Cloud Services",
                "mcc": "5734",
                "acceptor_id": "aws_1",
                "currency": "USD",
            },
        },
    }

    body, sig = _signed_payload(SECRET, webhook_payload)
    result = asyncio.run(auto_handler.process_webhook(body, sig))

    assert result is not None
    assert result["action"] == "conversion_triggered"
    assert result["wallet_id"] == "wallet_conv_1"
    assert result["card_id"] == "card_conv_1"
    assert result["amount_cents"] == 2500
    assert len(conversions_triggered) == 1
    assert conversions_triggered[0][0] == "wallet_conv_1"
    assert conversions_triggered[0][1] == 2500


# ---------------------------------------------------------------------------
# 14. Full lifecycle — create -> activate -> auth -> freeze -> auth (declined)
# ---------------------------------------------------------------------------


def test_card_lifecycle_create_activate_auth_freeze(monkeypatch):
    """Full lifecycle: create -> activate -> fund -> auth (approved) -> freeze -> auth (declined)."""
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    async def _run():
        # --- Step 1: Create card ---
        provider = MockProvider()
        card = await provider.create_card(
            wallet_id="wallet_lifecycle_1",
            card_type=CardType.MULTI_USE,
            limit_per_tx=Decimal("500"),
            limit_daily=Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
        assert card.status == CardStatus.PENDING

        # --- Step 2: Activate ---
        card = await provider.activate_card(card.provider_card_id)
        assert card.status == CardStatus.ACTIVE

        # --- Step 3: Fund ---
        card = await provider.fund_card(card.provider_card_id, Decimal("1000"))
        assert card.funded_amount == Decimal("1000")

        # Keep a reference dict for the lookup
        cards = {card.card_id: card}

        handler = ASAHandler(
            webhook_handler=CardWebhookHandler(secret=SECRET, provider="lithic"),
            card_lookup=_make_card_lookup(cards),
            policy_check=_make_policy_check(allowed=True, reason="OK"),
        )

        # --- Step 4: Authorize (should approve) ---
        payload_dict = _asa_payload(
            token="auth_lifecycle_1",
            card_token=card.card_id,
            amount=2500,
        )
        body, sig = _signed_payload(SECRET, payload_dict)
        result = await handler.handle_authorization(body, sig)

        assert result.decision == ASADecision.APPROVE
        assert result.reason == "approved"

        # --- Step 5: Simulate approved transaction on MockProvider ---
        tx = await provider.simulate_transaction(
            provider_card_id=card.provider_card_id,
            amount=Decimal("25.00"),
            merchant_name="Amazon Marketplace",
            merchant_category="5734",
            status=TransactionStatus.APPROVED,
        )
        assert tx.status == TransactionStatus.APPROVED
        assert card.spent_today == Decimal("25.00")

        # --- Step 6: Freeze card ---
        card = await provider.freeze_card(card.provider_card_id)
        assert card.status == CardStatus.FROZEN

        # Update reference in lookup dict (same object, but verify)
        cards[card.card_id] = card

        # --- Step 7: Authorize after freeze (should decline) ---
        payload_dict_2 = _asa_payload(
            token="auth_lifecycle_2",
            card_token=card.card_id,
            amount=500,
        )
        body2, sig2 = _signed_payload(SECRET, payload_dict_2)
        result2 = await handler.handle_authorization(body2, sig2)

        assert result2.decision == ASADecision.DECLINE
        assert "frozen" in result2.reason.lower()
        assert result2.token == "auth_lifecycle_2"

    asyncio.run(_run())

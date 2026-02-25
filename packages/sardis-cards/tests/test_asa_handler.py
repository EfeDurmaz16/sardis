from __future__ import annotations

import asyncio
import hashlib
import hmac
import json

from sardis_cards.webhooks import ASADecision, ASAHandler, CardWebhookHandler


def _signed_payload(secret: str, payload: dict) -> tuple[bytes, str]:
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return body, signature


def _asa_payload(*, token: str = "auth_1", card_token: str = "card_1") -> dict:
    return {
        "payload": {
            "token": token,
            "card_token": card_token,
            "amount": 1299,
            "merchant": {
                "descriptor": "Amazon Marketplace",
                "mcc": "5734",
                "acceptor_id": "merchant_1",
                "currency": "USD",
            },
        }
    }


def test_asa_card_lookup_error_fail_open_in_dev(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")
    monkeypatch.delenv("SARDIS_ASA_FAIL_CLOSED_ON_CARD_LOOKUP_ERROR", raising=False)
    secret = "asa_secret"
    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=secret, provider="lithic"),
        card_lookup=lambda _card_token: (_ for _ in ()).throw(RuntimeError("lookup_down")),
    )
    payload, signature = _signed_payload(secret, _asa_payload())
    result = asyncio.run(handler.handle_authorization(payload, signature))
    assert result.decision == ASADecision.APPROVE
    assert result.reason == "approved"


def test_asa_card_lookup_error_fail_closed_in_production(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.delenv("SARDIS_ASA_FAIL_CLOSED_ON_CARD_LOOKUP_ERROR", raising=False)
    secret = "asa_secret"
    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=secret, provider="lithic"),
        card_lookup=lambda _card_token: (_ for _ in ()).throw(RuntimeError("lookup_down")),
    )
    payload, signature = _signed_payload(secret, _asa_payload(token="auth_prod_1"))
    result = asyncio.run(handler.handle_authorization(payload, signature))
    assert result.decision == ASADecision.DECLINE
    assert result.reason == "card_lookup_failed"


def test_asa_card_lookup_error_can_be_overridden_to_fail_open(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_ASA_FAIL_CLOSED_ON_CARD_LOOKUP_ERROR", "0")
    secret = "asa_secret"
    handler = ASAHandler(
        webhook_handler=CardWebhookHandler(secret=secret, provider="lithic"),
        card_lookup=lambda _card_token: (_ for _ in ()).throw(RuntimeError("lookup_down")),
    )
    payload, signature = _signed_payload(secret, _asa_payload(token="auth_prod_2"))
    result = asyncio.run(handler.handle_authorization(payload, signature))
    assert result.decision == ASADecision.APPROVE
    assert result.reason == "approved"

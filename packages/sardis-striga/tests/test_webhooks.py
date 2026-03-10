"""Tests for Striga webhook handler."""
from __future__ import annotations

import hashlib
import hmac
import json

import pytest

from sardis_striga.exceptions import StrigaWebhookVerificationError
from sardis_striga.webhooks import (
    StrigaWebhookEvent,
    StrigaWebhookEventType,
    StrigaWebhookHandler,
)


@pytest.fixture
def handler():
    return StrigaWebhookHandler(webhook_secret="test_webhook_secret")


class TestStrigaWebhookHandler:
    """Tests for StrigaWebhookHandler."""

    def test_verify_valid_signature(self, handler):
        """Test valid signature verification."""
        payload = b'{"type":"card.created","data":{}}'
        signature = hmac.new(
            b"test_webhook_secret",
            payload,
            hashlib.sha256,
        ).hexdigest()

        assert handler.verify_signature(payload, signature) is True

    def test_verify_invalid_signature(self, handler):
        """Test invalid signature is rejected."""
        payload = b'{"type":"card.created","data":{}}'
        assert handler.verify_signature(payload, "invalid_signature") is False

    def test_parse_card_event(self, handler):
        """Test parsing card webhook event."""
        payload = json.dumps({
            "eventId": "evt_123",
            "type": "card.created",
            "data": {
                "cardId": "card_456",
                "userId": "user_789",
                "walletId": "wal_abc",
            },
        }).encode()

        event = handler.parse_event(payload)

        assert event.event_id == "evt_123"
        assert event.event_type == StrigaWebhookEventType.CARD_CREATED
        assert event.card_id == "card_456"
        assert event.user_id == "user_789"
        assert event.wallet_id == "wal_abc"

    def test_parse_transaction_event(self, handler):
        """Test parsing transaction webhook event."""
        payload = json.dumps({
            "eventId": "evt_tx_001",
            "type": "transaction.authorization",
            "data": {
                "transactionId": "tx_001",
                "cardId": "card_456",
                "amount": 2500,
                "currency": "EUR",
            },
        }).encode()

        event = handler.parse_event(payload)

        assert event.event_type == StrigaWebhookEventType.TRANSACTION_AUTHORIZATION
        assert event.transaction_id == "tx_001"
        assert event.amount_cents == 2500
        assert event.currency == "EUR"

    def test_parse_sepa_event(self, handler):
        """Test parsing SEPA webhook event."""
        payload = json.dumps({
            "eventId": "evt_sepa_001",
            "type": "sepa.incoming",
            "data": {
                "walletId": "wal_abc",
                "amount": 10000,
                "currency": "EUR",
            },
        }).encode()

        event = handler.parse_event(payload)

        assert event.event_type == StrigaWebhookEventType.SEPA_INCOMING
        assert event.wallet_id == "wal_abc"

    def test_verify_and_parse_valid(self, handler):
        """Test verify_and_parse with valid signature."""
        payload = json.dumps({
            "eventId": "evt_123",
            "type": "card.activated",
            "data": {"cardId": "card_456"},
        }).encode()

        signature = hmac.new(
            b"test_webhook_secret",
            payload,
            hashlib.sha256,
        ).hexdigest()

        event = handler.verify_and_parse(payload, signature)
        assert event.event_type == StrigaWebhookEventType.CARD_ACTIVATED

    def test_verify_and_parse_invalid_raises(self, handler):
        """Test verify_and_parse with invalid signature raises."""
        payload = b'{"type":"card.created"}'

        with pytest.raises(StrigaWebhookVerificationError):
            handler.verify_and_parse(payload, "bad_sig")

    def test_parse_unknown_event_type(self, handler):
        """Test parsing unknown event type defaults gracefully."""
        payload = json.dumps({
            "eventId": "evt_999",
            "type": "unknown.event.type",
            "data": {},
        }).encode()

        event = handler.parse_event(payload)
        # Should default to TRANSACTION_AUTHORIZATION
        assert isinstance(event, StrigaWebhookEvent)

    def test_parse_kyc_event(self, handler):
        """Test parsing KYC webhook events."""
        payload = json.dumps({
            "eventId": "evt_kyc_001",
            "type": "kyc.approved",
            "data": {"userId": "user_123"},
        }).encode()

        event = handler.parse_event(payload)
        assert event.event_type == StrigaWebhookEventType.KYC_APPROVED
        assert event.user_id == "user_123"

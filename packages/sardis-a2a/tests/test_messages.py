"""Tests for A2A message types."""

from datetime import datetime, timezone, timedelta

import pytest

from sardis_a2a.messages import (
    A2AMessageType,
    A2AMessageStatus,
    A2AMessage,
    A2APaymentRequest,
    A2APaymentResponse,
    A2ACredentialRequest,
    A2ACredentialResponse,
)


class TestA2AMessageType:
    """Tests for A2AMessageType enum."""

    def test_payment_types(self):
        """Test payment message types."""
        assert A2AMessageType.PAYMENT_REQUEST.value == "payment_request"
        assert A2AMessageType.PAYMENT_RESPONSE.value == "payment_response"

    def test_credential_types(self):
        """Test credential message types."""
        assert A2AMessageType.CREDENTIAL_REQUEST.value == "credential_request"
        assert A2AMessageType.CREDENTIAL_RESPONSE.value == "credential_response"

    def test_checkout_types(self):
        """Test checkout message types."""
        assert A2AMessageType.CHECKOUT_INITIATE.value == "checkout_initiate"
        assert A2AMessageType.CHECKOUT_COMPLETE.value == "checkout_complete"

    def test_status_types(self):
        """Test status message types."""
        assert A2AMessageType.ACK.value == "ack"
        assert A2AMessageType.ERROR.value == "error"


class TestA2AMessageStatus:
    """Tests for A2AMessageStatus enum."""

    def test_status_values(self):
        """Test message status values."""
        assert A2AMessageStatus.PENDING.value == "pending"
        assert A2AMessageStatus.RECEIVED.value == "received"
        assert A2AMessageStatus.PROCESSING.value == "processing"
        assert A2AMessageStatus.COMPLETED.value == "completed"
        assert A2AMessageStatus.FAILED.value == "failed"


class TestA2AMessage:
    """Tests for A2AMessage."""

    def test_create_message(self):
        """Test creating a message."""
        msg = A2AMessage(
            message_type=A2AMessageType.PAYMENT_REQUEST,
            sender_id="sender_123",
            recipient_id="recipient_456",
            payload={"amount": 1000},
        )

        assert msg.message_type == A2AMessageType.PAYMENT_REQUEST
        assert msg.sender_id == "sender_123"
        assert msg.recipient_id == "recipient_456"
        assert msg.payload == {"amount": 1000}
        assert msg.status == A2AMessageStatus.PENDING

    def test_default_values(self):
        """Test default message values."""
        msg = A2AMessage()

        assert msg.message_id is not None
        assert msg.message_type == A2AMessageType.ACK
        assert msg.status == A2AMessageStatus.PENDING
        assert msg.signature_algorithm == "Ed25519"
        assert isinstance(msg.timestamp, datetime)

    def test_correlation_fields(self):
        """Test correlation fields."""
        msg = A2AMessage(
            correlation_id="corr_123",
            in_reply_to="msg_456",
        )

        assert msg.correlation_id == "corr_123"
        assert msg.in_reply_to == "msg_456"

    def test_to_dict(self):
        """Test message serialization."""
        msg = A2AMessage(
            message_type=A2AMessageType.PAYMENT_REQUEST,
            sender_id="sender_123",
            recipient_id="recipient_456",
            payload={"amount": 1000, "token": "USDC"},
            signature="sig123",
        )

        data = msg.to_dict()

        assert data["message_type"] == "payment_request"
        assert data["sender_id"] == "sender_123"
        assert data["recipient_id"] == "recipient_456"
        assert data["payload"]["amount"] == 1000
        assert data["signature"] == "sig123"
        assert "timestamp" in data

    def test_to_dict_with_error(self):
        """Test serialization with error."""
        msg = A2AMessage(
            message_type=A2AMessageType.ERROR,
            status=A2AMessageStatus.FAILED,
            error="Payment failed",
            error_code="insufficient_funds",
        )

        data = msg.to_dict()

        assert data["message_type"] == "error"
        assert data["status"] == "failed"
        assert data["error"] == "Payment failed"
        assert data["error_code"] == "insufficient_funds"

    def test_from_dict(self):
        """Test message deserialization."""
        data = {
            "message_id": "msg_123",
            "message_type": "payment_request",
            "sender_id": "sender_123",
            "recipient_id": "recipient_456",
            "timestamp": "2024-01-15T10:30:00+00:00",
            "payload": {"amount": 1000},
            "status": "completed",
        }

        msg = A2AMessage.from_dict(data)

        assert msg.message_id == "msg_123"
        assert msg.message_type == A2AMessageType.PAYMENT_REQUEST
        assert msg.sender_id == "sender_123"
        assert msg.payload == {"amount": 1000}
        assert msg.status == A2AMessageStatus.COMPLETED

    def test_from_dict_with_expiration(self):
        """Test deserialization with expiration."""
        data = {
            "message_type": "payment_request",
            "expires_at": "2024-01-15T12:00:00+00:00",
        }

        msg = A2AMessage.from_dict(data)

        assert msg.expires_at is not None
        assert msg.expires_at.year == 2024

    def test_roundtrip_serialization(self):
        """Test serialization/deserialization roundtrip."""
        original = A2AMessage(
            message_type=A2AMessageType.CREDENTIAL_REQUEST,
            sender_id="agent_a",
            recipient_id="agent_b",
            correlation_id="corr_1",
            payload={"credential_type": "mandate"},
        )

        data = original.to_dict()
        restored = A2AMessage.from_dict(data)

        assert restored.message_type == original.message_type
        assert restored.sender_id == original.sender_id
        assert restored.recipient_id == original.recipient_id
        assert restored.correlation_id == original.correlation_id
        assert restored.payload == original.payload


class TestA2APaymentRequest:
    """Tests for A2APaymentRequest."""

    @pytest.fixture
    def payment_request(self):
        """Create a sample payment request."""
        return A2APaymentRequest(
            sender_agent_id="agent_sender",
            recipient_agent_id="agent_recipient",
            amount_minor=5000,  # $50.00
            currency="USD",
            token="USDC",
            chain="base",
            destination="0x1234567890abcdef1234567890abcdef12345678",
            purpose="Test payment",
            reference="order_123",
        )

    def test_create_payment_request(self, payment_request):
        """Test creating a payment request."""
        assert payment_request.sender_agent_id == "agent_sender"
        assert payment_request.recipient_agent_id == "agent_recipient"
        assert payment_request.amount_minor == 5000
        assert payment_request.token == "USDC"
        assert payment_request.chain == "base"
        assert payment_request.purpose == "Test payment"

    def test_default_values(self):
        """Test default payment request values."""
        req = A2APaymentRequest()

        assert req.request_id is not None
        assert req.currency == "USD"
        assert req.token == "USDC"
        assert req.chain == "base"

    def test_to_a2a_message(self, payment_request):
        """Test converting to A2A message."""
        msg = payment_request.to_a2a_message()

        assert msg.message_type == A2AMessageType.PAYMENT_REQUEST
        assert msg.sender_id == "agent_sender"
        assert msg.recipient_id == "agent_recipient"
        assert msg.correlation_id == payment_request.request_id
        assert msg.payload["amount_minor"] == 5000
        assert msg.payload["token"] == "USDC"
        assert msg.payload["chain"] == "base"
        assert msg.payload["destination"] == "0x1234567890abcdef1234567890abcdef12345678"
        assert msg.payload["purpose"] == "Test payment"
        assert msg.payload["reference"] == "order_123"

    def test_from_a2a_message(self, payment_request):
        """Test creating from A2A message."""
        msg = payment_request.to_a2a_message()
        restored = A2APaymentRequest.from_a2a_message(msg)

        assert restored.request_id == payment_request.request_id
        assert restored.sender_agent_id == payment_request.sender_agent_id
        assert restored.recipient_agent_id == payment_request.recipient_agent_id
        assert restored.amount_minor == payment_request.amount_minor
        assert restored.token == payment_request.token
        assert restored.chain == payment_request.chain
        assert restored.destination == payment_request.destination

    def test_with_callback_url(self):
        """Test payment request with callback URL."""
        req = A2APaymentRequest(
            amount_minor=1000,
            callback_url="https://callback.example.com/payments",
        )

        msg = req.to_a2a_message()

        assert msg.payload["callback_url"] == "https://callback.example.com/payments"

    def test_with_metadata(self):
        """Test payment request with metadata."""
        req = A2APaymentRequest(
            amount_minor=1000,
            metadata={"order_id": "123", "customer": "abc"},
        )

        msg = req.to_a2a_message()

        assert msg.payload["metadata"]["order_id"] == "123"
        assert msg.payload["metadata"]["customer"] == "abc"


class TestA2APaymentResponse:
    """Tests for A2APaymentResponse."""

    def test_create_success_response(self):
        """Test creating a successful payment response."""
        resp = A2APaymentResponse(
            request_id="req_123",
            sender_agent_id="agent_recipient",
            recipient_agent_id="agent_sender",
            success=True,
            status="confirmed",
            tx_hash="0xabcdef123456",
            chain="base",
            block_number=12345,
        )

        assert resp.success is True
        assert resp.status == "confirmed"
        assert resp.tx_hash == "0xabcdef123456"
        assert resp.block_number == 12345

    def test_create_failure_response(self):
        """Test creating a failed payment response."""
        resp = A2APaymentResponse(
            request_id="req_123",
            success=False,
            status="failed",
            error="Insufficient balance",
            error_code="insufficient_balance",
        )

        assert resp.success is False
        assert resp.status == "failed"
        assert resp.error == "Insufficient balance"
        assert resp.error_code == "insufficient_balance"

    def test_to_a2a_message_success(self):
        """Test converting successful response to message."""
        resp = A2APaymentResponse(
            request_id="req_123",
            success=True,
            status="confirmed",
            tx_hash="0xabcdef",
        )

        msg = resp.to_a2a_message()

        assert msg.message_type == A2AMessageType.PAYMENT_RESPONSE
        assert msg.in_reply_to == "req_123"
        assert msg.status == A2AMessageStatus.COMPLETED
        assert msg.payload["success"] is True
        assert msg.payload["tx_hash"] == "0xabcdef"

    def test_to_a2a_message_failure(self):
        """Test converting failed response to message."""
        resp = A2APaymentResponse(
            request_id="req_123",
            success=False,
            error="Payment rejected",
            error_code="rejected",
        )

        msg = resp.to_a2a_message()

        assert msg.message_type == A2AMessageType.PAYMENT_RESPONSE
        assert msg.status == A2AMessageStatus.FAILED
        assert msg.payload["success"] is False
        assert msg.error == "Payment rejected"


class TestA2ACredentialRequest:
    """Tests for A2ACredentialRequest."""

    def test_create_credential_request(self):
        """Test creating a credential request."""
        req = A2ACredentialRequest(
            sender_agent_id="agent_a",
            recipient_agent_id="agent_b",
            credential_type="mandate",
            credential_data={"mandate_id": "mand_123", "issuer": "sardis.sh"},
        )

        assert req.sender_agent_id == "agent_a"
        assert req.credential_type == "mandate"
        assert req.credential_data["mandate_id"] == "mand_123"
        assert req.verify_signature is True
        assert req.verify_expiration is True
        assert req.verify_chain is True

    def test_custom_verification_options(self):
        """Test custom verification options."""
        req = A2ACredentialRequest(
            credential_type="identity",
            verify_signature=True,
            verify_expiration=False,
            verify_chain=False,
        )

        assert req.verify_signature is True
        assert req.verify_expiration is False
        assert req.verify_chain is False

    def test_to_a2a_message(self):
        """Test converting to A2A message."""
        req = A2ACredentialRequest(
            sender_agent_id="agent_a",
            recipient_agent_id="agent_b",
            credential_type="mandate",
            credential_data={"mandate_id": "mand_123"},
        )

        msg = req.to_a2a_message()

        assert msg.message_type == A2AMessageType.CREDENTIAL_REQUEST
        assert msg.sender_id == "agent_a"
        assert msg.recipient_id == "agent_b"
        assert msg.correlation_id == req.request_id
        assert msg.payload["credential_type"] == "mandate"
        assert msg.payload["verify_signature"] is True


class TestA2ACredentialResponse:
    """Tests for A2ACredentialResponse."""

    def test_create_valid_response(self):
        """Test creating a valid credential response."""
        resp = A2ACredentialResponse(
            request_id="req_123",
            sender_agent_id="agent_b",
            recipient_agent_id="agent_a",
            valid=True,
            signature_valid=True,
            not_expired=True,
            chain_valid=True,
            verification_details={"verified_fields": ["issuer", "subject"]},
        )

        assert resp.valid is True
        assert resp.signature_valid is True
        assert resp.not_expired is True
        assert resp.chain_valid is True

    def test_create_invalid_response(self):
        """Test creating an invalid credential response."""
        resp = A2ACredentialResponse(
            request_id="req_123",
            valid=False,
            signature_valid=False,
            error="Invalid signature",
            error_code="invalid_signature",
        )

        assert resp.valid is False
        assert resp.signature_valid is False
        assert resp.error == "Invalid signature"

    def test_to_a2a_message_valid(self):
        """Test converting valid response to message."""
        resp = A2ACredentialResponse(
            request_id="req_123",
            valid=True,
            signature_valid=True,
            not_expired=True,
        )

        msg = resp.to_a2a_message()

        assert msg.message_type == A2AMessageType.CREDENTIAL_RESPONSE
        assert msg.in_reply_to == "req_123"
        assert msg.status == A2AMessageStatus.COMPLETED
        assert msg.payload["valid"] is True

    def test_to_a2a_message_invalid(self):
        """Test converting invalid response to message."""
        resp = A2ACredentialResponse(
            request_id="req_123",
            valid=False,
            error="Mandate expired",
        )

        msg = resp.to_a2a_message()

        assert msg.message_type == A2AMessageType.CREDENTIAL_RESPONSE
        assert msg.status == A2AMessageStatus.FAILED
        assert msg.payload["valid"] is False

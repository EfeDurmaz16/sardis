"""A2A message types for inter-agent communication.

Defines structured message formats for:
- Payment requests/responses
- Credential verification
- Checkout flows
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class A2AMessageType(str, Enum):
    """Types of A2A messages."""

    # Payment messages
    PAYMENT_REQUEST = "payment_request"
    PAYMENT_RESPONSE = "payment_response"

    # Credential messages
    CREDENTIAL_REQUEST = "credential_request"
    CREDENTIAL_RESPONSE = "credential_response"

    # Checkout messages (UCP)
    CHECKOUT_INITIATE = "checkout_initiate"
    CHECKOUT_COMPLETE = "checkout_complete"

    # Status/Error
    ACK = "ack"
    ERROR = "error"


class A2AMessageStatus(str, Enum):
    """Status of an A2A message."""

    PENDING = "pending"
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass(slots=True)
class A2AMessage:
    """
    Base A2A message structure.

    All A2A messages follow this structure with type-specific payloads.
    """

    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    message_type: A2AMessageType = A2AMessageType.ACK
    sender_id: str = ""
    recipient_id: str = ""

    # Timing
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Request correlation
    correlation_id: Optional[str] = None  # Links request/response pairs
    in_reply_to: Optional[str] = None  # Message this is responding to

    # Payload
    payload: Dict[str, Any] = field(default_factory=dict)

    # Signature
    signature: Optional[str] = None
    signature_algorithm: str = "Ed25519"

    # Status
    status: A2AMessageStatus = A2AMessageStatus.PENDING

    # Error (if failed)
    error: Optional[str] = None
    error_code: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "message_type": self.message_type.value,
            "sender_id": self.sender_id,
            "recipient_id": self.recipient_id,
            "timestamp": self.timestamp.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "correlation_id": self.correlation_id,
            "in_reply_to": self.in_reply_to,
            "payload": self.payload,
            "signature": self.signature,
            "signature_algorithm": self.signature_algorithm,
            "status": self.status.value,
            "error": self.error,
            "error_code": self.error_code,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "A2AMessage":
        """Create from dictionary."""
        return cls(
            message_id=data.get("message_id", str(uuid.uuid4())),
            message_type=A2AMessageType(data.get("message_type", "ack")),
            sender_id=data.get("sender_id", ""),
            recipient_id=data.get("recipient_id", ""),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(timezone.utc),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            correlation_id=data.get("correlation_id"),
            in_reply_to=data.get("in_reply_to"),
            payload=data.get("payload", {}),
            signature=data.get("signature"),
            signature_algorithm=data.get("signature_algorithm", "Ed25519"),
            status=A2AMessageStatus(data.get("status", "pending")),
            error=data.get("error"),
            error_code=data.get("error_code"),
        )


# ============ Payment Messages ============


@dataclass(slots=True)
class A2APaymentRequest:
    """
    Request to execute a payment.

    Sent from one agent to another to request payment execution.
    """

    # Request metadata
    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_agent_id: str = ""
    recipient_agent_id: str = ""

    # Payment details
    amount_minor: int = 0
    currency: str = "USD"
    token: str = "USDC"
    chain: str = "base"
    destination: str = ""

    # Purpose/context
    purpose: str = ""
    reference: Optional[str] = None  # External reference (invoice, order ID, etc.)
    memo: Optional[str] = None

    # Mandate information
    mandate_id: Optional[str] = None
    audit_hash: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    # Callback
    callback_url: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_a2a_message(self) -> A2AMessage:
        """Convert to A2A message format."""
        return A2AMessage(
            message_type=A2AMessageType.PAYMENT_REQUEST,
            sender_id=self.sender_agent_id,
            recipient_id=self.recipient_agent_id,
            correlation_id=self.request_id,
            payload={
                "request_id": self.request_id,
                "amount_minor": self.amount_minor,
                "currency": self.currency,
                "token": self.token,
                "chain": self.chain,
                "destination": self.destination,
                "purpose": self.purpose,
                "reference": self.reference,
                "memo": self.memo,
                "mandate_id": self.mandate_id,
                "audit_hash": self.audit_hash,
                "callback_url": self.callback_url,
                "metadata": self.metadata,
            },
            expires_at=self.expires_at,
        )

    @classmethod
    def from_a2a_message(cls, message: A2AMessage) -> "A2APaymentRequest":
        """Create from A2A message."""
        payload = message.payload
        return cls(
            request_id=payload.get("request_id", message.correlation_id or str(uuid.uuid4())),
            sender_agent_id=message.sender_id,
            recipient_agent_id=message.recipient_id,
            amount_minor=payload.get("amount_minor", 0),
            currency=payload.get("currency", "USD"),
            token=payload.get("token", "USDC"),
            chain=payload.get("chain", "base"),
            destination=payload.get("destination", ""),
            purpose=payload.get("purpose", ""),
            reference=payload.get("reference"),
            memo=payload.get("memo"),
            mandate_id=payload.get("mandate_id"),
            audit_hash=payload.get("audit_hash"),
            created_at=message.timestamp,
            expires_at=message.expires_at,
            callback_url=payload.get("callback_url"),
            metadata=payload.get("metadata", {}),
        )


@dataclass(slots=True)
class A2APaymentResponse:
    """
    Response to a payment request.

    Sent after payment execution (success or failure).
    """

    # Response metadata
    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""  # ID of the original request
    sender_agent_id: str = ""
    recipient_agent_id: str = ""

    # Result
    success: bool = False
    status: str = "pending"  # pending, submitted, confirmed, failed

    # Transaction details (if successful)
    tx_hash: Optional[str] = None
    chain: Optional[str] = None
    block_number: Optional[int] = None

    # Error details (if failed)
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_a2a_message(self) -> A2AMessage:
        """Convert to A2A message format."""
        return A2AMessage(
            message_type=A2AMessageType.PAYMENT_RESPONSE,
            sender_id=self.sender_agent_id,
            recipient_id=self.recipient_agent_id,
            correlation_id=self.response_id,
            in_reply_to=self.request_id,
            payload={
                "response_id": self.response_id,
                "request_id": self.request_id,
                "success": self.success,
                "status": self.status,
                "tx_hash": self.tx_hash,
                "chain": self.chain,
                "block_number": self.block_number,
                "error": self.error,
                "error_code": self.error_code,
                "metadata": self.metadata,
            },
            status=A2AMessageStatus.COMPLETED if self.success else A2AMessageStatus.FAILED,
            error=self.error,
            error_code=self.error_code,
        )


# ============ Credential Messages ============


@dataclass(slots=True)
class A2ACredentialRequest:
    """
    Request to verify credentials or mandates.

    Sent to request verification of a credential chain or mandate.
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender_agent_id: str = ""
    recipient_agent_id: str = ""

    # Credential to verify
    credential_type: str = "mandate"  # mandate, identity, authorization
    credential_data: Dict[str, Any] = field(default_factory=dict)

    # What to verify
    verify_signature: bool = True
    verify_expiration: bool = True
    verify_chain: bool = True  # For mandate chains

    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_a2a_message(self) -> A2AMessage:
        """Convert to A2A message format."""
        return A2AMessage(
            message_type=A2AMessageType.CREDENTIAL_REQUEST,
            sender_id=self.sender_agent_id,
            recipient_id=self.recipient_agent_id,
            correlation_id=self.request_id,
            payload={
                "request_id": self.request_id,
                "credential_type": self.credential_type,
                "credential_data": self.credential_data,
                "verify_signature": self.verify_signature,
                "verify_expiration": self.verify_expiration,
                "verify_chain": self.verify_chain,
            },
        )


@dataclass(slots=True)
class A2ACredentialResponse:
    """
    Response to a credential verification request.
    """

    response_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    request_id: str = ""
    sender_agent_id: str = ""
    recipient_agent_id: str = ""

    # Verification result
    valid: bool = False
    verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Verification details
    signature_valid: Optional[bool] = None
    not_expired: Optional[bool] = None
    chain_valid: Optional[bool] = None

    # Error (if failed)
    error: Optional[str] = None
    error_code: Optional[str] = None

    # Additional info from verification
    verification_details: Dict[str, Any] = field(default_factory=dict)

    def to_a2a_message(self) -> A2AMessage:
        """Convert to A2A message format."""
        return A2AMessage(
            message_type=A2AMessageType.CREDENTIAL_RESPONSE,
            sender_id=self.sender_agent_id,
            recipient_id=self.recipient_agent_id,
            correlation_id=self.response_id,
            in_reply_to=self.request_id,
            payload={
                "response_id": self.response_id,
                "request_id": self.request_id,
                "valid": self.valid,
                "verified_at": self.verified_at.isoformat(),
                "signature_valid": self.signature_valid,
                "not_expired": self.not_expired,
                "chain_valid": self.chain_valid,
                "error": self.error,
                "error_code": self.error_code,
                "verification_details": self.verification_details,
            },
            status=A2AMessageStatus.COMPLETED if self.valid else A2AMessageStatus.FAILED,
        )


__all__ = [
    "A2AMessageType",
    "A2AMessageStatus",
    "A2AMessage",
    "A2APaymentRequest",
    "A2APaymentResponse",
    "A2ACredentialRequest",
    "A2ACredentialResponse",
]

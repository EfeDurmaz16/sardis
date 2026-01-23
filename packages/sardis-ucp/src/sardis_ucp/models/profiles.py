"""UCP Profile models for businesses and platforms.

Profiles declare capabilities and endpoints for UCP participants.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional


class UCPCapabilityType(str, Enum):
    """Types of UCP capabilities."""

    # Checkout capabilities
    CHECKOUT_CREATE = "checkout.create"
    CHECKOUT_UPDATE = "checkout.update"
    CHECKOUT_COMPLETE = "checkout.complete"

    # Order capabilities
    ORDER_CREATE = "order.create"
    ORDER_GET = "order.get"
    ORDER_CANCEL = "order.cancel"

    # Fulfillment capabilities
    FULFILLMENT_SHIP = "fulfillment.ship"
    FULFILLMENT_TRACK = "fulfillment.track"
    FULFILLMENT_RETURN = "fulfillment.return"

    # Payment capabilities
    PAYMENT_EXECUTE = "payment.execute"
    PAYMENT_VERIFY = "payment.verify"
    PAYMENT_REFUND = "payment.refund"


@dataclass(slots=True)
class UCPCapability:
    """A capability that a UCP participant supports."""

    capability_type: UCPCapabilityType
    version: str = "1.0"
    enabled: bool = True
    endpoint: Optional[str] = None  # Override endpoint for this capability
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "capability_type": self.capability_type.value,
            "version": self.version,
            "enabled": self.enabled,
            "endpoint": self.endpoint,
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPPaymentCapability:
    """Payment-specific capability declaration."""

    # Supported payment methods
    supported_tokens: List[str] = field(default_factory=lambda: ["USDC", "USDT"])
    supported_chains: List[str] = field(default_factory=lambda: ["base", "polygon"])

    # Limits
    min_amount_minor: int = 100  # $1.00
    max_amount_minor: int = 100_000_00  # $100,000.00

    # Protocol support
    ap2_compliant: bool = True
    x402_compliant: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "supported_tokens": self.supported_tokens,
            "supported_chains": self.supported_chains,
            "min_amount_minor": self.min_amount_minor,
            "max_amount_minor": self.max_amount_minor,
            "ap2_compliant": self.ap2_compliant,
            "x402_compliant": self.x402_compliant,
        }


@dataclass(slots=True)
class UCPEndpoints:
    """Service endpoints for a UCP participant."""

    # REST API
    rest_base_url: Optional[str] = None

    # MCP server
    mcp_command: Optional[str] = None
    mcp_args: List[str] = field(default_factory=list)

    # A2A agent card
    agent_card_url: Optional[str] = None

    # Webhooks
    webhook_url: Optional[str] = None
    webhook_secret: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "rest_base_url": self.rest_base_url,
            "mcp_command": self.mcp_command,
            "mcp_args": self.mcp_args,
            "agent_card_url": self.agent_card_url,
            "webhook_url": self.webhook_url,
        }


@dataclass(slots=True)
class UCPBusinessProfile:
    """Profile for a business accepting payments via UCP.

    Represents merchants who sell goods/services and accept payments.
    """

    profile_id: str
    business_name: str
    business_domain: str

    # Contact information
    support_email: Optional[str] = None
    support_url: Optional[str] = None

    # Capabilities
    capabilities: List[UCPCapability] = field(default_factory=list)
    payment_capability: UCPPaymentCapability = field(default_factory=UCPPaymentCapability)

    # Service endpoints
    endpoints: UCPEndpoints = field(default_factory=UCPEndpoints)

    # Verification
    verified: bool = False
    verified_at: Optional[datetime] = None
    verification_method: Optional[str] = None

    # Signing keys for mandate verification
    signing_key_id: Optional[str] = None
    public_key: Optional[str] = None
    key_algorithm: str = "Ed25519"

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports_capability(self, capability_type: UCPCapabilityType) -> bool:
        """Check if this business supports a specific capability."""
        return any(
            c.capability_type == capability_type and c.enabled
            for c in self.capabilities
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "profile_type": "business",
            "business_name": self.business_name,
            "business_domain": self.business_domain,
            "support_email": self.support_email,
            "support_url": self.support_url,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "payment_capability": self.payment_capability.to_dict(),
            "endpoints": self.endpoints.to_dict(),
            "verified": self.verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "signing_key_id": self.signing_key_id,
            "public_key": self.public_key,
            "key_algorithm": self.key_algorithm,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass(slots=True)
class UCPPlatformProfile:
    """Profile for a platform making payments via UCP.

    Represents AI agents or platforms that initiate payments on behalf of users.
    """

    profile_id: str
    platform_name: str
    platform_domain: str

    # Contact information
    support_email: Optional[str] = None

    # Capabilities
    capabilities: List[UCPCapability] = field(default_factory=list)
    payment_capability: UCPPaymentCapability = field(default_factory=UCPPaymentCapability)

    # Service endpoints
    endpoints: UCPEndpoints = field(default_factory=UCPEndpoints)

    # Verification
    verified: bool = False
    verified_at: Optional[datetime] = None

    # Signing keys for mandate verification
    signing_key_id: Optional[str] = None
    public_key: Optional[str] = None
    key_algorithm: str = "Ed25519"

    # Agent configuration (for AI agents)
    is_agent: bool = False
    agent_owner: Optional[str] = None  # Owner/operator of the agent

    # Rate limits
    rate_limit_per_minute: int = 60
    rate_limit_per_day: int = 10000

    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

    def supports_capability(self, capability_type: UCPCapabilityType) -> bool:
        """Check if this platform supports a specific capability."""
        return any(
            c.capability_type == capability_type and c.enabled
            for c in self.capabilities
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "profile_id": self.profile_id,
            "profile_type": "platform",
            "platform_name": self.platform_name,
            "platform_domain": self.platform_domain,
            "support_email": self.support_email,
            "capabilities": [c.to_dict() for c in self.capabilities],
            "payment_capability": self.payment_capability.to_dict(),
            "endpoints": self.endpoints.to_dict(),
            "verified": self.verified,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None,
            "signing_key_id": self.signing_key_id,
            "public_key": self.public_key,
            "key_algorithm": self.key_algorithm,
            "is_agent": self.is_agent,
            "agent_owner": self.agent_owner,
            "rate_limit_per_minute": self.rate_limit_per_minute,
            "rate_limit_per_day": self.rate_limit_per_day,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


__all__ = [
    "UCPCapabilityType",
    "UCPCapability",
    "UCPPaymentCapability",
    "UCPEndpoints",
    "UCPBusinessProfile",
    "UCPPlatformProfile",
]

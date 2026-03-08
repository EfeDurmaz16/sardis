"""Delegated payment credential model for tokenized card execution.

Sardis never stores raw PANs. Credentials are opaque network tokens
(Stripe SPT, Visa TAP, Mastercard Agent Pay) with encrypted payloads
and bound scopes.  Every credential requires a consent reference.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional


class CredentialNetwork(str, Enum):
    """Supported delegated credential networks."""
    STRIPE_SPT = "stripe_spt"
    VISA_TAP = "visa_tap"
    MASTERCARD_AGENT_PAY = "mastercard_agent_pay"


class CredentialStatus(str, Enum):
    """Lifecycle status of a delegated credential."""
    PROVISIONING = "provisioning"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    REVOKED = "revoked"
    EXPIRED = "expired"


class CredentialClass(str, Enum):
    """Sensitivity / ownership classification with handling matrix.

    ┌──────────────────────────────┬────────┬──────────┬──────────┬────────────┬────────┬──────────┬───────────┬────────────────┐
    │ Class                        │Encrypt │Envelope  │Rotatable │Exportable  │In logs │In admin  │Cacheable  │Decryptable by  │
    ├──────────────────────────────┼────────┼──────────┼──────────┼────────────┼────────┼──────────┼───────────┼────────────────┤
    │ REFERENCE_ONLY               │  No    │  No      │  N/A     │  Yes       │ Yes    │ Yes      │ Yes       │ Anyone         │
    │ OPAQUE_DELEGATED_TOKEN       │  Yes   │  No      │  Yes     │  No        │ Masked │ Masked   │ TTL only  │ Service only   │
    │ REHYDRATABLE_EXECUTION_TOKEN │  Yes   │  Yes     │  Yes     │  No        │ Never  │ Never    │ No        │ Executor only  │
    │ SENSITIVE_PAYMENT_SECRET     │  Yes   │  Yes+HSM │  Yes     │  No        │ Never  │ Never    │ No        │ HSM only       │
    └──────────────────────────────┴────────┴──────────┴──────────┴────────────┴────────┴──────────┴───────────┴────────────────┘
    """
    REFERENCE_ONLY = "reference_only"
    OPAQUE_DELEGATED_TOKEN = "opaque_delegated_token"
    REHYDRATABLE_EXECUTION_TOKEN = "rehydratable_execution_token"
    SENSITIVE_PAYMENT_SECRET = "sensitive_payment_secret"


# Handling matrix — looked up by CredentialClass
CREDENTIAL_HANDLING: dict[CredentialClass, dict[str, Any]] = {
    CredentialClass.REFERENCE_ONLY: {
        "encrypt_at_rest": False,
        "envelope_encrypt": False,
        "rotatable": False,
        "exportable": True,
        "in_logs": True,
        "in_admin_api": True,
        "cacheable": True,
        "decryptable_by": "anyone",
    },
    CredentialClass.OPAQUE_DELEGATED_TOKEN: {
        "encrypt_at_rest": True,
        "envelope_encrypt": False,
        "rotatable": True,
        "exportable": False,
        "in_logs": "masked",
        "in_admin_api": "masked",
        "cacheable": "ttl_only",
        "decryptable_by": "service",
    },
    CredentialClass.REHYDRATABLE_EXECUTION_TOKEN: {
        "encrypt_at_rest": True,
        "envelope_encrypt": True,
        "rotatable": True,
        "exportable": False,
        "in_logs": False,
        "in_admin_api": False,
        "cacheable": False,
        "decryptable_by": "executor",
    },
    CredentialClass.SENSITIVE_PAYMENT_SECRET: {
        "encrypt_at_rest": True,
        "envelope_encrypt": True,  # + HSM in production
        "rotatable": True,
        "exportable": False,
        "in_logs": False,
        "in_admin_api": False,
        "cacheable": False,
        "decryptable_by": "hsm",
    },
}


@dataclass
class CredentialScope:
    """Policy constraints bound to a credential."""
    max_per_tx: Decimal = Decimal("500")
    daily_limit: Decimal = Decimal("2000")
    allowed_mccs: list[str] = field(default_factory=list)
    allowed_merchant_ids: list[str] = field(default_factory=list)
    expires_at: Optional[datetime] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "max_per_tx": str(self.max_per_tx),
            "daily_limit": str(self.daily_limit),
            "allowed_mccs": self.allowed_mccs,
            "allowed_merchant_ids": self.allowed_merchant_ids,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CredentialScope:
        return cls(
            max_per_tx=Decimal(str(data.get("max_per_tx", "500"))),
            daily_limit=Decimal(str(data.get("daily_limit", "2000"))),
            allowed_mccs=data.get("allowed_mccs", []),
            allowed_merchant_ids=data.get("allowed_merchant_ids", []),
            expires_at=(
                datetime.fromisoformat(data["expires_at"])
                if data.get("expires_at")
                else None
            ),
        )

    def is_tighter_than(self, other: CredentialScope) -> bool:
        """Return True if self is strictly tighter than (or equal to) other."""
        if self.max_per_tx > other.max_per_tx:
            return False
        if self.daily_limit > other.daily_limit:
            return False
        # Allowed lists: tighter means subset or identical
        if self.allowed_mccs and other.allowed_mccs:
            if not set(self.allowed_mccs).issubset(set(other.allowed_mccs)):
                return False
        if self.allowed_merchant_ids and other.allowed_merchant_ids:
            if not set(self.allowed_merchant_ids).issubset(set(other.allowed_merchant_ids)):
                return False
        return True


@dataclass(slots=True)
class DelegatedCredential:
    """Tokenized delegated payment credential.

    Sardis never stores raw PANs — only opaque network tokens with
    encrypted payloads.  Each credential is bound to a consent record.
    """
    credential_id: str = field(
        default_factory=lambda: f"dcred_{uuid.uuid4().hex[:16]}"
    )
    org_id: str = ""
    agent_id: str = ""
    network: CredentialNetwork = CredentialNetwork.STRIPE_SPT
    status: CredentialStatus = CredentialStatus.PROVISIONING
    credential_class: CredentialClass = CredentialClass.OPAQUE_DELEGATED_TOKEN

    # Token material
    token_reference: str = ""  # opaque network token ID (non-secret identifier)
    token_encrypted: bytes = b""  # Fernet-encrypted token payload

    # Constraints
    scope: CredentialScope = field(default_factory=CredentialScope)

    # Network-specific metadata
    provider_metadata: dict[str, Any] = field(default_factory=dict)

    # Consent linkage — REQUIRED (DB enforces NOT NULL)
    consent_id: str = ""

    # Timestamps
    last_used_at: Optional[datetime] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = None

    @property
    def is_valid(self) -> bool:
        """Status + expiry check."""
        if self.status != CredentialStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) >= self.expires_at:
            return False
        return True

    def can_execute(
        self,
        amount: Decimal,
        merchant_id: Optional[str] = None,
        mcc_code: Optional[str] = None,
    ) -> tuple[bool, str]:
        """Local scope check — mirrors VirtualCard.can_authorize()."""
        if not self.is_valid:
            return False, f"credential invalid ({self.status.value})"

        if amount > self.scope.max_per_tx:
            return False, (
                f"amount {amount} exceeds per-tx limit {self.scope.max_per_tx}"
            )

        if (
            self.scope.allowed_merchant_ids
            and merchant_id
            and merchant_id not in self.scope.allowed_merchant_ids
        ):
            return False, f"merchant {merchant_id} not in allowed list"

        if (
            self.scope.allowed_mccs
            and mcc_code
            and mcc_code not in self.scope.allowed_mccs
        ):
            return False, f"MCC {mcc_code} not in allowed list"

        if self.scope.expires_at and datetime.now(timezone.utc) >= self.scope.expires_at:
            return False, "credential scope expired"

        return True, "OK"

    def handling(self) -> dict[str, Any]:
        """Return the handling matrix entry for this credential's class."""
        return CREDENTIAL_HANDLING[self.credential_class]

    def mask_token_reference(self) -> str:
        """Masked form of token_reference for logs/admin API."""
        h = self.handling()
        if h["in_logs"] is True:
            return self.token_reference
        if h["in_logs"] == "masked":
            if len(self.token_reference) > 8:
                return self.token_reference[:4] + "..." + self.token_reference[-4:]
            return "****"
        return "[REDACTED]"

    def to_dict(self, include_sensitive: bool = False) -> dict[str, Any]:
        """Serialise for API responses.  Sensitive fields omitted by default."""
        h = self.handling()
        result: dict[str, Any] = {
            "credential_id": self.credential_id,
            "org_id": self.org_id,
            "agent_id": self.agent_id,
            "network": self.network.value,
            "status": self.status.value,
            "credential_class": self.credential_class.value,
            "token_reference": self.mask_token_reference(),
            "scope": self.scope.to_dict(),
            "consent_id": self.consent_id,
            "last_used_at": (
                self.last_used_at.isoformat() if self.last_used_at else None
            ),
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }
        if include_sensitive and h.get("exportable"):
            result["provider_metadata"] = self.provider_metadata
        return result

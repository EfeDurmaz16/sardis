"""Provider-neutral delegated payment executor.

Abstraction-first: internal contract is provider-neutral, each adapter
translates to/from its provider's actual API shape.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Protocol, runtime_checkable

from .delegated_credential import (
    CredentialNetwork,
    CredentialScope,
    DelegatedCredential,
)

# ---------------------------------------------------------------------------
# Provider-neutral internal contract
# ---------------------------------------------------------------------------

@dataclass
class DelegatedPaymentRequest:
    """Provider-neutral payment request."""

    credential_reference: str = ""  # opaque credential ref
    consent_reference: str = ""     # consent proof
    merchant_binding: str = ""      # merchant identity/domain
    usage_scope: CredentialScope = field(default_factory=CredentialScope)
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    idempotency_key: str = field(
        default_factory=lambda: f"dpay_{uuid.uuid4().hex[:16]}"
    )
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegatedPaymentResult:
    """Provider-neutral payment result."""

    success: bool = False
    network: str = ""
    reference_id: str = ""
    amount: Decimal = Decimal("0")
    currency: str = ""
    fee: Decimal = Decimal("0")
    settlement_status: str = "pending"  # instant, pending, failed
    authorization_id: str = ""
    raw_response: dict[str, Any] = field(default_factory=dict)
    error: str = ""


# ---------------------------------------------------------------------------
# Provider port (translation boundary)
# ---------------------------------------------------------------------------

@runtime_checkable
class DelegatedExecutorPort(Protocol):
    """Each adapter translates from neutral contract to provider API."""

    @property
    def network(self) -> CredentialNetwork: ...

    async def execute(
        self,
        request: DelegatedPaymentRequest,
        credential: DelegatedCredential,
    ) -> DelegatedPaymentResult: ...

    async def check_health(self) -> bool: ...

    async def estimate_fee(
        self, amount: Decimal, currency: str,
    ) -> Decimal: ...

"""Stripe SPT (Secure Payment Token) adapter.

Translation boundary: converts provider-neutral DelegatedPaymentRequest
to whatever Stripe's actual SPT API shape turns out to be.

Currently uses MockStripeSPTAdapter for dev/test.  Swap to real adapter
when Stripe partnership provides actual API access.
"""
from __future__ import annotations

import logging
import uuid
from decimal import Decimal
from typing import Any, Optional

from ..credential_store import CredentialEncryption
from ..delegated_credential import (
    CredentialClass,
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from ..delegated_executor import (
    DelegatedPaymentRequest,
    DelegatedPaymentResult,
)

logger = logging.getLogger(__name__)


class StripeSPTAdapter:
    """Real Stripe SPT adapter (placeholder until API access confirmed)."""

    def __init__(
        self,
        api_key: str = "",
        encryption: Optional[CredentialEncryption] = None,
    ) -> None:
        self._api_key = api_key
        self._encryption = encryption or CredentialEncryption()

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.STRIPE_SPT

    async def execute(
        self,
        request: DelegatedPaymentRequest,
        credential: DelegatedCredential,
    ) -> DelegatedPaymentResult:
        # Decrypt credential token payload
        try:
            token_bytes = self._encryption.decrypt_for_class(
                credential.token_encrypted, credential.credential_class,
            )
        except Exception as e:
            return DelegatedPaymentResult(
                success=False,
                network=self.network.value,
                error=f"Credential decryption failed: {e}",
            )

        # Translate to Stripe-specific request
        stripe_payload = self._translate_to_stripe(request, token_bytes)

        # TODO: Call actual Stripe SPT API when partnership provides access
        # response = await self._http_client.post(...)
        raise NotImplementedError(
            "Real Stripe SPT API not yet available. Use MockStripeSPTAdapter."
        )

    async def check_health(self) -> bool:
        return bool(self._api_key)

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        return amount * Decimal("0.025")  # 2.5%

    def _translate_to_stripe(
        self, request: DelegatedPaymentRequest, token: bytes,
    ) -> dict[str, Any]:
        """Translate neutral contract to Stripe-specific request format."""
        return {
            "amount": int(request.amount * 100),  # cents
            "currency": request.currency.lower(),
            "payment_method": token.decode("utf-8", errors="replace"),
            "merchant": request.merchant_binding,
            "idempotency_key": request.idempotency_key,
            "metadata": request.metadata,
        }

    @staticmethod
    def _translate_from_stripe(response: dict[str, Any]) -> DelegatedPaymentResult:
        """Translate Stripe response back to neutral result."""
        return DelegatedPaymentResult(
            success=response.get("status") == "succeeded",
            network="stripe_spt",
            reference_id=response.get("id", ""),
            amount=Decimal(str(response.get("amount", 0))) / 100,
            currency=response.get("currency", "").upper(),
            fee=Decimal(str(response.get("fee", 0))) / 100,
            settlement_status=(
                "instant" if response.get("status") == "succeeded" else "pending"
            ),
            authorization_id=response.get("authorization_id", ""),
            raw_response=response,
        )


class MockStripeSPTAdapter:
    """Simulated Stripe SPT adapter for dev/test.

    Follows the SimulatedMPCSigner pattern from sardis-wallet.
    """

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.STRIPE_SPT

    async def execute(
        self,
        request: DelegatedPaymentRequest,
        credential: DelegatedCredential,
    ) -> DelegatedPaymentResult:
        if credential.status != CredentialStatus.ACTIVE:
            return DelegatedPaymentResult(
                success=False,
                network=self.network.value,
                error=f"Credential not active: {credential.status.value}",
            )

        if self._should_fail:
            return DelegatedPaymentResult(
                success=False,
                network=self.network.value,
                reference_id=f"mock_fail_{uuid.uuid4().hex[:8]}",
                error="Mock failure (configured)",
            )

        ref_id = f"pi_mock_{uuid.uuid4().hex[:12]}"
        fee = request.amount * Decimal("0.025")

        return DelegatedPaymentResult(
            success=True,
            network=self.network.value,
            reference_id=ref_id,
            amount=request.amount,
            currency=request.currency,
            fee=fee,
            settlement_status="pending",
            authorization_id=f"auth_mock_{uuid.uuid4().hex[:8]}",
            raw_response={
                "id": ref_id,
                "status": "succeeded",
                "amount": int(request.amount * 100),
                "currency": request.currency.lower(),
            },
        )

    async def check_health(self) -> bool:
        return True

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        return amount * Decimal("0.025")

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: Optional[CredentialEncryption] = None,
        customer_id: Optional[str] = None,
    ) -> DelegatedCredential:
        """Create a mock credential for testing."""
        token = f"spt_mock_{uuid.uuid4().hex[:12]}".encode()
        encrypted = b"mock_encrypted"
        if encryption:
            encrypted = encryption.encrypt_for_class(
                token, CredentialClass.OPAQUE_DELEGATED_TOKEN,
            )
        return DelegatedCredential(
            org_id=org_id,
            agent_id=agent_id,
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.OPAQUE_DELEGATED_TOKEN,
            token_reference=f"tok_ref_mock_{uuid.uuid4().hex[:8]}",
            token_encrypted=encrypted,
            scope=scope,
            provider_metadata={
                "customer_id": customer_id,
                "mock": True,
            },
        )

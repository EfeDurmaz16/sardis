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
from typing import Any

import httpx

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
    """Real Stripe SPT adapter backed by the Stripe payment_intents API."""

    def __init__(
        self,
        api_key: str = "",
        partner_id: str = "",
        encryption: CredentialEncryption | None = None,
        base_url: str = "https://api.stripe.com",
    ) -> None:
        self._api_key = api_key
        self._partner_id = partner_id
        self._encryption = encryption or CredentialEncryption()
        self._base_url = base_url.rstrip("/")

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.STRIPE_SPT

    def _auth_headers(self) -> dict[str, str]:
        headers = {"Authorization": f"Bearer {self._api_key}"}
        if self._partner_id:
            headers["Stripe-Account"] = self._partner_id
        return headers

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

        payload = self._translate_to_stripe(request, token_bytes)

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/v1/payment_intents",
                    data=payload,
                    headers={
                        **self._auth_headers(),
                        "Idempotency-Key": request.idempotency_key,
                    },
                )
        except httpx.HTTPError as e:
            logger.error("Stripe SPT HTTP error during execute: %s", e)
            return DelegatedPaymentResult(
                success=False,
                network=self.network.value,
                error=f"HTTP error: {e}",
            )

        try:
            body = response.json()
        except Exception:
            body = {}

        if response.is_error:
            error_msg = body.get("error", {}).get("message", response.text)
            logger.warning(
                "Stripe SPT API error status=%s message=%s", response.status_code, error_msg,
            )
            return DelegatedPaymentResult(
                success=False,
                network=self.network.value,
                error=f"Stripe API error ({response.status_code}): {error_msg}",
                raw_response=body,
            )

        return self._translate_from_stripe(body)

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: CredentialEncryption | None = None,
        customer_id: str | None = None,
    ) -> DelegatedCredential:
        """Provision a real Stripe SPT credential via the payment methods API."""
        enc = encryption or self._encryption

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self._base_url}/v1/payment_methods",
                    data={
                        "type": "card",
                        **({"customer": customer_id} if customer_id else {}),
                    },
                    headers=self._auth_headers(),
                )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Stripe SPT provision HTTP error: {e}") from e

        body = response.json()
        if response.is_error:
            error_msg = body.get("error", {}).get("message", response.text)
            raise RuntimeError(f"Stripe SPT provision failed: {error_msg}")

        pm_id: str = body.get("id", f"pm_stub_{uuid.uuid4().hex[:12]}")
        token = pm_id.encode()
        encrypted = enc.encrypt_for_class(token, CredentialClass.OPAQUE_DELEGATED_TOKEN)

        return DelegatedCredential(
            org_id=org_id,
            agent_id=agent_id,
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.OPAQUE_DELEGATED_TOKEN,
            token_reference=f"tok_ref_{pm_id}",
            token_encrypted=encrypted,
            scope=scope,
            provider_metadata={
                "payment_method_id": pm_id,
                "customer_id": customer_id,
            },
        )

    async def check_health(self) -> bool:
        if not self._api_key:
            return False
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._base_url}/v1/payment_intents",
                    params={"limit": 1},
                    headers=self._auth_headers(),
                )
            return not response.is_error
        except httpx.HTTPError:
            return False

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
        encryption: CredentialEncryption | None = None,
        customer_id: str | None = None,
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

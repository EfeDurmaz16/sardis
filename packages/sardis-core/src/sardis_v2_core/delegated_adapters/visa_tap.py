"""Visa TAP (Token Authentication Protocol) adapter.

Translation boundary: converts provider-neutral DelegatedPaymentRequest
to Visa Token Service API shape (DPAN + cryptogram).

Real adapter requires a Visa partnership: TRID (Token Requestor ID) and
an mTLS certificate issued by Visa.  Use MockVisaTAPAdapter for dev/test.
Swap to VisaTAPAdapter when the partnership is in place.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import uuid
from decimal import Decimal
from typing import Any

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


# ---------------------------------------------------------------------------
# Signature verification (also used by the webhook router)
# ---------------------------------------------------------------------------


def verify_visa_tap_signature(payload: bytes, signature: str, webhook_secret: str) -> bool:
    """Verify a Visa TAP webhook HMAC-SHA256 signature.

    Visa sends the signature as a plain hex-encoded HMAC-SHA256 of the raw
    request body in the ``X-Visa-Signature`` header.

    Args:
        payload: Raw request body bytes.
        signature: Value from X-Visa-Signature header.
        webhook_secret: VISA_TAP_WEBHOOK_SECRET from environment.

    Returns:
        True if signature is valid, False otherwise.
    """
    try:
        computed = hmac.new(
            webhook_secret.encode("utf-8"),
            payload,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature.strip())
    except Exception as e:
        logger.error("Visa TAP signature verification error: %s", e)
        return False


# ---------------------------------------------------------------------------
# Visa TAP endpoint bases
# ---------------------------------------------------------------------------

_VISA_SANDBOX_BASE = "https://sandbox.api.visa.com"
_VISA_PRODUCTION_BASE = "https://api.visa.com"


class VisaTAPAdapter:
    """Real Visa TAP adapter (placeholder until partnership/TRID confirmed).

    Requires:
      - TRID  — Token Requestor ID assigned by Visa
      - mTLS  — mutual TLS certificate issued by Visa
      - api_key — Visa Developer API key
    """

    def __init__(
        self,
        api_key: str = "",
        certificate_path: str = "",
        trid: str = "",
        environment: str = "sandbox",
        base_url: str = "",
        encryption: CredentialEncryption | None = None,
    ) -> None:
        self._api_key = api_key
        self._certificate_path = certificate_path
        self._trid = trid
        self._environment = environment
        self._base_url = base_url or (
            _VISA_PRODUCTION_BASE
            if environment == "production"
            else _VISA_SANDBOX_BASE
        )
        self._encryption = encryption or CredentialEncryption()

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.VISA_TAP

    async def execute(
        self,
        request: DelegatedPaymentRequest,
        credential: DelegatedCredential,
    ) -> DelegatedPaymentResult:
        # Decrypt credential token payload (contains DPAN + cryptogram seed)
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

        # Translate to Visa-specific request
        self._translate_to_visa(request, token_bytes, credential)

        # TODO: Call actual Visa Token Service API when partnership provides access
        # async with self._get_http_client() as client:
        #     response = await client.post(
        #         f"{self._base_url}/vtap/v1/payments",
        #         json=visa_payload,
        #         headers={"Authorization": f"Basic {self._api_key}"},
        #     )
        #     return self._translate_from_visa(response.json())
        raise NotImplementedError(
            "Real Visa TAP API not yet available. Use MockVisaTAPAdapter."
        )

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: CredentialEncryption | None = None,
        pan_reference: str | None = None,
    ) -> DelegatedCredential:
        """Provision a Visa token via the Visa Token Service API.

        Returns a DelegatedCredential holding an encrypted DPAN + TRID.
        The PAR (Payment Account Reference) is stored in provider_metadata.
        """
        # TODO: POST to Visa Token Service when TRID + mTLS cert are available
        # async with self._get_http_client() as client:
        #     resp = await client.post(
        #         f"{self._base_url}/vts/v1/tokens",
        #         json={"trid": self._trid, "panReference": pan_reference},
        #     )
        #     data = resp.json()
        #
        # dpan = data["token"]["value"].encode()
        # par  = data.get("paymentAccountReference", "")
        raise NotImplementedError(
            "Real Visa TAP provisioning not yet available. Use MockVisaTAPAdapter."
        )

    async def check_health(self) -> bool:
        """Return True if api_key and certificate path are configured."""
        return bool(self._api_key and self._certificate_path)

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        """Estimate Visa interchange fee (2% placeholder)."""
        return amount * Decimal("0.020")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _translate_to_visa(
        self,
        request: DelegatedPaymentRequest,
        token: bytes,
        credential: DelegatedCredential,
    ) -> dict[str, Any]:
        """Translate neutral contract to Visa Token Service request format."""
        dpan_ref = token.decode("utf-8", errors="replace")
        return {
            "trid": self._trid,
            "dpan": dpan_ref,
            "amount": {
                "value": str(int(request.amount * 100)),  # minor units
                "currency": request.currency.upper(),
            },
            "merchant": request.merchant_binding,
            "idempotencyKey": request.idempotency_key,
            "paymentAccountReference": credential.provider_metadata.get("par", ""),
            "metadata": request.metadata,
        }

    @staticmethod
    def _translate_from_visa(response: dict[str, Any]) -> DelegatedPaymentResult:
        """Translate Visa Token Service response back to neutral result."""
        approved = response.get("responseCode") == "00"
        raw_amount = Decimal(str(response.get("amount", {}).get("value", 0)))
        return DelegatedPaymentResult(
            success=approved,
            network="visa_tap",
            reference_id=response.get("transactionId", ""),
            amount=raw_amount / 100,
            currency=(response.get("amount", {}).get("currency", "")).upper(),
            fee=Decimal("0"),  # Visa does not return fee inline
            settlement_status="pending" if not approved else "instant",
            authorization_id=response.get("authorizationCode", ""),
            raw_response=response,
        )

    def _get_http_client(self):  # type: ignore[return]
        """Create an httpx AsyncClient configured with mTLS certificate."""
        try:
            import httpx
        except ImportError as exc:
            raise RuntimeError("httpx is required for VisaTAPAdapter") from exc

        cert = (self._certificate_path,) if self._certificate_path else None
        return httpx.AsyncClient(cert=cert, timeout=10.0)


# ---------------------------------------------------------------------------
# Mock adapter — dev / test
# ---------------------------------------------------------------------------


class MockVisaTAPAdapter:
    """Simulated Visa TAP adapter for dev/test.

    Follows the SimulatedMPCSigner / MockStripeSPTAdapter pattern.
    """

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.VISA_TAP

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
                reference_id=f"visa_mock_fail_{uuid.uuid4().hex[:8]}",
                error="Mock failure (configured)",
            )

        ref_id = f"visa_mock_{uuid.uuid4().hex[:12]}"
        fee = request.amount * Decimal("0.020")
        dpan_ref = credential.provider_metadata.get("dpan_ref", f"dpan_mock_{uuid.uuid4().hex[:8]}")

        return DelegatedPaymentResult(
            success=True,
            network=self.network.value,
            reference_id=ref_id,
            amount=request.amount,
            currency=request.currency,
            fee=fee,
            settlement_status="pending",
            authorization_id=f"auth_visa_mock_{uuid.uuid4().hex[:8]}",
            raw_response={
                "transactionId": ref_id,
                "responseCode": "00",
                "amount": {
                    "value": str(int(request.amount * 100)),
                    "currency": request.currency.upper(),
                },
                "dpanReference": dpan_ref,
            },
        )

    async def check_health(self) -> bool:
        return True

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        return amount * Decimal("0.020")

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: CredentialEncryption | None = None,
        pan_reference: str | None = None,
    ) -> DelegatedCredential:
        """Create a mock Visa TAP credential for testing.

        Stores a fake TRID/DPAN pair; PAR is recorded in provider_metadata.
        """
        trid_mock = f"TRID_MOCK_{uuid.uuid4().hex[:8].upper()}"
        dpan_mock = f"dpan_mock_{uuid.uuid4().hex[:12]}"
        par_mock = f"PAR_MOCK_{uuid.uuid4().hex[:16].upper()}"

        token = dpan_mock.encode()
        encrypted = b"mock_encrypted"
        if encryption:
            encrypted = encryption.encrypt_for_class(
                token, CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            )

        return DelegatedCredential(
            org_id=org_id,
            agent_id=agent_id,
            network=CredentialNetwork.VISA_TAP,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            token_reference=f"tok_ref_visa_mock_{uuid.uuid4().hex[:8]}",
            token_encrypted=encrypted,
            scope=scope,
            provider_metadata={
                "trid": trid_mock,
                "dpan_ref": dpan_mock,
                "par": par_mock,
                "mock": True,
            },
        )

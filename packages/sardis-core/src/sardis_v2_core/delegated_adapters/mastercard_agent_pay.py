"""Mastercard Agent Pay / MDES tokenization adapter.

Translation boundary: converts provider-neutral DelegatedPaymentRequest
to Mastercard MDES EMV token format.

Currently supports MockMastercardAgentPayAdapter for dev/test.  Swap to
real adapter when Mastercard partnership provides MDES API access and
P12 certificate provisioning.
"""
from __future__ import annotations

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


class MastercardAgentPayAdapter:
    """Real Mastercard Agent Pay / MDES adapter (placeholder until MDES API access confirmed).

    Authentication uses PKCS12 (P12) certificate + consumer key as required
    by the Mastercard Developers OAuth1.0a signing scheme.
    """

    def __init__(
        self,
        consumer_key: str = "",
        p12_certificate_path: str = "",
        key_alias: str = "keyalias",
        key_password: str = "",
        environment: str = "sandbox",
        base_url: str = "https://sandbox.api.mastercard.com",
        encryption: CredentialEncryption | None = None,
    ) -> None:
        self._consumer_key = consumer_key
        self._p12_certificate_path = p12_certificate_path
        self._key_alias = key_alias
        self._key_password = key_password
        self._environment = environment
        self._base_url = base_url.rstrip("/")
        self._encryption = encryption or CredentialEncryption()

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.MASTERCARD_AGENT_PAY

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

        # Translate to Mastercard-specific request
        self._translate_to_mastercard(request, token_bytes)

        # TODO: Call actual MDES Agent Pay API when partnership provides access
        # client = await self._get_http_client()
        # response = await client.post(
        #     f"{self._base_url}/mdes/agent-pay/1/0/authorize",
        #     json=mc_request,
        # )
        # return self._translate_from_mastercard(response.json())
        raise NotImplementedError(
            "Real Mastercard MDES Agent Pay API not yet available. "
            "Use MockMastercardAgentPayAdapter."
        )

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: CredentialEncryption | None = None,
        funding_account_info: dict[str, Any] | None = None,
    ) -> DelegatedCredential:
        """Provision an MDES EMV token via Mastercard tokenization API.

        Calls MDES Tokenize endpoint and returns a DelegatedCredential
        containing the encrypted token unique reference.

        TODO: Implement when MDES API access is provisioned.
        """
        # TODO: Call MDES Tokenize API
        # POST /mdes/digitization/1/0/tokenize
        # {
        #   "requestId": ...,
        #   "tokenType": "CLOUD",
        #   "taskId": ...,
        #   "fundingAccountInfo": { ... },
        # }
        raise NotImplementedError(
            "Real Mastercard MDES tokenization API not yet available. "
            "Use MockMastercardAgentPayAdapter."
        )

    async def check_health(self) -> bool:
        """Return True if consumer_key and P12 certificate path are configured."""
        return bool(self._consumer_key and self._p12_certificate_path)

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        return amount * Decimal("0.022")  # 2.2% interchange estimate

    def _translate_to_mastercard(
        self, request: DelegatedPaymentRequest, token: bytes,
    ) -> dict[str, Any]:
        """Translate neutral contract to Mastercard MDES EMV token request format."""
        return {
            "requestId": request.idempotency_key,
            "tokenUniqueReference": token.decode("utf-8", errors="replace"),
            "transactionAmount": {
                "value": str(int(request.amount * 100)),  # minor units
                "currency": request.currency.upper(),
            },
            "merchantIdentifier": request.merchant_binding,
            "channel": "AGENT_PAY",
            "metadata": request.metadata,
        }

    @staticmethod
    def _translate_from_mastercard(response: dict[str, Any]) -> DelegatedPaymentResult:
        """Translate MDES response back to neutral result."""
        status = response.get("status", "")
        authorization_code = response.get("authorizationCode", "")
        return DelegatedPaymentResult(
            success=status == "APPROVED",
            network="mastercard_agent_pay",
            reference_id=response.get("transactionId", ""),
            amount=(
                Decimal(str(response.get("transactionAmount", {}).get("value", 0))) / 100
            ),
            currency=(
                response.get("transactionAmount", {}).get("currency", "").upper()
            ),
            fee=Decimal("0"),  # interchange settled separately
            settlement_status="pending" if status == "APPROVED" else "failed",
            authorization_id=authorization_code,
            raw_response=response,
        )

    async def _get_http_client(self):
        """Create an httpx AsyncClient configured with PKCS12 certificate auth.

        Mastercard's API uses OAuth1.0a signing over HTTPS with mutual TLS
        via the provided P12 certificate.

        TODO: Wire up oauth1 signing once mastercard-oauth1-signer is available.
        """
        import httpx

        # Load PKCS12 cert for mutual TLS
        ssl_context = None
        if self._p12_certificate_path:
            try:
                import ssl
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
                ssl_context.load_cert_chain(
                    certfile=self._p12_certificate_path,
                    password=self._key_password.encode() if self._key_password else None,
                )
            except Exception as e:
                logger.warning("Failed to load P12 certificate: %s", e)

        return httpx.AsyncClient(
            verify=ssl_context or True,
            timeout=30.0,
        )


class MockMastercardAgentPayAdapter:
    """Simulated Mastercard Agent Pay adapter for dev/test.

    Follows the SimulatedMPCSigner pattern from sardis-wallet.
    """

    def __init__(self, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    @property
    def network(self) -> CredentialNetwork:
        return CredentialNetwork.MASTERCARD_AGENT_PAY

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
                reference_id=f"mc_mock_fail_{uuid.uuid4().hex[:8]}",
                error="Mock failure (configured)",
            )

        ref_id = f"mc_mock_{uuid.uuid4().hex[:12]}"
        fee = request.amount * Decimal("0.022")

        return DelegatedPaymentResult(
            success=True,
            network=self.network.value,
            reference_id=ref_id,
            amount=request.amount,
            currency=request.currency,
            fee=fee,
            settlement_status="pending",
            authorization_id=f"mc_auth_mock_{uuid.uuid4().hex[:8]}",
            raw_response={
                "transactionId": ref_id,
                "status": "APPROVED",
                "transactionAmount": {
                    "value": str(int(request.amount * 100)),
                    "currency": request.currency.upper(),
                },
                "authorizationCode": f"mc_auth_mock_{uuid.uuid4().hex[:8]}",
            },
        )

    async def check_health(self) -> bool:
        return True

    async def estimate_fee(self, amount: Decimal, currency: str) -> Decimal:
        return amount * Decimal("0.022")

    async def provision_credential(
        self,
        org_id: str,
        agent_id: str,
        scope: CredentialScope,
        encryption: CredentialEncryption | None = None,
        funding_account_info: dict[str, Any] | None = None,
    ) -> DelegatedCredential:
        """Create a mock MDES EMV token credential for testing.

        Simulates the MDES Tokenize API response by generating a fake
        token unique reference and PAR (Payment Account Reference).
        """
        token_unique_ref = f"mc_tur_{uuid.uuid4().hex[:16]}"
        par = f"mc_par_{uuid.uuid4().hex[:16]}"
        token = token_unique_ref.encode()

        encrypted = b"mock_encrypted"
        if encryption:
            encrypted = encryption.encrypt_for_class(
                token, CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            )
        return DelegatedCredential(
            org_id=org_id,
            agent_id=agent_id,
            network=CredentialNetwork.MASTERCARD_AGENT_PAY,
            status=CredentialStatus.ACTIVE,
            credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN,
            token_reference=f"mc_tok_ref_mock_{uuid.uuid4().hex[:8]}",
            token_encrypted=encrypted,
            scope=scope,
            provider_metadata={
                "token_unique_reference": token_unique_ref,
                "payment_account_reference": par,
                "funding_account_info": funding_account_info or {},
                "mock": True,
            },
        )

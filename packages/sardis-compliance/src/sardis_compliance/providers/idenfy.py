"""
iDenfy KYC provider implementation.

iDenfy provides cost-effective identity verification at $0.55/verification
with a 14-day free trial and NO monthly fees, making it ideal for startups
and scale-ups looking to minimize compliance costs.

Features:
- Government ID verification
- Liveness detection
- Face matching
- AML screening
- Document authenticity checks

Pricing: $0.55 per verification, 14-day free trial, no monthly fees
API Reference: https://documentation.idenfy.com/
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from datetime import datetime, timezone
from typing import Optional

from sardis_compliance.kyc import (
    KYCProvider,
    KYCResult,
    KYCStatus,
    InquirySession,
    VerificationRequest,
)
from sardis_compliance.retry import (
    create_retryable_client,
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)


class IdenfyKYCProvider(KYCProvider):
    """
    iDenfy KYC provider implementation.

    Cost-effective alternative to Persona at $0.55/verification with no monthly fees.
    Ideal for early-stage companies and high-volume verification needs.

    API Reference: https://documentation.idenfy.com/
    """

    BASE_URL = "https://ivs.idenfy.com/api/v2"

    def __init__(
        self,
        api_key: str,
        api_secret: str,
        webhook_secret: Optional[str] = None,
        environment: str = "sandbox",
    ):
        """
        Initialize iDenfy provider.

        Args:
            api_key: iDenfy API key
            api_secret: iDenfy API secret (used for HTTP Basic Auth)
            webhook_secret: Secret for HMAC-SHA256 webhook signature verification
            environment: 'sandbox' or 'production'
        """
        self._api_key = api_key
        self._api_secret = api_secret
        self._webhook_secret = webhook_secret or api_secret  # Default to api_secret
        self._environment = environment
        self._http_client = None
        self._retry_client = create_retryable_client(
            name="idenfy_kyc",
            retry_config=RetryConfig(
                max_retries=3,
                initial_delay_seconds=1.0,
                max_delay_seconds=30.0,
            ),
            circuit_config=CircuitBreakerConfig(
                failure_threshold=5,
                timeout_seconds=120.0,
            ),
            rate_config=RateLimitConfig(
                requests_per_second=10.0,
                burst_size=20,
            ),
        )

    async def _get_client(self):
        """Get or create HTTP client with Basic Auth."""
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                auth=(self._api_key, self._api_secret),  # HTTP Basic Auth
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        return self._http_client

    async def _request(self, method: str, path: str, **kwargs):
        """Make HTTP request with retry and circuit breaker."""
        client = await self._get_client()

        async def _do_request():
            response = await getattr(client, method)(path, **kwargs)
            response.raise_for_status()
            return response.json()

        result = await self._retry_client.execute(_do_request)
        if not result.success:
            raise result.error
        return result.value

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """
        Create a new iDenfy verification token.

        Returns an InquirySession with a verification token for frontend integration.
        """
        # Build verification token request
        data = {
            "clientId": request.reference_id,
            "locale": "en",
        }

        # Add optional fields
        if request.name_first:
            data["firstName"] = request.name_first
        if request.name_last:
            data["lastName"] = request.name_last
        if request.email:
            data["email"] = request.email
        if request.phone:
            data["phone"] = request.phone
        if request.address_street:
            data["address"] = request.address_street
        if request.address_city:
            data["city"] = request.address_city
        if request.address_country:
            data["country"] = request.address_country
        if request.address_postal_code:
            data["zipCode"] = request.address_postal_code

        # Add metadata as custom data
        if request.metadata:
            data["customData"] = str(request.metadata)

        result = await self._request("post", "/token", json=data)

        # iDenfy returns: { scanRef, authToken, clientId, redirectUrl, expiryTime }
        scan_ref = result.get("scanRef", "")
        auth_token = result.get("authToken", "")
        redirect_url = result.get("redirectUrl", "")
        expiry_time = result.get("expiryTime")  # Unix timestamp in seconds

        expires_at = None
        if expiry_time:
            try:
                expires_at = datetime.fromtimestamp(expiry_time, tz=timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse iDenfy expiry time: {e}")

        return InquirySession(
            inquiry_id=scan_ref,
            session_token=auth_token,
            template_id="idenfy_default",
            status=KYCStatus.PENDING,  # New token is always pending
            redirect_url=redirect_url,
            expires_at=expires_at,
        )

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """
        Get the status of an iDenfy verification.

        Args:
            inquiry_id: The scanRef from iDenfy
        """
        result = await self._request("get", f"/status/{inquiry_id}")

        # iDenfy status response structure:
        # {
        #   "status": { "overall": "APPROVED", "suspicionReasons": [], "autoDocument": "DOC_VALIDATED" },
        #   "data": { "docFirstName": "...", "docLastName": "...", ... },
        #   "fileUrls": { ... },
        #   "scanRef": "...",
        #   "clientId": "...",
        #   "startTime": 1234567890,
        #   "finishTime": 1234567890
        # }

        status_data = result.get("status", {})
        overall_status = status_data.get("overall", "ACTIVE")
        suspicion_reasons = status_data.get("suspicionReasons", [])

        # Map iDenfy status to KYCStatus
        status = self._map_status(overall_status)

        # Parse timestamps
        verified_at = None
        finish_time = result.get("finishTime")
        if finish_time:
            try:
                verified_at = datetime.fromtimestamp(finish_time, tz=timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse iDenfy finish time: {e}")

        # Build reason from suspicion reasons
        reason = None
        if suspicion_reasons:
            reason = f"Suspicion reasons: {', '.join(suspicion_reasons)}"
        elif overall_status == "DENIED":
            reason = "Verification denied by iDenfy"
        elif overall_status == "EXPIRED":
            reason = "Verification session expired"

        # Extract verification data
        data = result.get("data", {})

        return KYCResult(
            status=status,
            verification_id=inquiry_id,
            provider="idenfy",
            verified_at=verified_at,
            expires_at=None,  # iDenfy doesn't provide verification expiration
            reason=reason,
            metadata={
                "client_id": result.get("clientId"),
                "overall_status": overall_status,
                "suspicion_reasons": suspicion_reasons,
                "auto_document": status_data.get("autoDocument"),
                "auto_face": status_data.get("autoFace"),
                "manual_document": status_data.get("manualDocument"),
                "manual_face": status_data.get("manualFace"),
                "doc_first_name": data.get("docFirstName"),
                "doc_last_name": data.get("docLastName"),
                "doc_number": data.get("docNumber"),
                "doc_type": data.get("docType"),
                "doc_country": data.get("docIssuingCountry"),
                "start_time": result.get("startTime"),
                "finish_time": result.get("finishTime"),
            },
        )

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """
        Cancel an ongoing iDenfy verification.

        Note: iDenfy doesn't have a direct cancel endpoint.
        Verifications expire automatically based on configured timeout.
        """
        logger.warning(
            f"iDenfy does not support cancellation. "
            f"Verification {inquiry_id} will expire automatically."
        )
        return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify iDenfy webhook signature using HMAC-SHA256.

        iDenfy sends webhooks with a signature in the request headers.
        The signature is calculated as: HMAC-SHA256(payload, api_secret)

        Args:
            payload: Raw webhook payload bytes
            signature: Signature from webhook headers
        """
        if not self._webhook_secret:
            logger.warning("Webhook secret not configured for iDenfy")
            return False

        try:
            # Calculate expected signature
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()

            # Compare signatures (constant-time comparison)
            is_valid = hmac.compare_digest(signature, expected)

            if not is_valid:
                logger.warning(
                    f"iDenfy webhook signature mismatch. "
                    f"Expected: {expected[:8]}..., Got: {signature[:8]}..."
                )

            return is_valid

        except Exception as e:
            logger.error(f"iDenfy webhook verification failed: {e}")
            return False

    def _map_status(self, idenfy_status: str) -> KYCStatus:
        """
        Map iDenfy status to KYCStatus.

        iDenfy statuses:
        - APPROVED: Verification passed all checks
        - DENIED: Verification failed
        - SUSPECTED: Flagged for manual review
        - EXPIRED: Session timeout
        - ACTIVE: In progress
        - REVIEWING: Under manual review
        """
        status_map = {
            "APPROVED": KYCStatus.APPROVED,
            "DENIED": KYCStatus.DECLINED,
            "SUSPECTED": KYCStatus.NEEDS_REVIEW,
            "EXPIRED": KYCStatus.EXPIRED,
            "ACTIVE": KYCStatus.PENDING,
            "REVIEWING": KYCStatus.PENDING,
        }
        mapped = status_map.get(idenfy_status, KYCStatus.PENDING)

        if mapped == KYCStatus.PENDING:
            logger.debug(f"Mapped iDenfy status '{idenfy_status}' to PENDING")

        return mapped

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

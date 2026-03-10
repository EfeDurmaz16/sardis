"""Striga KYC provider for EEA users."""
from __future__ import annotations

import hashlib
import hmac
import logging

from sardis_compliance.kyc import (
    InquirySession,
    KYCProvider,
    KYCResult,
    KYCStatus,
    VerificationRequest,
)

from .client import StrigaClient

logger = logging.getLogger(__name__)


class StrigaKYCProvider(KYCProvider):
    """
    Striga KYC provider for EEA compliance.

    Uses Striga's hosted KYC flow which returns redirect URLs.
    Suitable for EEA-based agents requiring European banking access.
    """

    def __init__(
        self,
        client: StrigaClient,
        webhook_secret: str = "",
    ):
        self._client = client
        self._webhook_secret = webhook_secret

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """
        Create a new Striga KYC inquiry.

        Striga's hosted flow returns a redirect URL for the user to complete.
        """
        # Create Striga user first (if needed)
        user_data = {
            "email": request.email or f"{request.reference_id}@sardis.sh",
            "firstName": request.name_first or "",
            "lastName": request.name_last or "",
            "country": request.address_country or "",
        }
        if request.phone:
            user_data["phoneNumber"] = request.phone

        result = await self._client.request("POST", "/users", user_data)
        user_id = result.get("userId", "")

        # Initiate KYC verification
        kyc_result = await self._client.request(
            "POST",
            f"/users/{user_id}/kyc/start",
            {"redirectUrl": f"https://sardis.sh/kyc/callback?ref={request.reference_id}"},
        )

        return InquirySession(
            inquiry_id=user_id,
            session_token=kyc_result.get("sessionToken", ""),
            template_id="striga_eea",
            status=KYCStatus.PENDING,
            redirect_url=kyc_result.get("redirectUrl", kyc_result.get("verificationUrl", "")),
        )

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """Get Striga KYC verification status."""
        result = await self._client.request("GET", f"/users/{inquiry_id}/kyc")

        status_map = {
            "not_started": KYCStatus.NOT_STARTED,
            "pending": KYCStatus.PENDING,
            "initiated": KYCStatus.PENDING,
            "approved": KYCStatus.APPROVED,
            "verified": KYCStatus.APPROVED,
            "rejected": KYCStatus.DECLINED,
            "failed": KYCStatus.DECLINED,
            "review": KYCStatus.NEEDS_REVIEW,
        }

        raw_status = result.get("status", result.get("kycStatus", "pending"))
        kyc_status = status_map.get(raw_status, KYCStatus.PENDING)

        return KYCResult(
            status=kyc_status,
            verification_id=inquiry_id,
            provider="striga",
            reason=result.get("rejectionReason"),
            metadata={
                "reference_id": inquiry_id,
                "kyc_level": result.get("kycLevel", 0),
                "country": result.get("country", ""),
            },
        )

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """Cancel a Striga KYC inquiry."""
        try:
            await self._client.request("POST", f"/users/{inquiry_id}/kyc/cancel")
            return True
        except Exception as e:
            logger.error(f"Striga cancel_inquiry failed: {e}")
            return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Striga KYC webhook signature."""
        if not self._webhook_secret:
            logger.warning("Striga webhook secret not configured")
            return False

        expected = hmac.new(
            self._webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(signature, expected)

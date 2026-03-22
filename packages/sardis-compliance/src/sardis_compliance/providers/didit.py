"""
Didit KYC provider implementation.

Didit provides identity verification with ID document scanning,
liveness detection, face matching, and AML screening.

API Reference: https://docs.didit.me/api-reference/overview
Auth: x-api-key header (simple API key, no OAuth2)
Base URL: https://verification.didit.me
"""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import time
from datetime import UTC, datetime
from typing import Any

from sardis_compliance.kyc import (
    InquirySession,
    KYCProvider,
    KYCResult,
    KYCStatus,
    VerificationRequest,
)

logger = logging.getLogger(__name__)


class DiditKYCProvider(KYCProvider):
    """
    Didit KYC provider implementation.

    Uses simple API key authentication (x-api-key header).
    Creates verification sessions with a workflow_id that defines
    which checks to run (ID, liveness, face match, AML, etc.).

    Environment variables:
        DIDIT_API_KEY: API key from Didit Console
        DIDIT_WEBHOOK_SECRET: HMAC-SHA256 secret for webhook verification
        DIDIT_WORKFLOW_ID: Workflow ID defining verification checks

    API Reference: https://docs.didit.me/api-reference/overview
    """

    BASE_URL = "https://verification.didit.me"

    def __init__(
        self,
        api_key: str | None = None,
        webhook_secret: str | None = None,
        workflow_id: str | None = None,
    ):
        self._api_key = api_key or os.getenv("DIDIT_API_KEY", "")
        self._webhook_secret = webhook_secret or os.getenv("DIDIT_WEBHOOK_SECRET", "")
        self._workflow_id = workflow_id or os.getenv(
            "DIDIT_WORKFLOW_ID",
            "5851a693-9276-4d7e-ae87-d5f348b5f0bd",  # Custom KYC default
        )

        if not self._api_key:
            raise ValueError(
                "Didit API key is required. "
                "Set DIDIT_API_KEY environment variable or pass api_key directly."
            )

        self._http_client = None

    async def _get_client(self):
        """Get or create HTTP client with API key header."""
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "x-api-key": self._api_key,
                },
                timeout=30,
            )
        return self._http_client

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """Make an authenticated API request."""
        client = await self._get_client()

        import httpx

        try:
            response = await getattr(client, method)(path, **kwargs)
            response.raise_for_status()
            if response.status_code == 204:
                return {}
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Didit API error: %s %s → %s",
                method.upper(),
                path,
                e.response.text[:200],
            )
            raise
        except httpx.HTTPError as e:
            logger.error("Didit API request failed: %s %s → %s", method.upper(), path, e)
            raise

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """
        Create a new Didit verification session.

        POST /v3/session/ with workflow_id.
        Returns session with verification URL for the user.
        """
        data: dict[str, Any] = {
            "workflow_id": self._workflow_id,
            "vendor_data": request.reference_id,
        }

        # Add callback URL if configured
        callback_url = os.getenv("DIDIT_CALLBACK_URL", "")
        if callback_url:
            data["callback"] = callback_url

        # Add optional user details
        if request.metadata:
            data["metadata"] = request.metadata

        contact = {}
        if request.email:
            contact["email"] = request.email
            contact["send_notification_emails"] = True
        if contact:
            data["contact_details"] = contact

        expected = {}
        if request.name_first:
            expected["first_name"] = request.name_first
        if request.name_last:
            expected["last_name"] = request.name_last
        if expected:
            data["expected_details"] = expected

        result = await self._request("post", "/v3/session/", json=data)

        session_id = result.get("session_id", "")
        session_token = result.get("session_token", "")
        verification_url = result.get("url", "")
        status = result.get("status", "Not Started")

        logger.info(
            "Didit session created: id=%s ref=%s status=%s url=%s",
            session_id,
            request.reference_id,
            status,
            verification_url,
        )

        return InquirySession(
            inquiry_id=session_id,
            session_token=session_token,
            template_id=self._workflow_id,
            status=self._map_status(status),
            redirect_url=verification_url,
            expires_at=None,
        )

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """
        Get the status/decision of a Didit verification session.

        GET /v3/session/{session_id}/decision/
        """
        result = await self._request("get", f"/v3/session/{inquiry_id}/decision/")

        status_str = result.get("status", "Not Started")
        status = self._map_status(status_str)

        # Extract check results
        id_verifications = result.get("id_verifications")
        liveness_checks = result.get("liveness_checks")
        face_matches = result.get("face_matches")
        aml_screenings = result.get("aml_screenings")

        created_at_str = result.get("created_at")
        verified_at = None
        if status == KYCStatus.APPROVED and created_at_str:
            verified_at = self._parse_datetime(created_at_str)

        return KYCResult(
            status=status,
            verification_id=inquiry_id,
            provider="didit",
            verified_at=verified_at,
            expires_at=None,
            reason=None,
            metadata={
                "didit_status": status_str,
                "workflow_id": result.get("workflow_id"),
                "vendor_data": result.get("vendor_data"),
                "features": result.get("features"),
                "id_verifications": id_verifications,
                "liveness_checks": liveness_checks,
                "face_matches": face_matches,
                "aml_screenings": aml_screenings,
                "ip_analyses": result.get("ip_analyses"),
                "reviews": result.get("reviews"),
            },
        )

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """
        Delete/cancel a Didit verification session.

        DELETE /v3/session/{session_id}/
        """
        try:
            await self._request("delete", f"/v3/session/{inquiry_id}/")
            logger.info("Didit session deleted: %s", inquiry_id)
            return True
        except Exception as e:
            logger.error("Didit cancel failed for %s: %s", inquiry_id, e)
            return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Didit webhook signature using HMAC-SHA256 (X-Signature-V2).

        Didit signs webhooks with canonicalized JSON (sorted keys, compact separators).
        The signature header is X-Signature-V2.
        """
        if not self._webhook_secret:
            logger.warning("Didit webhook secret not configured (DIDIT_WEBHOOK_SECRET)")
            return False

        try:
            # For X-Signature-V2: canonical JSON of the parsed body
            body_dict = json.loads(payload)
            canonical = json.dumps(
                body_dict,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            )
            expected = hmac.new(
                self._webhook_secret.encode("utf-8"),
                canonical.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            is_valid = hmac.compare_digest(signature, expected)

            if not is_valid:
                logger.warning(
                    "Didit webhook sig mismatch. Expected: %s..., Got: %s...",
                    expected[:8],
                    signature[:8],
                )

            return is_valid

        except Exception as e:
            logger.error("Didit webhook verification failed: %s", e)
            return False

    def _map_status(self, didit_status: str) -> KYCStatus:
        """
        Map Didit verification status to KYCStatus.

        Didit uses Title Case with spaces:
        "Not Started", "In Progress", "Approved", "Declined",
        "In Review", "Resubmitted", "Expired", "Abandoned", "Kyc Expired"
        """
        normalized = didit_status.lower().strip()
        status_map = {
            "not started": KYCStatus.NOT_STARTED,
            "in progress": KYCStatus.PENDING,
            "approved": KYCStatus.APPROVED,
            "declined": KYCStatus.DECLINED,
            "in review": KYCStatus.NEEDS_REVIEW,
            "resubmitted": KYCStatus.PENDING,
            "expired": KYCStatus.EXPIRED,
            "abandoned": KYCStatus.EXPIRED,
            "kyc expired": KYCStatus.EXPIRED,
        }
        mapped = status_map.get(normalized, KYCStatus.PENDING)

        if normalized not in status_map:
            logger.warning(
                "Unknown Didit status '%s', defaulting to PENDING", didit_status
            )

        return mapped

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """Parse ISO-8601 datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse Didit datetime '%s': %s", value, e)
            return None

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

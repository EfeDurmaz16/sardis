"""
Didit KYC provider implementation.

Didit provides decentralized identity verification with reusable credentials,
offering privacy-preserving KYC through zero-knowledge proofs.

Features:
- Government ID verification
- Liveness detection / selfie matching
- AML screening
- Reusable verification credentials (users verify once, reuse across services)
- GDPR-compliant data handling

API Reference: https://docs.didit.me/
Auth: OAuth2 client_credentials flow (client_id + client_secret)
"""
from __future__ import annotations

import hashlib
import hmac
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
from sardis_compliance.retry import (
    CircuitBreakerConfig,
    RateLimitConfig,
    RetryConfig,
    create_retryable_client,
)

logger = logging.getLogger(__name__)


class DiditKYCProvider(KYCProvider):
    """
    Didit KYC provider implementation.

    Uses OAuth2 client_credentials for authentication and provides
    identity verification through Didit's decentralized identity platform.

    Environment variables:
        DIDIT_CLIENT_ID: OAuth2 client ID
        DIDIT_CLIENT_SECRET: OAuth2 client secret
        DIDIT_WEBHOOK_SECRET: HMAC-SHA256 secret for webhook verification

    API Reference: https://docs.didit.me/
    """

    BASE_URL = "https://api.didit.me/v2"
    AUTH_URL = "https://api.didit.me/auth/token"

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        webhook_secret: str | None = None,
        environment: str = "sandbox",
    ):
        """
        Initialize Didit provider.

        Args:
            client_id: Didit OAuth2 client ID (falls back to DIDIT_CLIENT_ID env var)
            client_secret: Didit OAuth2 client secret (falls back to DIDIT_CLIENT_SECRET env var)
            webhook_secret: Secret for HMAC-SHA256 webhook signature verification
                            (falls back to DIDIT_WEBHOOK_SECRET env var)
            environment: 'sandbox' or 'production'
        """
        self._client_id = client_id or os.getenv("DIDIT_CLIENT_ID", "")
        self._client_secret = client_secret or os.getenv("DIDIT_CLIENT_SECRET", "")
        self._webhook_secret = webhook_secret or os.getenv("DIDIT_WEBHOOK_SECRET", "")
        self._environment = environment

        if not self._client_id or not self._client_secret:
            raise ValueError(
                "Didit client_id and client_secret are required. "
                "Set DIDIT_CLIENT_ID and DIDIT_CLIENT_SECRET environment variables "
                "or pass them directly."
            )

        self._http_client = None
        self._access_token: str | None = None
        self._token_expires_at: float = 0.0

        self._retry_client = create_retryable_client(
            name="didit_kyc",
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
        """Get or create HTTP client."""
        if self._http_client is None:
            import httpx

            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                timeout=30,
            )
        return self._http_client

    async def _ensure_access_token(self) -> str:
        """
        Obtain or refresh the OAuth2 access token via client_credentials grant.

        Tokens are cached until 60 seconds before expiry to avoid
        clock-skew issues.

        Returns:
            Valid access token string.

        Raises:
            RuntimeError: If token exchange fails.
        """
        # Return cached token if still valid (with 60s buffer)
        if self._access_token and time.monotonic() < (self._token_expires_at - 60):
            return self._access_token

        import httpx

        client = await self._get_client()

        try:
            response = await client.post(
                self.AUTH_URL,
                data={
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            response.raise_for_status()
            token_data = response.json()
        except httpx.HTTPStatusError as e:
            logger.error(
                "Didit OAuth2 token exchange failed: %s %s",
                e.response.status_code,
                e.response.text[:200],
            )
            raise RuntimeError(
                f"Didit OAuth2 token exchange failed with status {e.response.status_code}"
            ) from e
        except httpx.HTTPError as e:
            logger.error("Didit OAuth2 token request failed: %s", e)
            raise RuntimeError("Didit OAuth2 token request failed") from e

        self._access_token = token_data.get("access_token")
        if not self._access_token:
            raise RuntimeError(
                "Didit OAuth2 response missing access_token. "
                f"Response keys: {list(token_data.keys())}"
            )

        # Cache expiry based on expires_in (default 3600s if not provided)
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires_at = time.monotonic() + expires_in

        logger.debug(
            "Didit OAuth2 token acquired, expires in %ds", expires_in
        )
        return self._access_token

    async def _request(self, method: str, path: str, **kwargs) -> Any:
        """
        Make an authenticated HTTP request with retry and circuit breaker.

        Automatically injects a valid Bearer token. On 401, forces a token
        refresh and retries once.

        Args:
            method: HTTP method (get, post, patch, delete)
            path: API path relative to BASE_URL
            **kwargs: Passed through to httpx request

        Returns:
            Parsed JSON response.

        Raises:
            Exception from the underlying HTTP call or retry logic.
        """
        client = await self._get_client()
        token = await self._ensure_access_token()

        async def _do_request():
            headers = {
                **(kwargs.pop("headers", {}) or {}),
                "Authorization": f"Bearer {token}",
            }
            response = await getattr(client, method)(
                path, headers=headers, **kwargs
            )
            response.raise_for_status()
            return response.json()

        result = await self._retry_client.execute(_do_request)

        if not result.success:
            # If we got a 401, force token refresh and retry once
            error = result.error
            import httpx

            if isinstance(error, httpx.HTTPStatusError) and error.response.status_code == 401:
                logger.info("Didit API returned 401, refreshing access token")
                self._access_token = None
                self._token_expires_at = 0.0
                refreshed_token = await self._ensure_access_token()

                async def _retry_request():
                    headers_retry = {
                        "Authorization": f"Bearer {refreshed_token}",
                    }
                    resp = await getattr(client, method)(
                        path, headers=headers_retry, **kwargs
                    )
                    resp.raise_for_status()
                    return resp.json()

                retry_result = await self._retry_client.execute(_retry_request)
                if not retry_result.success:
                    raise retry_result.error
                return retry_result.value

            raise error

        return result.value

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """
        Create a new Didit verification session.

        Calls POST /v2/verifications to start an identity verification flow.
        Returns an InquirySession with a session URL for frontend integration.

        Args:
            request: Verification request with user details.

        Returns:
            InquirySession with redirect URL and session token.
        """
        data: dict[str, Any] = {
            "reference_id": request.reference_id,
            "type": self._map_verification_type(request.verification_type),
        }

        # Add optional user details
        if request.name_first:
            data["first_name"] = request.name_first
        if request.name_last:
            data["last_name"] = request.name_last
        if request.email:
            data["email"] = request.email
        if request.phone:
            data["phone"] = request.phone
        if request.address_street:
            data["address"] = {
                "street": request.address_street,
                "city": request.address_city or "",
                "country": request.address_country or "",
                "postal_code": request.address_postal_code or "",
            }

        # Include metadata
        if request.metadata:
            data["metadata"] = request.metadata

        result = await self._request("post", "/verifications", json=data)

        # Didit response: { id, session_token, session_url, status, expires_at, ... }
        verification_id = result.get("id", "")
        session_token = result.get("session_token", "")
        session_url = result.get("session_url", "")
        status = result.get("status", "pending")
        expires_at_str = result.get("expires_at")

        expires_at = self._parse_datetime(expires_at_str)

        logger.info(
            "Didit verification created: id=%s ref=%s status=%s",
            verification_id,
            request.reference_id,
            status,
        )

        return InquirySession(
            inquiry_id=verification_id,
            session_token=session_token,
            template_id="didit_default",
            status=self._map_status(status),
            redirect_url=session_url,
            expires_at=expires_at,
        )

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """
        Get the status of a Didit verification.

        Calls GET /v2/verifications/{id} and maps the response to KYCResult.

        Args:
            inquiry_id: The Didit verification ID.

        Returns:
            KYCResult with mapped status, timestamps, and metadata.
        """
        result = await self._request("get", f"/verifications/{inquiry_id}")

        # Didit verification response:
        # {
        #   "id": "...",
        #   "reference_id": "...",
        #   "status": "approved" | "declined" | "pending" | "expired" | "review",
        #   "decision": { "reason": "...", "risk_level": "..." },
        #   "verified_at": "ISO-8601",
        #   "expires_at": "ISO-8601",
        #   "created_at": "ISO-8601",
        #   "checks": [ { "type": "...", "status": "...", "details": {...} } ],
        #   "metadata": {...}
        # }

        status_str = result.get("status", "pending")
        status = self._map_status(status_str)

        decision = result.get("decision", {})
        reason = decision.get("reason")
        risk_level = decision.get("risk_level")

        checks = result.get("checks", [])

        verified_at = self._parse_datetime(result.get("verified_at"))
        expires_at = self._parse_datetime(result.get("expires_at"))

        return KYCResult(
            status=status,
            verification_id=inquiry_id,
            provider="didit",
            verified_at=verified_at,
            expires_at=expires_at,
            reason=reason,
            metadata={
                "reference_id": result.get("reference_id"),
                "didit_status": status_str,
                "risk_level": risk_level,
                "checks": [
                    {
                        "type": c.get("type"),
                        "status": c.get("status"),
                        "details": c.get("details", {}),
                    }
                    for c in checks
                ],
                "created_at": result.get("created_at"),
            },
        )

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """
        Cancel an ongoing Didit verification.

        Calls POST /v2/verifications/{id}/cancel.

        Args:
            inquiry_id: The Didit verification ID to cancel.

        Returns:
            True if cancellation succeeded, False otherwise.
        """
        try:
            await self._request(
                "post", f"/verifications/{inquiry_id}/cancel", json={}
            )
            logger.info("Didit verification cancelled: %s", inquiry_id)
            return True
        except Exception as e:
            logger.error("Didit cancel_inquiry failed for %s: %s", inquiry_id, e)
            return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """
        Verify Didit webhook signature using HMAC-SHA256.

        Didit signs webhook payloads with the webhook secret configured in
        the dashboard. The signature is sent as a hex-encoded HMAC-SHA256 digest.

        Args:
            payload: Raw webhook request body bytes.
            signature: Hex-encoded HMAC-SHA256 signature from the webhook header.

        Returns:
            True if signature is valid, False otherwise.
        """
        if not self._webhook_secret:
            logger.warning(
                "Didit webhook secret not configured. "
                "Set DIDIT_WEBHOOK_SECRET environment variable."
            )
            return False

        try:
            expected = hmac.new(
                self._webhook_secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).hexdigest()

            is_valid = hmac.compare_digest(signature, expected)

            if not is_valid:
                logger.warning(
                    "Didit webhook signature mismatch. "
                    "Expected: %s..., Got: %s...",
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

        Didit statuses:
        - created: Verification session created, user hasn't started
        - pending: User has started but verification is in progress
        - approved: Verification passed all checks
        - declined: Verification failed checks
        - expired: Verification session timed out
        - review: Flagged for manual review
        - cancelled: Verification was cancelled

        Args:
            didit_status: Raw status string from Didit API.

        Returns:
            Mapped KYCStatus enum value.
        """
        status_map = {
            "created": KYCStatus.NOT_STARTED,
            "pending": KYCStatus.PENDING,
            "processing": KYCStatus.PENDING,
            "approved": KYCStatus.APPROVED,
            "verified": KYCStatus.APPROVED,
            "declined": KYCStatus.DECLINED,
            "rejected": KYCStatus.DECLINED,
            "failed": KYCStatus.DECLINED,
            "expired": KYCStatus.EXPIRED,
            "review": KYCStatus.NEEDS_REVIEW,
            "manual_review": KYCStatus.NEEDS_REVIEW,
            "cancelled": KYCStatus.EXPIRED,
        }
        mapped = status_map.get(didit_status.lower(), KYCStatus.PENDING)

        if didit_status.lower() not in status_map:
            logger.warning(
                "Unknown Didit status '%s', defaulting to PENDING", didit_status
            )

        return mapped

    @staticmethod
    def _map_verification_type(verification_type) -> str:
        """
        Map internal VerificationType to Didit's verification type string.

        Args:
            verification_type: VerificationType enum value.

        Returns:
            Didit-compatible verification type string.
        """
        from sardis_compliance.kyc import VerificationType

        type_map = {
            VerificationType.IDENTITY: "identity",
            VerificationType.DOCUMENT: "document",
            VerificationType.SELFIE: "selfie",
            VerificationType.ADDRESS: "address",
            VerificationType.PHONE: "phone",
            VerificationType.EMAIL: "email",
        }
        return type_map.get(verification_type, "identity")

    def _parse_datetime(self, value: str | None) -> datetime | None:
        """
        Parse ISO-8601 datetime string to datetime object.

        Handles both 'Z' suffix and explicit timezone offsets.

        Args:
            value: ISO-8601 datetime string, or None.

        Returns:
            Parsed datetime with UTC timezone, or None.
        """
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except (ValueError, TypeError) as e:
            logger.warning("Failed to parse Didit datetime '%s': %s", value, e)
            return None

    async def close(self) -> None:
        """Close HTTP client and clear cached token."""
        self._access_token = None
        self._token_expires_at = 0.0
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

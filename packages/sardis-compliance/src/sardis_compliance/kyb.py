"""
KYB (Know Your Business) integration module.

Supports Persona as the primary KYB provider for business entity verification.
Persona Business Inquiries API: https://docs.withpersona.com/reference/create-a-business-inquiry

Required for organizations deploying agents that transact above KYB thresholds.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from sardis_compliance.retry import (
    create_retryable_client,
    RetryConfig,
    CircuitBreakerConfig,
    RateLimitConfig,
)

logger = logging.getLogger(__name__)


class KYBStatus(str, Enum):
    """KYB verification status."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    EXPIRED = "expired"
    NEEDS_REVIEW = "needs_review"


@dataclass
class KYBResult:
    """Result of a KYB verification check."""
    status: KYBStatus
    inquiry_id: str
    provider: str = "persona"
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    business_name: Optional[str] = None
    ein_last4: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_verified(self) -> bool:
        if self.status != KYBStatus.APPROVED:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True


@dataclass
class BusinessVerificationRequest:
    """Request to create a new business verification."""
    reference_id: str  # Organization ID
    business_name: str
    ein: Optional[str] = None  # US Employer Identification Number
    incorporation_state: Optional[str] = None
    incorporation_country: str = "US"
    website: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_state: Optional[str] = None
    address_country: Optional[str] = None
    address_postal_code: Optional[str] = None
    beneficial_owners: list[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BusinessInquirySession:
    """Persona business inquiry session."""
    inquiry_id: str
    session_token: str
    template_id: str
    status: KYBStatus
    redirect_url: Optional[str] = None


class KYBProvider(ABC):
    """Abstract interface for KYB providers."""

    @abstractmethod
    async def create_business_inquiry(
        self,
        request: BusinessVerificationRequest,
    ) -> BusinessInquirySession:
        pass

    @abstractmethod
    async def get_inquiry_status(self, inquiry_id: str) -> KYBResult:
        pass

    @abstractmethod
    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        pass


class PersonaKYBProvider(KYBProvider):
    """
    Persona KYB provider implementation.

    Uses Persona Business Inquiries for entity verification:
    - Business name + EIN verification
    - Secretary of State filings check
    - Beneficial ownership identification
    - Sanctions / watchlist screening
    """

    BASE_URL = "https://withpersona.com/api/v1"

    def __init__(
        self,
        api_key: str,
        template_id: str,
        webhook_secret: Optional[str] = None,
        environment: str = "sandbox",
    ):
        self._api_key = api_key
        self._template_id = template_id
        self._webhook_secret = webhook_secret
        self._environment = environment
        self._http_client = None
        self._retry_client = create_retryable_client(
            name="persona_kyb",
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
        if self._http_client is None:
            import httpx
            self._http_client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Persona-Version": "2023-01-05",
                    "Content-Type": "application/json",
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

    async def create_business_inquiry(
        self,
        request: BusinessVerificationRequest,
    ) -> BusinessInquirySession:
        data = {
            "data": {
                "attributes": {
                    "inquiry-template-id": self._template_id,
                    "reference-id": request.reference_id,
                    "fields": {
                        "business-name": request.business_name,
                    },
                },
            },
        }

        fields = data["data"]["attributes"]["fields"]
        if request.ein:
            fields["business-ein"] = request.ein
        if request.incorporation_state:
            fields["business-incorporation-state"] = request.incorporation_state
        if request.incorporation_country:
            fields["business-incorporation-country-code"] = request.incorporation_country
        if request.website:
            fields["business-website"] = request.website
        if request.address_street:
            fields["business-address-street-1"] = request.address_street
        if request.address_city:
            fields["business-address-city"] = request.address_city
        if request.address_state:
            fields["business-address-subdivision"] = request.address_state
        if request.address_country:
            fields["business-address-country-code"] = request.address_country
        if request.address_postal_code:
            fields["business-address-postal-code"] = request.address_postal_code

        result = await self._request("post", "/inquiries", json=data)

        inquiry_data = result.get("data", {})
        attributes = inquiry_data.get("attributes", {})

        session_data = await self._request(
            "post",
            f"/inquiries/{inquiry_data['id']}/generate-one-time-link",
        )

        return BusinessInquirySession(
            inquiry_id=inquiry_data["id"],
            session_token=session_data.get("meta", {}).get("session-token", ""),
            template_id=self._template_id,
            status=self._map_status(attributes.get("status", "pending")),
            redirect_url=session_data.get("meta", {}).get("one-time-link"),
        )

    async def get_inquiry_status(self, inquiry_id: str) -> KYBResult:
        result = await self._request("get", f"/inquiries/{inquiry_id}")

        data = result.get("data", {})
        attributes = data.get("attributes", {})

        return KYBResult(
            status=self._map_status(attributes.get("status", "pending")),
            inquiry_id=inquiry_id,
            provider="persona",
            verified_at=self._parse_datetime(attributes.get("completed-at")),
            expires_at=self._parse_datetime(attributes.get("expired-at")),
            reason=attributes.get("decline-reason"),
            business_name=attributes.get("fields", {}).get("business-name"),
            metadata={
                "reference_id": attributes.get("reference-id"),
                "template_id": attributes.get("inquiry-template-id"),
                "checks": attributes.get("checks", []),
            },
        )

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        if not self._webhook_secret:
            logger.warning("KYB webhook secret not configured")
            return False
        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            return hmac.compare_digest(signature, expected)
        except Exception as e:
            logger.error(f"KYB webhook verification failed: {e}")
            return False

    def _map_status(self, persona_status: str) -> KYBStatus:
        status_map = {
            "created": KYBStatus.NOT_STARTED,
            "pending": KYBStatus.PENDING,
            "completed": KYBStatus.APPROVED,
            "approved": KYBStatus.APPROVED,
            "declined": KYBStatus.DECLINED,
            "failed": KYBStatus.DECLINED,
            "expired": KYBStatus.EXPIRED,
            "needs_review": KYBStatus.NEEDS_REVIEW,
        }
        return status_map.get(persona_status, KYBStatus.PENDING)

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    async def close(self):
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockKYBProvider(KYBProvider):
    """Mock KYB provider for development and testing."""

    def __init__(self):
        self._inquiries: Dict[str, KYBResult] = {}
        self._counter = 0

    async def create_business_inquiry(
        self,
        request: BusinessVerificationRequest,
    ) -> BusinessInquirySession:
        self._counter += 1
        inquiry_id = f"biz_inq_mock_{self._counter}"

        self._inquiries[inquiry_id] = KYBResult(
            status=KYBStatus.PENDING,
            inquiry_id=inquiry_id,
            provider="mock",
            business_name=request.business_name,
            metadata={"reference_id": request.reference_id},
        )

        return BusinessInquirySession(
            inquiry_id=inquiry_id,
            session_token=f"biz_session_mock_{self._counter}",
            template_id="mock_kyb_template",
            status=KYBStatus.PENDING,
            redirect_url=f"https://mock.kyb.local/verify/{inquiry_id}",
        )

    async def get_inquiry_status(self, inquiry_id: str) -> KYBResult:
        if inquiry_id not in self._inquiries:
            raise ValueError(f"Unknown KYB inquiry: {inquiry_id}")
        return self._inquiries[inquiry_id]

    async def verify_webhook(self, payload: bytes, signature: str) -> bool:
        return True

    def approve_inquiry(self, inquiry_id: str) -> None:
        if inquiry_id in self._inquiries:
            self._inquiries[inquiry_id] = KYBResult(
                status=KYBStatus.APPROVED,
                inquiry_id=inquiry_id,
                provider="mock",
                verified_at=datetime.now(timezone.utc),
                business_name=self._inquiries[inquiry_id].business_name,
            )


class KYBService:
    """
    High-level KYB service for managing business entity verification.

    Required for organizations that deploy agents handling transactions
    above regulatory thresholds.
    """

    def __init__(
        self,
        provider: Optional[KYBProvider] = None,
        require_kyb_above: int = 10_000_000,  # $100,000 cumulative in minor units
    ):
        self._provider = provider or MockKYBProvider()
        self._require_kyb_above = require_kyb_above
        self._cache: Dict[str, KYBResult] = {}

    async def create_verification(
        self,
        org_id: str,
        business_name: str,
        **kwargs,
    ) -> BusinessInquirySession:
        request = BusinessVerificationRequest(
            reference_id=org_id,
            business_name=business_name,
            **kwargs,
        )
        return await self._provider.create_business_inquiry(request)

    async def check_verification(
        self,
        org_id: str,
        force_refresh: bool = False,
    ) -> KYBResult:
        if not force_refresh and org_id in self._cache:
            cached = self._cache[org_id]
            if cached.is_verified:
                return cached

        # Look up from database
        try:
            from sardis_v2_core.database import Database
            row = await Database.fetchrow(
                """
                SELECT inquiry_id, provider, status, verified_at, expires_at,
                       reason, business_name, metadata
                FROM kyb_verifications
                WHERE org_id = $1
                ORDER BY created_at DESC LIMIT 1
                """,
                org_id,
            )
            if row:
                import json
                meta = row["metadata"]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                result = KYBResult(
                    status=KYBStatus(row["status"]),
                    inquiry_id=row["inquiry_id"],
                    provider=row["provider"] or "persona",
                    verified_at=row["verified_at"],
                    expires_at=row["expires_at"],
                    reason=row["reason"],
                    business_name=row["business_name"],
                    metadata=meta or {},
                )
                self._cache[org_id] = result
                return result
        except Exception as e:
            logger.warning(f"DB lookup for KYB failed: {e}")

        return KYBResult(
            status=KYBStatus.NOT_STARTED,
            inquiry_id="",
            provider=self._provider.__class__.__name__,
        )

    async def is_kyb_required(self, org_id: str, cumulative_volume: int) -> bool:
        if cumulative_volume < self._require_kyb_above:
            return False
        result = await self.check_verification(org_id)
        return not result.is_verified

    async def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        if event_type in ("inquiry.completed", "inquiry.approved"):
            inquiry_id = payload.get("data", {}).get("id")
            if inquiry_id:
                result = await self._provider.get_inquiry_status(inquiry_id)
                reference_id = result.metadata.get("reference_id")
                if reference_id:
                    self._cache[reference_id] = result
                    logger.info(f"KYB completed for {reference_id}: {result.status}")
                    try:
                        import json as _json
                        from sardis_v2_core.database import Database
                        await Database.execute(
                            """
                            INSERT INTO kyb_verifications
                                (org_id, inquiry_id, provider, status, verified_at,
                                 expires_at, reason, business_name, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                            ON CONFLICT (inquiry_id) DO UPDATE SET
                                status = EXCLUDED.status,
                                verified_at = EXCLUDED.verified_at,
                                updated_at = NOW()
                            """,
                            reference_id,
                            inquiry_id,
                            result.provider,
                            result.status.value,
                            result.verified_at,
                            result.expires_at,
                            result.reason,
                            result.business_name,
                            _json.dumps(result.metadata, default=str),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist KYB result: {e}")


def create_kyb_service(
    api_key: Optional[str] = None,
    template_id: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    environment: str = "sandbox",
) -> KYBService:
    """Factory function to create KYB service."""
    import os

    webhook_secret = webhook_secret or os.getenv("PERSONA_KYB_WEBHOOK_SECRET")

    if api_key and template_id:
        if environment == "production" and not webhook_secret:
            logger.error(
                "SECURITY WARNING: Production KYB service without webhook_secret. "
                "Set PERSONA_KYB_WEBHOOK_SECRET."
            )
        provider = PersonaKYBProvider(
            api_key=api_key,
            template_id=template_id,
            webhook_secret=webhook_secret,
            environment=environment,
        )
    else:
        env = os.getenv("SARDIS_ENVIRONMENT", "dev")
        if env in ("prod", "production"):
            raise RuntimeError(
                "Production requires Persona KYB provider. "
                "Set PERSONA_API_KEY and PERSONA_KYB_TEMPLATE_ID."
            )
        logger.warning("No Persona KYB API key provided, using mock (dev/test only)")
        provider = MockKYBProvider()

    return KYBService(provider=provider)

"""
KYC (Know Your Customer) integration module.

Supports Persona as the primary KYC provider for identity verification.
Persona API: https://docs.withpersona.com/
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class KYCStatus(str, Enum):
    """KYC verification status."""
    NOT_STARTED = "not_started"
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    EXPIRED = "expired"
    NEEDS_REVIEW = "needs_review"


class VerificationType(str, Enum):
    """Types of verification supported."""
    IDENTITY = "identity"
    DOCUMENT = "document"
    SELFIE = "selfie"
    ADDRESS = "address"
    PHONE = "phone"
    EMAIL = "email"


@dataclass
class KYCResult:
    """Result of a KYC verification check."""
    status: KYCStatus
    verification_id: str
    provider: str = "persona"
    verified_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if KYC verification has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    @property
    def is_verified(self) -> bool:
        """Check if KYC is verified and not expired."""
        if self.status != KYCStatus.APPROVED:
            return False
        if self.is_expired:
            return False
        return True

    @property
    def effective_status(self) -> KYCStatus:
        """
        Get the effective status, accounting for expiration.

        Returns EXPIRED if the verification was approved but has since expired.
        """
        if self.status == KYCStatus.APPROVED and self.is_expired:
            return KYCStatus.EXPIRED
        return self.status

    def time_until_expiration(self) -> Optional[float]:
        """
        Get seconds until expiration, or None if no expiration set.

        Returns negative value if already expired.
        """
        if self.expires_at is None:
            return None
        delta = self.expires_at - datetime.now(timezone.utc)
        return delta.total_seconds()


@dataclass
class VerificationRequest:
    """Request to create a new verification."""
    reference_id: str  # Agent ID or Wallet ID
    verification_type: VerificationType = VerificationType.IDENTITY
    name_first: Optional[str] = None
    name_last: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address_street: Optional[str] = None
    address_city: Optional[str] = None
    address_country: Optional[str] = None
    address_postal_code: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class InquirySession:
    """Persona inquiry session for frontend integration."""
    inquiry_id: str
    session_token: str
    template_id: str
    status: KYCStatus
    redirect_url: Optional[str] = None
    expires_at: Optional[datetime] = None


class KYCProvider(ABC):
    """Abstract interface for KYC providers."""

    @abstractmethod
    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """Create a new verification inquiry."""
        pass

    @abstractmethod
    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """Get the status of an inquiry."""
        pass

    @abstractmethod
    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """Cancel an ongoing inquiry."""
        pass

    @abstractmethod
    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify webhook signature."""
        pass


class PersonaKYCProvider(KYCProvider):
    """
    Persona KYC provider implementation.
    
    Persona provides identity verification through:
    - Government ID verification
    - Selfie verification
    - Database verification
    - Watchlist screening
    
    API Reference: https://docs.withpersona.com/reference/introduction
    """

    BASE_URL = "https://withpersona.com/api/v1"

    def __init__(
        self,
        api_key: str,
        template_id: str,
        webhook_secret: Optional[str] = None,
        environment: str = "sandbox",
    ):
        """
        Initialize Persona provider.
        
        Args:
            api_key: Persona API key
            template_id: Inquiry template ID
            webhook_secret: Secret for webhook signature verification
            environment: 'sandbox' or 'production'
        """
        self._api_key = api_key
        self._template_id = template_id
        self._webhook_secret = webhook_secret
        self._environment = environment
        self._http_client = None

    async def _get_client(self):
        """Get or create HTTP client."""
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

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """
        Create a new Persona inquiry.
        
        Returns an InquirySession with a session token for frontend integration.
        """
        client = await self._get_client()
        
        # Build inquiry data
        data = {
            "data": {
                "attributes": {
                    "inquiry-template-id": self._template_id,
                    "reference-id": request.reference_id,
                    "fields": {},
                },
            },
        }
        
        # Add optional fields
        fields = {}
        if request.name_first:
            fields["name-first"] = request.name_first
        if request.name_last:
            fields["name-last"] = request.name_last
        if request.email:
            fields["email-address"] = request.email
        if request.phone:
            fields["phone-number"] = request.phone
        if request.address_street:
            fields["address-street-1"] = request.address_street
        if request.address_city:
            fields["address-city"] = request.address_city
        if request.address_country:
            fields["address-country-code"] = request.address_country
        if request.address_postal_code:
            fields["address-postal-code"] = request.address_postal_code
        
        if fields:
            data["data"]["attributes"]["fields"] = fields
        
        try:
            response = await client.post("/inquiries", json=data)
            response.raise_for_status()
            result = response.json()
            
            inquiry_data = result.get("data", {})
            attributes = inquiry_data.get("attributes", {})
            
            # Get session token
            session_response = await client.post(
                f"/inquiries/{inquiry_data['id']}/generate-one-time-link"
            )
            session_response.raise_for_status()
            session_data = session_response.json()
            
            return InquirySession(
                inquiry_id=inquiry_data["id"],
                session_token=session_data.get("meta", {}).get("session-token", ""),
                template_id=self._template_id,
                status=self._map_status(attributes.get("status", "pending")),
                redirect_url=session_data.get("meta", {}).get("one-time-link"),
            )
            
        except Exception as e:
            logger.error(f"Persona create_inquiry failed: {e}")
            raise

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """Get the status of a Persona inquiry."""
        client = await self._get_client()
        
        try:
            response = await client.get(f"/inquiries/{inquiry_id}")
            response.raise_for_status()
            result = response.json()
            
            data = result.get("data", {})
            attributes = data.get("attributes", {})
            
            status = self._map_status(attributes.get("status", "pending"))
            
            return KYCResult(
                status=status,
                verification_id=inquiry_id,
                provider="persona",
                verified_at=self._parse_datetime(attributes.get("completed-at")),
                expires_at=self._parse_datetime(attributes.get("expired-at")),
                reason=attributes.get("decline-reason"),
                metadata={
                    "reference_id": attributes.get("reference-id"),
                    "template_id": attributes.get("inquiry-template-id"),
                    "checks": attributes.get("checks", []),
                },
            )
            
        except Exception as e:
            logger.error(f"Persona get_inquiry_status failed: {e}")
            raise

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """Cancel an ongoing Persona inquiry."""
        client = await self._get_client()
        
        try:
            response = await client.post(
                f"/inquiries/{inquiry_id}/expire",
                json={},
            )
            response.raise_for_status()
            return True
            
        except Exception as e:
            logger.error(f"Persona cancel_inquiry failed: {e}")
            return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Persona webhook signature."""
        if not self._webhook_secret:
            logger.warning("Webhook secret not configured")
            return False
        
        try:
            expected = hmac.new(
                self._webhook_secret.encode(),
                payload,
                hashlib.sha256,
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected)
            
        except Exception as e:
            logger.error(f"Webhook verification failed: {e}")
            return False

    def _map_status(self, persona_status: str) -> KYCStatus:
        """Map Persona status to KYCStatus."""
        status_map = {
            "created": KYCStatus.NOT_STARTED,
            "pending": KYCStatus.PENDING,
            "completed": KYCStatus.APPROVED,
            "approved": KYCStatus.APPROVED,
            "declined": KYCStatus.DECLINED,
            "failed": KYCStatus.DECLINED,
            "expired": KYCStatus.EXPIRED,
            "needs_review": KYCStatus.NEEDS_REVIEW,
        }
        return status_map.get(persona_status, KYCStatus.PENDING)

    def _parse_datetime(self, value: Optional[str]) -> Optional[datetime]:
        """Parse ISO datetime string."""
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None


class MockKYCProvider(KYCProvider):
    """
    Mock KYC provider for development and testing.
    
    Simulates Persona behavior without making real API calls.
    """

    def __init__(self):
        self._inquiries: Dict[str, KYCResult] = {}
        self._counter = 0

    async def create_inquiry(
        self,
        request: VerificationRequest,
    ) -> InquirySession:
        """Create a mock inquiry."""
        self._counter += 1
        inquiry_id = f"inq_mock_{self._counter}"
        
        # Store initial result
        self._inquiries[inquiry_id] = KYCResult(
            status=KYCStatus.PENDING,
            verification_id=inquiry_id,
            provider="mock",
            metadata={"reference_id": request.reference_id},
        )
        
        return InquirySession(
            inquiry_id=inquiry_id,
            session_token=f"session_mock_{self._counter}",
            template_id="mock_template",
            status=KYCStatus.PENDING,
            redirect_url=f"https://mock.kyc.local/verify/{inquiry_id}",
        )

    async def get_inquiry_status(
        self,
        inquiry_id: str,
    ) -> KYCResult:
        """Get mock inquiry status."""
        if inquiry_id not in self._inquiries:
            raise ValueError(f"Unknown inquiry: {inquiry_id}")
        return self._inquiries[inquiry_id]

    async def cancel_inquiry(
        self,
        inquiry_id: str,
    ) -> bool:
        """Cancel mock inquiry."""
        if inquiry_id in self._inquiries:
            self._inquiries[inquiry_id].status = KYCStatus.EXPIRED
            return True
        return False

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Always return True for mock."""
        return True

    def approve_inquiry(self, inquiry_id: str) -> None:
        """Helper method to approve a mock inquiry."""
        if inquiry_id in self._inquiries:
            self._inquiries[inquiry_id] = KYCResult(
                status=KYCStatus.APPROVED,
                verification_id=inquiry_id,
                provider="mock",
                verified_at=datetime.now(timezone.utc),
            )

    def decline_inquiry(self, inquiry_id: str, reason: str = "Test decline") -> None:
        """Helper method to decline a mock inquiry."""
        if inquiry_id in self._inquiries:
            self._inquiries[inquiry_id] = KYCResult(
                status=KYCStatus.DECLINED,
                verification_id=inquiry_id,
                provider="mock",
                reason=reason,
            )


class KYCService:
    """
    High-level KYC service for managing identity verification.
    
    Features:
    - Provider abstraction (Persona or mock)
    - Caching of verification results
    - Webhook handling
    - Status checks for payments
    """

    def __init__(
        self,
        provider: Optional[KYCProvider] = None,
        require_kyc_above: int = 1_000_000,  # $10,000 in minor units
    ):
        """
        Initialize KYC service.
        
        Args:
            provider: KYC provider instance
            require_kyc_above: Amount threshold requiring KYC (in minor units)
        """
        self._provider = provider or MockKYCProvider()
        self._require_kyc_above = require_kyc_above
        self._cache: Dict[str, KYCResult] = {}

    async def create_verification(
        self,
        agent_id: str,
        **kwargs,
    ) -> InquirySession:
        """Create a new verification for an agent."""
        request = VerificationRequest(
            reference_id=agent_id,
            **kwargs,
        )
        return await self._provider.create_inquiry(request)

    async def check_verification(
        self,
        agent_id: str,
        force_refresh: bool = False,
    ) -> KYCResult:
        """
        Check verification status for an agent.

        Returns cached result if available. If the cached result is expired,
        returns a result with EXPIRED status and triggers re-verification flow.

        Args:
            agent_id: The agent to check verification for
            force_refresh: If True, ignores cache and fetches fresh status

        Returns:
            KYCResult with effective_status reflecting expiration state
        """
        # Check cache (unless force_refresh)
        if not force_refresh and agent_id in self._cache:
            cached = self._cache[agent_id]

            # Check if cached result has expired
            if cached.is_expired:
                logger.warning(
                    f"KYC verification expired for agent {agent_id}. "
                    f"Expired at: {cached.expires_at}, "
                    f"Original verification: {cached.verification_id}"
                )

                # Return expired status (keeps original data for audit)
                return KYCResult(
                    status=KYCStatus.EXPIRED,
                    verification_id=cached.verification_id,
                    provider=cached.provider,
                    verified_at=cached.verified_at,
                    expires_at=cached.expires_at,
                    reason="Verification expired - re-verification required",
                    metadata={
                        **cached.metadata,
                        "expired": True,
                        "original_status": str(cached.status),
                    },
                )

            # Return cached result if still valid
            if cached.is_verified:
                return cached

            # Cached but not verified (declined, pending, etc.) - return as-is
            return cached

        # Look up from database
        try:
            from sardis_v2_core.database import Database
            row = await Database.fetchrow(
                """
                SELECT inquiry_id, provider, status, verified_at, expires_at, reason, metadata
                FROM kyc_verifications
                WHERE agent_id = $1
                ORDER BY created_at DESC LIMIT 1
                """,
                agent_id,
            )
            if row:
                import json
                meta = row["metadata"]
                if isinstance(meta, str):
                    meta = json.loads(meta)
                result = KYCResult(
                    status=KYCStatus(row["status"]),
                    verification_id=row["inquiry_id"],
                    provider=row["provider"] or "persona",
                    verified_at=row["verified_at"],
                    expires_at=row["expires_at"],
                    reason=row["reason"],
                    metadata=meta or {},
                )
                # Populate cache for future lookups
                self._cache[agent_id] = result
                return result
        except Exception as e:
            logger.warning(f"DB lookup for KYC failed, returning not_started: {e}")

        return KYCResult(
            status=KYCStatus.NOT_STARTED,
            verification_id="",
            provider=self._provider.__class__.__name__,
        )

    async def needs_reverification(self, agent_id: str) -> bool:
        """
        Check if an agent needs re-verification due to expiration.

        Returns True if:
        - Agent has an expired verification
        - Agent has never been verified
        """
        result = await self.check_verification(agent_id)
        return result.effective_status in (KYCStatus.EXPIRED, KYCStatus.NOT_STARTED)

    async def get_expiration_warning(
        self,
        agent_id: str,
        warning_days: int = 30,
    ) -> Optional[str]:
        """
        Check if verification is expiring soon and return a warning message.

        Args:
            agent_id: The agent to check
            warning_days: Days before expiration to start warning

        Returns:
            Warning message if expiring soon, None otherwise
        """
        if agent_id not in self._cache:
            return None

        cached = self._cache[agent_id]
        remaining = cached.time_until_expiration()

        if remaining is None:
            return None

        if remaining <= 0:
            return f"KYC verification has expired. Re-verification required."

        days_remaining = remaining / 86400  # seconds to days

        if days_remaining <= warning_days:
            return (
                f"KYC verification expires in {int(days_remaining)} days. "
                f"Please complete re-verification before {cached.expires_at}."
            )

        return None

    async def is_kyc_required(
        self,
        agent_id: str,
        amount_minor: int,
    ) -> bool:
        """
        Check if KYC is required for a transaction.
        
        KYC is required if:
        - Amount exceeds threshold
        - Agent is not verified
        """
        if amount_minor < self._require_kyc_above:
            return False
        
        result = await self.check_verification(agent_id)
        return not result.is_verified

    async def handle_webhook(
        self,
        event_type: str,
        payload: Dict[str, Any],
    ) -> None:
        """Handle KYC webhook events."""
        if event_type == "inquiry.completed":
            inquiry_id = payload.get("data", {}).get("id")
            if inquiry_id:
                result = await self._provider.get_inquiry_status(inquiry_id)
                reference_id = result.metadata.get("reference_id")
                if reference_id:
                    self._cache[reference_id] = result
                    logger.info(f"KYC completed for {reference_id}: {result.status}")
                    # Persist to database
                    try:
                        import json as _json
                        from sardis_v2_core.database import Database
                        await Database.execute(
                            """
                            INSERT INTO kyc_verifications
                                (agent_id, inquiry_id, provider, status, verified_at, expires_at, reason, metadata)
                            VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                            ON CONFLICT (inquiry_id) DO UPDATE SET
                                status = EXCLUDED.status, verified_at = EXCLUDED.verified_at,
                                updated_at = NOW()
                            """,
                            reference_id,
                            inquiry_id,
                            result.provider,
                            result.status.value,
                            result.verified_at,
                            result.expires_at,
                            result.reason,
                            _json.dumps(result.metadata, default=str),
                        )
                    except Exception as e:
                        logger.warning(f"Failed to persist KYC result: {e}")

        elif event_type == "inquiry.expired":
            inquiry_id = payload.get("data", {}).get("id")
            if inquiry_id:
                result = await self._provider.get_inquiry_status(inquiry_id)
                reference_id = result.metadata.get("reference_id")
                if reference_id and reference_id in self._cache:
                    del self._cache[reference_id]
                    logger.info(f"KYC expired for {reference_id}")


def create_kyc_service(
    api_key: Optional[str] = None,
    template_id: Optional[str] = None,
    webhook_secret: Optional[str] = None,
    environment: str = "sandbox",
) -> KYCService:
    """
    Factory function to create KYC service.

    Uses MockKYCProvider if no API key is provided.

    Args:
        api_key: Persona API key
        template_id: Persona inquiry template ID
        webhook_secret: Secret for webhook signature verification (REQUIRED for production)
        environment: 'sandbox' or 'production'

    SECURITY: In production, webhook_secret MUST be configured.
    Webhooks without valid signatures will be rejected.
    """
    import os

    # Get webhook secret from parameter or environment
    webhook_secret = webhook_secret or os.getenv("PERSONA_WEBHOOK_SECRET")

    if api_key and template_id:
        # Production warning if webhook secret not configured
        if environment == "production" and not webhook_secret:
            logger.error(
                "SECURITY WARNING: Production KYC service created without webhook_secret. "
                "Webhook signature verification will fail. Set PERSONA_WEBHOOK_SECRET."
            )

        provider = PersonaKYCProvider(
            api_key=api_key,
            template_id=template_id,
            webhook_secret=webhook_secret,
            environment=environment,
        )
    else:
        logger.warning("No Persona API key provided, using mock provider")
        provider = MockKYCProvider()

    return KYCService(provider=provider)


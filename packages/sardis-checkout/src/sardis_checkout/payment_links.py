"""
Payment link management for checkout sessions.

This module provides functionality to create, manage, and track payment links
that can be shared with customers for completing payments.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
import string
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
import uuid

from sardis_checkout.models import (
    PaymentLink,
    PaymentStatus,
    DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS,
)

logger = logging.getLogger(__name__)


class PaymentLinkError(Exception):
    """Base exception for payment link errors."""
    pass


class PaymentLinkNotFound(PaymentLinkError):
    """Raised when a payment link is not found."""
    pass


class PaymentLinkExpired(PaymentLinkError):
    """Raised when a payment link has expired."""
    pass


class PaymentLinkAlreadyUsed(PaymentLinkError):
    """Raised when a payment link has already been used."""
    pass


class PaymentLinkRevoked(PaymentLinkError):
    """Raised when a payment link has been revoked."""
    pass


class PaymentLinkStore(ABC):
    """Abstract interface for payment link storage."""

    @abstractmethod
    async def create(self, link: PaymentLink) -> PaymentLink:
        """Create a new payment link."""
        pass

    @abstractmethod
    async def get(self, link_id: str) -> Optional[PaymentLink]:
        """Get a payment link by ID."""
        pass

    @abstractmethod
    async def get_by_checkout(self, checkout_id: str) -> List[PaymentLink]:
        """Get all payment links for a checkout."""
        pass

    @abstractmethod
    async def update(self, link: PaymentLink) -> PaymentLink:
        """Update a payment link."""
        pass

    @abstractmethod
    async def delete(self, link_id: str) -> bool:
        """Delete a payment link."""
        pass

    @abstractmethod
    async def find_by_short_code(self, short_code: str) -> Optional[PaymentLink]:
        """Find a payment link by its short code."""
        pass

    @abstractmethod
    async def cleanup_expired(self) -> int:
        """Remove expired payment links. Returns count of removed links."""
        pass


class InMemoryPaymentLinkStore(PaymentLinkStore):
    """
    In-memory payment link store for development and testing.

    Note: This store is not suitable for production use.
    Use a persistent store like Redis or a database.
    """

    def __init__(self):
        self._links: Dict[str, PaymentLink] = {}
        self._short_codes: Dict[str, str] = {}  # short_code -> link_id

    async def create(self, link: PaymentLink) -> PaymentLink:
        self._links[link.link_id] = link
        if link.short_url:
            # Extract short code from URL
            short_code = link.short_url.split("/")[-1]
            self._short_codes[short_code] = link.link_id
        return link

    async def get(self, link_id: str) -> Optional[PaymentLink]:
        return self._links.get(link_id)

    async def get_by_checkout(self, checkout_id: str) -> List[PaymentLink]:
        return [
            link for link in self._links.values()
            if link.checkout_id == checkout_id
        ]

    async def update(self, link: PaymentLink) -> PaymentLink:
        if link.link_id in self._links:
            self._links[link.link_id] = link
        return link

    async def delete(self, link_id: str) -> bool:
        if link_id in self._links:
            link = self._links.pop(link_id)
            if link.short_url:
                short_code = link.short_url.split("/")[-1]
                self._short_codes.pop(short_code, None)
            return True
        return False

    async def find_by_short_code(self, short_code: str) -> Optional[PaymentLink]:
        link_id = self._short_codes.get(short_code)
        if link_id:
            return self._links.get(link_id)
        return None

    async def cleanup_expired(self) -> int:
        now = datetime.utcnow()
        expired = [
            link_id for link_id, link in self._links.items()
            if link.expires_at < now
        ]
        for link_id in expired:
            await self.delete(link_id)
        return len(expired)


class PaymentLinkManager:
    """
    Manages payment links for checkout sessions.

    Features:
    - Create shareable payment links
    - Short URL generation
    - Expiration management
    - Usage tracking and limits
    - Link revocation
    """

    def __init__(
        self,
        store: PaymentLinkStore,
        base_url: str = "https://pay.example.com",
        short_url_base: str = "https://p.example.com",
        default_expiration_hours: int = DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS,
        short_code_length: int = 8,
    ):
        self.store = store
        self.base_url = base_url.rstrip("/")
        self.short_url_base = short_url_base.rstrip("/")
        self.default_expiration_hours = default_expiration_hours
        self.short_code_length = short_code_length

    def _generate_short_code(self) -> str:
        """Generate a random short code for URLs."""
        alphabet = string.ascii_letters + string.digits
        return "".join(secrets.choice(alphabet) for _ in range(self.short_code_length))

    def _generate_link_url(self, link_id: str) -> str:
        """Generate the full payment link URL."""
        return f"{self.base_url}/pay/{link_id}"

    def _generate_short_url(self, short_code: str) -> str:
        """Generate a short URL for the payment link."""
        return f"{self.short_url_base}/{short_code}"

    async def create_payment_link(
        self,
        checkout_id: str,
        amount: Decimal,
        currency: str,
        description: Optional[str] = None,
        expiration_hours: Optional[int] = None,
        max_uses: int = 1,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> PaymentLink:
        """
        Create a new payment link for a checkout session.

        Args:
            checkout_id: ID of the checkout session
            amount: Payment amount
            currency: Payment currency
            description: Optional description
            expiration_hours: Hours until link expires (default: 24)
            max_uses: Maximum number of times link can be used (default: 1)
            metadata: Additional metadata

        Returns:
            The created PaymentLink
        """
        exp_hours = expiration_hours or self.default_expiration_hours
        short_code = self._generate_short_code()

        link = PaymentLink(
            link_id=str(uuid.uuid4()),
            checkout_id=checkout_id,
            url=self._generate_link_url(checkout_id),
            short_url=self._generate_short_url(short_code),
            status="active",
            expires_at=datetime.utcnow() + timedelta(hours=exp_hours),
            max_uses=max_uses,
            use_count=0,
            amount=amount,
            currency=currency,
            description=description,
            metadata=metadata or {},
        )

        await self.store.create(link)
        logger.info(
            f"Created payment link {link.link_id} for checkout {checkout_id}"
        )

        return link

    async def get_payment_link(self, link_id: str) -> PaymentLink:
        """
        Get a payment link by ID.

        Raises:
            PaymentLinkNotFound: If the link doesn't exist
        """
        link = await self.store.get(link_id)
        if not link:
            raise PaymentLinkNotFound(f"Payment link {link_id} not found")
        return link

    async def get_checkout_links(self, checkout_id: str) -> List[PaymentLink]:
        """Get all payment links for a checkout session."""
        return await self.store.get_by_checkout(checkout_id)

    async def resolve_short_code(self, short_code: str) -> PaymentLink:
        """
        Resolve a short code to its payment link.

        Raises:
            PaymentLinkNotFound: If the short code doesn't exist
        """
        link = await self.store.find_by_short_code(short_code)
        if not link:
            raise PaymentLinkNotFound(f"Payment link with code {short_code} not found")
        return link

    async def validate_link(self, link_id: str) -> PaymentLink:
        """
        Validate a payment link for use.

        Checks expiration, status, and usage limits.

        Raises:
            PaymentLinkNotFound: If the link doesn't exist
            PaymentLinkExpired: If the link has expired
            PaymentLinkAlreadyUsed: If the link has reached its usage limit
            PaymentLinkRevoked: If the link has been revoked
        """
        link = await self.get_payment_link(link_id)

        # Check expiration
        if link.expires_at < datetime.utcnow():
            link.status = "expired"
            await self.store.update(link)
            raise PaymentLinkExpired(f"Payment link {link_id} has expired")

        # Check status
        if link.status == "revoked":
            raise PaymentLinkRevoked(f"Payment link {link_id} has been revoked")

        if link.status == "used":
            raise PaymentLinkAlreadyUsed(f"Payment link {link_id} has already been used")

        if link.status == "expired":
            raise PaymentLinkExpired(f"Payment link {link_id} has expired")

        # Check usage limit
        if link.use_count >= link.max_uses:
            link.status = "used"
            await self.store.update(link)
            raise PaymentLinkAlreadyUsed(
                f"Payment link {link_id} has reached its usage limit"
            )

        return link

    async def use_link(self, link_id: str) -> PaymentLink:
        """
        Mark a payment link as used.

        This should be called when a payment is initiated from the link.
        """
        link = await self.validate_link(link_id)

        link.use_count += 1
        link.used_at = datetime.utcnow()

        # Mark as used if limit reached
        if link.use_count >= link.max_uses:
            link.status = "used"

        await self.store.update(link)
        logger.info(f"Payment link {link_id} used (count: {link.use_count})")

        return link

    async def revoke_link(self, link_id: str) -> PaymentLink:
        """
        Revoke a payment link, preventing further use.
        """
        link = await self.get_payment_link(link_id)
        link.status = "revoked"
        await self.store.update(link)
        logger.info(f"Payment link {link_id} revoked")
        return link

    async def extend_expiration(
        self,
        link_id: str,
        additional_hours: int,
    ) -> PaymentLink:
        """
        Extend the expiration time of a payment link.
        """
        link = await self.get_payment_link(link_id)

        if link.status in ("used", "revoked"):
            raise PaymentLinkError(
                f"Cannot extend link {link_id} with status {link.status}"
            )

        # If already expired, extend from now; otherwise extend from current expiration
        base_time = max(link.expires_at, datetime.utcnow())
        link.expires_at = base_time + timedelta(hours=additional_hours)

        # Reactivate if was expired
        if link.status == "expired":
            link.status = "active"

        await self.store.update(link)
        logger.info(
            f"Extended payment link {link_id} expiration to {link.expires_at}"
        )

        return link

    async def update_max_uses(
        self,
        link_id: str,
        max_uses: int,
    ) -> PaymentLink:
        """
        Update the maximum number of uses for a payment link.
        """
        link = await self.get_payment_link(link_id)

        if max_uses < link.use_count:
            raise PaymentLinkError(
                f"Cannot set max_uses ({max_uses}) below current use count ({link.use_count})"
            )

        link.max_uses = max_uses

        # Reactivate if was marked used but now has capacity
        if link.status == "used" and link.use_count < link.max_uses:
            link.status = "active"

        await self.store.update(link)
        return link

    async def get_link_status(self, link_id: str) -> Dict[str, Any]:
        """
        Get the current status of a payment link.

        Returns a dict with status information.
        """
        link = await self.get_payment_link(link_id)

        now = datetime.utcnow()
        is_expired = link.expires_at < now
        is_usable = (
            link.status == "active"
            and not is_expired
            and link.use_count < link.max_uses
        )

        return {
            "link_id": link.link_id,
            "checkout_id": link.checkout_id,
            "status": link.status,
            "is_expired": is_expired,
            "is_usable": is_usable,
            "use_count": link.use_count,
            "max_uses": link.max_uses,
            "uses_remaining": max(0, link.max_uses - link.use_count),
            "created_at": link.created_at,
            "expires_at": link.expires_at,
            "used_at": link.used_at,
            "seconds_until_expiry": max(
                0,
                int((link.expires_at - now).total_seconds())
            ) if not is_expired else 0,
        }

    async def cleanup_expired_links(self) -> int:
        """
        Clean up expired payment links.

        Returns the number of links cleaned up.
        """
        count = await self.store.cleanup_expired()
        if count > 0:
            logger.info(f"Cleaned up {count} expired payment links")
        return count

    async def get_active_links_count(self, checkout_id: str) -> int:
        """Get count of active payment links for a checkout."""
        links = await self.get_checkout_links(checkout_id)
        now = datetime.utcnow()
        return sum(
            1 for link in links
            if link.status == "active" and link.expires_at > now
        )

"""Laso Finance virtual card service via MPP.

Laso Finance provides non-reloadable Visa prepaid virtual cards through the
Locus (YC F25) MPP proxy. Cards range from $5-$1,000, US-only (IP-locked).

Architecture:
    AI Agent → Sardis → Locus x402 Proxy → Laso Finance API → Visa Prepaid Card

MPP Service Entry:
    ID: laso
    URL: https://beta-api.paywithlocus.com/api/laso-mpp
    Realm: laso.mpp.paywithlocus.com
    Intent: charge
    Payment: USDC on Tempo

Endpoints:
    POST /api/laso-mpp/get-card      — Order a virtual card ($5-$1,000)
    POST /api/laso-mpp/get-card-data — Get card details (free)
    POST /api/laso-mpp/send-payment  — Venmo/PayPal payment ($5-$1,000)
    POST /api/laso-mpp/get-account-balance — Check balance (free)
    POST /api/laso-mpp/withdraw      — Initiate withdrawal
    POST /api/laso-mpp/refresh       — Refresh session token (free)

Restrictions:
    - US-only (IP-locked)
    - Non-reloadable cards
    - Max $1,000 per card, $6,000 daily (6 cards), $10,000 personal daily
    - No 3D Secure support
    - Card amount must match checkout total exactly
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

LASO_MPP_BASE = "https://beta-api.paywithlocus.com/api/laso-mpp"
LASO_AUTH_COST_USDC = Decimal("0.001")


@dataclass
class LasoCard:
    """Virtual card issued by Laso Finance."""
    card_id: str
    card_number: str
    cvv: str
    expiry: str
    amount: Decimal
    currency: str
    status: str
    card_type: str = "single_use"


@dataclass
class LasoPayment:
    """Payment sent via Laso (Venmo/PayPal)."""
    payment_id: str
    amount: Decimal
    method: str  # "venmo" or "paypal"
    recipient: str
    status: str


class LasoMPPService:
    """Client for Laso Finance virtual cards via MPP/Locus proxy.

    Uses the x402 payment protocol — authenticates with a micro-payment
    ($0.001 USDC), then uses session tokens for subsequent API calls.
    """

    def __init__(
        self,
        base_url: str = LASO_MPP_BASE,
        session_token: str | None = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.timeout = timeout

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
    ) -> dict:
        """Make an authenticated request to the Laso MPP endpoint."""
        url = f"{self.base_url}{path}"
        headers: dict[str, str] = {}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(method, url, json=json_data, headers=headers)

            # Handle x402 payment challenge
            if resp.status_code == 402:
                logger.info("Laso MPP: received 402 challenge, payment required")
                # In production, this would be handled by the MPP client SDK
                # which automatically fulfills the payment and retries
                raise LasoPaymentRequired(
                    challenge=resp.headers.get("WWW-Authenticate", ""),
                    amount=LASO_AUTH_COST_USDC,
                )

            resp.raise_for_status()
            return resp.json()

    async def issue_card(
        self,
        amount: Decimal,
        currency: str = "USD",
    ) -> LasoCard:
        """Issue a virtual prepaid card via Laso Finance.

        Args:
            amount: Card amount ($5-$1,000). Must match checkout total exactly.
            currency: Card currency (USD only currently).

        Returns:
            LasoCard with card number, CVV, and expiry.

        Raises:
            ValueError: If amount is out of range.
            LasoPaymentRequired: If x402 auth payment needed.
        """
        if amount < 5 or amount > 1000:
            raise ValueError(f"Card amount must be between $5 and $1,000 (got ${amount})")

        logger.info("Laso: issuing %s %s virtual card", amount, currency)

        data = await self._request("POST", "/get-card", json_data={
            "amount": str(amount),
            "currency": currency,
            "type": "single_use",
        })

        card_id = data.get("card_id") or data.get("id", "")

        # Card may need polling — typically ready in 7-10 seconds
        if data.get("status") == "processing" and card_id:
            logger.info("Laso: card %s is processing, polling for readiness...", card_id)
            data = await self._poll_card_ready(card_id, max_attempts=5, interval=3.0)

        return LasoCard(
            card_id=card_id,
            card_number=data.get("card_number", ""),
            cvv=data.get("cvv", ""),
            expiry=data.get("expiry", ""),
            amount=Decimal(str(data.get("amount", amount))),
            currency=data.get("currency", currency),
            status=data.get("status", "processing"),
        )

    async def _poll_card_ready(
        self,
        card_id: str,
        max_attempts: int = 5,
        interval: float = 3.0,
    ) -> dict:
        """Poll until card is ready or max attempts reached."""
        for attempt in range(1, max_attempts + 1):
            await asyncio.sleep(interval)
            data = await self._request("POST", "/get-card-data", json_data={
                "card_id": card_id,
            })
            status = data.get("status", "processing")
            if status != "processing":
                logger.info("Laso: card %s ready after %d polls (status=%s)", card_id, attempt, status)
                return data
            logger.debug("Laso: card %s still processing (attempt %d/%d)", card_id, attempt, max_attempts)
        logger.warning("Laso: card %s still processing after %d polls", card_id, max_attempts)
        return data  # Return last response even if still processing

    async def get_card_data(self, card_id: str) -> dict:
        """Get card details (free endpoint, no payment required)."""
        return await self._request("POST", "/get-card-data", json_data={
            "card_id": card_id,
        })

    async def get_balance(self) -> dict:
        """Get account balance (free endpoint)."""
        return await self._request("POST", "/get-account-balance")

    async def send_payment(
        self,
        amount: Decimal,
        method: str,
        recipient: str,
    ) -> LasoPayment:
        """Send payment via Venmo (by phone) or PayPal (by email).

        Args:
            amount: Payment amount ($5-$1,000).
            method: "venmo" or "paypal".
            recipient: Phone number (Venmo) or email (PayPal).

        Note: Requires human confirmation before processing.
        """
        if amount < 5 or amount > 1000:
            raise ValueError(f"Payment amount must be between $5 and $1,000 (got ${amount})")
        if method not in ("venmo", "paypal"):
            raise ValueError(f"Method must be 'venmo' or 'paypal' (got '{method}')")

        data = await self._request("POST", "/send-payment", json_data={
            "amount": str(amount),
            "method": method,
            "recipient": recipient,
        })

        return LasoPayment(
            payment_id=data.get("payment_id") or data.get("id", ""),
            amount=Decimal(str(data.get("amount", amount))),
            method=method,
            recipient=recipient,
            status=data.get("status", "pending_confirmation"),
        )

    async def refresh_session(self) -> str:
        """Refresh session token (free endpoint)."""
        data = await self._request("POST", "/refresh")
        self.session_token = data.get("token", self.session_token)
        return self.session_token or ""


class LasoPaymentRequired(Exception):
    """Raised when Laso MPP endpoint returns 402 requiring x402 payment."""

    def __init__(self, challenge: str, amount: Decimal):
        self.challenge = challenge
        self.amount = amount
        super().__init__(f"MPP payment required: {amount} USDC (challenge: {challenge[:50]}...)")

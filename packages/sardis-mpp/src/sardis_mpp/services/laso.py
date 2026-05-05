"""Laso Finance virtual card service via MPP.

Laso Finance provides non-reloadable Visa prepaid virtual cards through the
Locus (YC F25) MPP proxy. Cards range from $5-$1,000, US-only (IP-locked).

Architecture:
    AI Agent → Sardis policy check → SardisMPPClient (auto-handles 402)
    → Laso x402 challenge → USDC micro-payment → session token → card issued

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

No API key needed — authentication is via x402 USDC micro-payment ($0.001).
"""

from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger(__name__)

LASO_MPP_BASE = "https://beta-api.paywithlocus.com/api/laso-mpp"
LASO_AUTH_COST_USDC = Decimal("0.001")

# Limits from Laso docs
LASO_MIN_CARD_AMOUNT = Decimal("5")
LASO_MAX_CARD_AMOUNT = Decimal("1000")
LASO_MAX_DAILY_CARDS = 6
LASO_MAX_DAILY_AMOUNT = Decimal("6000")
LASO_MAX_PERSONAL_DAILY = Decimal("10000")


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
    billing_address: dict[str, str] = field(default_factory=dict)
    created_at: str = ""

    def masked_number(self) -> str:
        """Return card number with only last 4 digits visible."""
        if len(self.card_number) >= 4:
            return "*" * (len(self.card_number) - 4) + self.card_number[-4:]
        return self.card_number

    @property
    def is_ready(self) -> bool:
        return self.status in ("ready", "active", "funded")


@dataclass
class LasoPayment:
    """Payment sent via Laso (Venmo/PayPal)."""
    payment_id: str
    amount: Decimal
    method: str  # "venmo" or "paypal"
    recipient: str
    status: str


@dataclass
class LasoBalance:
    """Account balance from Laso."""
    available: Decimal
    pending: Decimal
    currency: str = "USD"


class LasoMPPService:
    """Client for Laso Finance virtual cards via MPP.

    Uses SardisMPPClient to automatically handle x402 challenges:
    1. First request -> Laso returns 402 Payment Required
    2. SardisMPPClient's SardisPolicyTransport intercepts the 402
    3. Transport signs USDC micro-payment on Tempo via configured method
    4. Transport retries with payment credential -> gets response
    5. Session token extracted from response for subsequent requests

    The critical detail: requests MUST go through SardisMPPClient.post() /
    SardisMPPClient.get() (not _http directly) so the SardisPolicyTransport
    can intercept 402 responses and fulfill x402 challenges.

    No API key needed — just a funded Tempo wallet.
    """

    def __init__(
        self,
        base_url: str = LASO_MPP_BASE,
        session_token: str | None = None,
        timeout: float = 30.0,
        tempo_private_key: str | None = None,
        policy_checker=None,
    ):
        self.base_url = base_url.rstrip("/")
        self.session_token = session_token
        self.timeout = timeout
        self._tempo_key = tempo_private_key
        self._policy_checker = policy_checker
        self._mpp_client = None
        self._cards_issued_today: int = 0
        self._daily_amount: Decimal = Decimal("0")
        self._last_reset: str = ""

    def _check_daily_limits(self, amount: Decimal) -> None:
        """Enforce Laso daily issuance limits before making API call."""
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if self._last_reset != today:
            self._cards_issued_today = 0
            self._daily_amount = Decimal("0")
            self._last_reset = today

        if self._cards_issued_today >= LASO_MAX_DAILY_CARDS:
            raise LasoLimitExceeded(
                f"Daily card limit reached ({LASO_MAX_DAILY_CARDS} cards/day)"
            )
        if self._daily_amount + amount > LASO_MAX_DAILY_AMOUNT:
            raise LasoLimitExceeded(
                f"Daily amount limit exceeded (${self._daily_amount} + ${amount} > ${LASO_MAX_DAILY_AMOUNT})"
            )

    async def _get_mpp_client(self):
        """Lazy-init SardisMPPClient with Tempo payment method."""
        if self._mpp_client is not None:
            return self._mpp_client

        # Get signing key
        key = self._tempo_key or os.getenv("SARDIS_TEMPO_SIGNER_KEY") or os.getenv("SARDIS_EOA_PRIVATE_KEY")
        if not key:
            raise RuntimeError(
                "No signing key for Laso MPP. Set SARDIS_TEMPO_SIGNER_KEY or "
                "SARDIS_EOA_PRIVATE_KEY to enable x402 authentication."
            )

        try:
            from mpp.methods.tempo import ChargeIntent, TempoAccount, tempo

            account = TempoAccount.from_key(key)
            tempo_method = tempo(
                account=account,
                intents={"charge": ChargeIntent()},
            )

            from sardis_mpp.client import SardisMPPClient
            self._mpp_client = SardisMPPClient(
                methods=[tempo_method],
                policy_checker=self._policy_checker,
            )
            logger.info("Laso MPP client initialized with Tempo wallet %s", account.address)
            return self._mpp_client

        except ImportError:
            logger.warning(
                "pympp not installed — falling back to raw httpx (402 will not be handled). "
                "Install: pip install pympp"
            )
            return None

    async def _request(
        self,
        method: str,
        path: str,
        json_data: dict | None = None,
    ) -> dict:
        """Make a request to Laso MPP, auto-handling x402 payment challenges.

        Uses SardisMPPClient.post()/get() so the SardisPolicyTransport
        intercepts 402 responses and fulfills x402 challenges automatically.
        Going through _http directly would bypass the transport layer.
        """
        url = f"{self.base_url}{path}"

        # Try with SardisMPPClient (auto-handles 402 via transport)
        mpp_client = await self._get_mpp_client()
        if mpp_client:
            headers: dict[str, str] = {}
            if self.session_token:
                headers["Authorization"] = f"Bearer {self.session_token}"

            # Use mpp_client.post()/get() — NOT mpp_client._http —
            # so SardisPolicyTransport can intercept 402 and auto-pay.
            if method.upper() == "POST":
                resp = await mpp_client.post(url, json=json_data, headers=headers)
            else:
                resp = await mpp_client.get(url, headers=headers)

            # Extract session token from response if present
            data = resp.json()
            if "token" in data and not self.session_token:
                self.session_token = data["token"]
                logger.info("Laso session token acquired via x402 payment")

            if resp.status_code == 402:
                # If we still get 402 after transport handling, the payment
                # method may not have matched the challenge. Surface clearly.
                challenge = resp.headers.get("WWW-Authenticate", "")
                raise LasoPaymentRequired(
                    challenge=challenge,
                    amount=LASO_AUTH_COST_USDC,
                )

            resp.raise_for_status()
            return data

        # Fallback: raw httpx (will fail on 402)
        import httpx
        headers = {}
        if self.session_token:
            headers["Authorization"] = f"Bearer {self.session_token}"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.request(method, url, json=json_data, headers=headers)

            if resp.status_code == 402:
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
        card_type: str = "single_use",
    ) -> LasoCard:
        """Issue a virtual prepaid card via Laso Finance.

        The x402 authentication ($0.001 USDC) is handled automatically
        by SardisMPPClient's SardisPolicyTransport. The card amount
        ($5-$1,000) is charged separately during the card creation flow.

        Args:
            amount: Card amount ($5-$1,000). Must match checkout total exactly.
            currency: Card currency (USD only currently).
            card_type: "single_use" or "multi_use".

        Returns:
            LasoCard with card number, CVV, expiry, and billing address.
        """
        if amount < LASO_MIN_CARD_AMOUNT or amount > LASO_MAX_CARD_AMOUNT:
            raise ValueError(
                f"Card amount must be between ${LASO_MIN_CARD_AMOUNT} and "
                f"${LASO_MAX_CARD_AMOUNT} (got ${amount})"
            )
        if card_type not in ("single_use", "multi_use"):
            raise ValueError(f"card_type must be 'single_use' or 'multi_use' (got '{card_type}')")

        self._check_daily_limits(amount)

        logger.info("Laso: issuing %s %s %s virtual card", amount, currency, card_type)

        data = await self._request("POST", "/get-card", json_data={
            "amount": str(amount),
            "currency": currency,
            "type": card_type,
        })

        card_id = data.get("card_id") or data.get("id", "")

        # Card may need polling — typically ready in 7-10 seconds
        if data.get("status") == "processing" and card_id:
            logger.info("Laso: card %s is processing, polling for readiness...", card_id)
            data = await self._poll_card_ready(card_id, max_attempts=5, interval=3.0)

        # Track daily limits
        self._cards_issued_today += 1
        self._daily_amount += amount

        return LasoCard(
            card_id=card_id,
            card_number=data.get("card_number", ""),
            cvv=data.get("cvv", ""),
            expiry=data.get("expiry", ""),
            amount=Decimal(str(data.get("amount", amount))),
            currency=data.get("currency", currency),
            status=data.get("status", "processing"),
            card_type=card_type,
            billing_address=data.get("billing_address", {}),
            created_at=data.get("created_at", datetime.now(UTC).isoformat()),
        )

    async def _poll_card_ready(
        self,
        card_id: str,
        max_attempts: int = 5,
        interval: float = 3.0,
    ) -> dict:
        """Poll until card is ready or max attempts reached."""
        data: dict[str, Any] = {}
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
        return data

    async def get_card_data(self, card_id: str) -> LasoCard:
        """Get card details (free endpoint, no payment required).

        Returns a full LasoCard with number, CVV, expiry, and billing address.
        """
        data = await self._request("POST", "/get-card-data", json_data={
            "card_id": card_id,
        })
        return LasoCard(
            card_id=card_id,
            card_number=data.get("card_number", ""),
            cvv=data.get("cvv", ""),
            expiry=data.get("expiry", ""),
            amount=Decimal(str(data.get("amount", "0"))),
            currency=data.get("currency", "USD"),
            status=data.get("status", "unknown"),
            card_type=data.get("type", "single_use"),
            billing_address=data.get("billing_address", {}),
            created_at=data.get("created_at", ""),
        )

    async def get_card_data_raw(self, card_id: str) -> dict:
        """Get raw card details dict (free endpoint)."""
        return await self._request("POST", "/get-card-data", json_data={
            "card_id": card_id,
        })

    async def get_balance(self) -> LasoBalance:
        """Get account balance (free endpoint)."""
        data = await self._request("POST", "/get-account-balance")
        return LasoBalance(
            available=Decimal(str(data.get("available", data.get("balance", "0")))),
            pending=Decimal(str(data.get("pending", "0"))),
            currency=data.get("currency", "USD"),
        )

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

    async def close(self) -> None:
        """Close the underlying MPP client."""
        if self._mpp_client:
            await self._mpp_client.close()
            self._mpp_client = None


class LasoPaymentRequired(Exception):
    """Raised when Laso MPP endpoint returns 402 requiring x402 payment.

    This should NOT happen when using SardisMPPClient — it auto-handles 402.
    Only raised when:
    - pympp is not installed (raw httpx fallback path)
    - The transport's payment method doesn't match the challenge
    """

    def __init__(self, challenge: str, amount: Decimal):
        self.challenge = challenge
        self.amount = amount
        super().__init__(f"MPP payment required: {amount} USDC (challenge: {challenge[:50]}...)")


class LasoLimitExceeded(Exception):
    """Raised when Laso daily issuance limits would be exceeded.

    Limits:
    - Max 6 cards per day ($6,000 total)
    - Max $10,000 personal daily
    """

    pass


class LasoCardNotReady(Exception):
    """Raised when a card is still processing after max poll attempts."""

    def __init__(self, card_id: str, status: str):
        self.card_id = card_id
        self.status = status
        super().__init__(f"Card {card_id} still in '{status}' state after polling")

"""MPP (Machine Payments Protocol) client with Sardis policy enforcement.

Handles HTTP 402 challenges from MPP-enabled services.
Supports one-time payments, pay-as-you-go sessions, and streamed payments.

Protocol flow:
    1. Agent requests a resource
    2. Service returns 402 with MPP challenge (payment details)
    3. Sardis policy engine evaluates the payment
    4. If approved: sign and submit payment, retry with credential
    5. If denied: raise MPPPaymentDenied (no funds moved)
    6. Audit trail records the decision

References:
    - https://mpp.dev
    - https://docs.stripe.com/payments/machine/mpp
    - https://tempo.xyz/blog/mainnet
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Callable, Awaitable

import httpx

logger = logging.getLogger(__name__)


class MPPPaymentDenied(Exception):
    """Raised when Sardis policy blocks an MPP payment."""


@dataclass
class MPPChallenge:
    """Parsed MPP 402 challenge from a service."""

    payment_method: str  # "tempo", "stripe", "lightning", "card"
    amount: Decimal
    currency: str  # "USD", "USDC", etc.
    recipient: str  # Address or payment endpoint
    network: str  # "tempo", "base", etc.
    session_id: str | None = None
    memo: str | None = None
    expires_at: str | None = None
    raw: dict = field(default_factory=dict)

    @classmethod
    def from_response(cls, response: httpx.Response) -> MPPChallenge:
        """Parse an MPP challenge from a 402 response.

        MPP challenges come via:
        - WWW-Authenticate header with scheme "MPP"
        - JSON body with payment details
        """
        body = {}
        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            pass

        # Parse from body (primary)
        payment = body.get("payment", body)
        amount_raw = payment.get("amount", payment.get("price", "0"))

        return cls(
            payment_method=str(payment.get("method", payment.get("payment_method", "tempo"))),
            amount=Decimal(str(amount_raw)),
            currency=str(payment.get("currency", payment.get("token", "USD"))),
            recipient=str(payment.get("recipient", payment.get("address", payment.get("to", "")))),
            network=str(payment.get("network", payment.get("chain", "tempo"))),
            session_id=payment.get("session_id"),
            memo=payment.get("memo"),
            expires_at=payment.get("expires_at"),
            raw=body,
        )


@dataclass
class MPPCredential:
    """Payment credential to attach to retry request."""

    tx_hash: str
    network: str
    payment_method: str
    session_id: str | None = None

    def to_header(self) -> str:
        """Format as Authorization header value."""
        parts = [f"txHash={self.tx_hash}", f"network={self.network}"]
        if self.session_id:
            parts.append(f"sessionId={self.session_id}")
        return f"MPP {','.join(parts)}"


@dataclass
class MPPSession:
    """Active MPP pay-as-you-go session."""

    session_id: str
    service_url: str
    budget_remaining: Decimal
    payments_made: int = 0
    total_spent: Decimal = field(default_factory=lambda: Decimal("0"))


# Type alias for the policy checker callback
PolicyChecker = Callable[..., Awaitable[tuple[bool, str]]]

# Type alias for the payment signer callback
PaymentSigner = Callable[..., Awaitable[str]]  # Returns tx_hash


class MPPClient:
    """HTTP client that auto-handles MPP 402 challenges with Sardis policy enforcement.

    Args:
        wallet_address: The agent's wallet address (for on-chain payments).
        chain: Default chain for payments ("tempo", "base", etc.).
        policy_checker: Async function(amount, merchant, payment_type) -> (allowed, reason).
        signer: Async function(to, amount, token, chain) -> tx_hash.
        max_retries: Maximum 402 retry attempts per request.
    """

    def __init__(
        self,
        wallet_address: str,
        chain: str = "tempo",
        policy_checker: PolicyChecker | None = None,
        signer: PaymentSigner | None = None,
        max_retries: int = 1,
    ):
        self.wallet_address = wallet_address
        self.chain = chain
        self.policy_checker = policy_checker
        self.signer = signer
        self.max_retries = max_retries
        self._http = httpx.AsyncClient(timeout=30.0)
        self._sessions: dict[str, MPPSession] = {}

    async def close(self) -> None:
        await self._http.aclose()

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    async def _request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        """Make an HTTP request, handling 402 MPP challenges."""
        response = await self._http.request(method, url, **kwargs)

        if response.status_code != 402:
            return response

        for attempt in range(self.max_retries):
            credential = await self._handle_challenge(url, response)
            headers = dict(kwargs.get("headers", {}))
            headers["Authorization"] = credential.to_header()
            kwargs["headers"] = headers
            response = await self._http.request(method, url, **kwargs)
            if response.status_code != 402:
                return response

        return response

    async def _handle_challenge(self, url: str, response: httpx.Response) -> MPPCredential:
        """Process a 402 challenge: policy check -> sign payment -> return credential."""
        challenge = MPPChallenge.from_response(response)
        logger.info(
            "MPP challenge: %s %s %s to %s on %s",
            challenge.amount,
            challenge.currency,
            challenge.payment_method,
            challenge.recipient,
            challenge.network,
        )

        # Policy check
        if self.policy_checker:
            allowed, reason = await self.policy_checker(
                amount=challenge.amount,
                merchant=url,
                payment_type=f"mpp_{challenge.payment_method}",
                currency=challenge.currency,
                network=challenge.network,
            )
            if not allowed:
                logger.warning("MPP payment blocked by policy: %s", reason)
                raise MPPPaymentDenied(f"MPP payment to {url} blocked: {reason}")

        # Sign and submit payment
        if not self.signer:
            raise MPPPaymentDenied("No payment signer configured")

        tx_hash = await self.signer(
            to=challenge.recipient,
            amount=challenge.amount,
            token=challenge.currency,
            chain=challenge.network or self.chain,
        )

        logger.info("MPP payment submitted: tx=%s", tx_hash)

        # Track session if applicable
        if challenge.session_id:
            session = self._sessions.get(challenge.session_id)
            if session:
                session.payments_made += 1
                session.total_spent += challenge.amount
            else:
                self._sessions[challenge.session_id] = MPPSession(
                    session_id=challenge.session_id,
                    service_url=url,
                    budget_remaining=Decimal("0"),
                    payments_made=1,
                    total_spent=challenge.amount,
                )

        return MPPCredential(
            tx_hash=tx_hash,
            network=challenge.network or self.chain,
            payment_method=challenge.payment_method,
            session_id=challenge.session_id,
        )

    @property
    def active_sessions(self) -> dict[str, MPPSession]:
        return dict(self._sessions)

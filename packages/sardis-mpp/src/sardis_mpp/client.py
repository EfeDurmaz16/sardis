"""Sardis MPP client — policy-governed Machine Payments Protocol for AI agents.

Wraps the official pympp SDK with Sardis policy enforcement.
Every MPP payment (HTTP 402 challenge) passes through the Sardis
12-check policy pipeline before funds move.

Supports:
- Tempo stablecoin payments (pathUSD, USDC)
- Stripe card/wallet payments (SPT)
- Lightning Network payments (BOLT11)
- Any MPP-compatible payment method

Usage:
    from sardis_mpp import SardisMPPClient
    from mpp.methods.tempo.client import TempoMethod
    from mpp.methods.tempo.account import TempoAccount
    from eth_account import Account

    account = TempoAccount(Account.from_key("0x..."))
    tempo = TempoMethod(account=account, rpc_url="https://rpc.tempo.xyz")

    client = SardisMPPClient(
        methods=[tempo],
        policy_checker=sardis_policy_fn,
    )

    # Auto-handles 402, checks policy, pays, retries
    response = await client.get("https://api.example.com/data")

References:
    - https://mpp.dev (protocol spec)
    - https://docs.stripe.com/payments/machine/mpp (Stripe integration)
    - https://tempo.xyz/blog/mainnet (Tempo + MPP launch)
    - https://paymentauth.org (IETF draft)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Awaitable, Callable, Sequence

import httpx

from mpp.client.transport import (
    Challenge,
    Client as MPPBaseClient,
    Method,
    PaymentTransport,
)

logger = logging.getLogger(__name__)

# Policy checker: async fn(amount, merchant, payment_type, ...) -> (allowed, reason)
PolicyChecker = Callable[..., Awaitable[tuple[bool, str]]]


class MPPPaymentDenied(Exception):
    """Raised when Sardis policy blocks an MPP payment."""


@dataclass
class MPPPaymentRecord:
    """Record of an MPP payment for audit trail."""

    url: str
    method: str
    challenge_id: str
    amount: str
    currency: str
    payment_method: str
    network: str
    policy_result: str  # "ALLOWED" or "DENIED"
    policy_reason: str
    tx_hash: str | None = None
    error: str | None = None


class SardisPolicyTransport(httpx.AsyncBaseTransport):
    """httpx transport that intercepts MPP 402 challenges for policy enforcement.

    Wraps PaymentTransport but adds a policy check before any payment is made.
    """

    def __init__(
        self,
        methods: Sequence[Method],
        policy_checker: PolicyChecker | None = None,
        on_payment: Callable[[MPPPaymentRecord], None] | None = None,
        inner: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._methods = list(methods)
        self._policy_checker = policy_checker
        self._on_payment = on_payment
        self._inner = inner or httpx.AsyncHTTPTransport()

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        # First request — no payment
        response = await self._inner.handle_async_request(request)

        if response.status_code != 402:
            return response

        # Parse 402 challenge
        www_auth = response.headers.get("www-authenticate", "")
        if not www_auth:
            return response

        try:
            challenge = Challenge.from_www_authenticate(www_auth)
        except Exception as e:
            logger.warning("Failed to parse MPP challenge: %s", e)
            return response

        # Extract payment details from challenge
        req_data = challenge.request or {}
        amount_raw = req_data.get("amount", "0")
        currency = req_data.get("currency", "USD")
        payment_method = challenge.method
        network = req_data.get("network", "tempo")
        merchant_url = str(request.url)

        # Policy check
        if self._policy_checker:
            allowed, reason = await self._policy_checker(
                amount=Decimal(str(amount_raw)),
                merchant=merchant_url,
                payment_type=f"mpp_{payment_method}",
                currency=currency,
                network=network,
            )

            record = MPPPaymentRecord(
                url=merchant_url,
                method=payment_method,
                challenge_id=challenge.id,
                amount=str(amount_raw),
                currency=currency,
                payment_method=payment_method,
                network=network,
                policy_result="ALLOWED" if allowed else "DENIED",
                policy_reason=reason,
            )

            if not allowed:
                logger.warning("MPP payment blocked by Sardis policy: %s", reason)
                if self._on_payment:
                    self._on_payment(record)
                raise MPPPaymentDenied(
                    f"Payment to {merchant_url} blocked: {reason}"
                )

            if self._on_payment:
                self._on_payment(record)

        # Find matching method and create credential
        for method in self._methods:
            if method.name == challenge.method:
                credential = method.create_credential(challenge)
                auth_header = credential.to_authorization()

                # Retry with payment credential
                retry_request = httpx.Request(
                    method=request.method,
                    url=request.url,
                    headers={**dict(request.headers), "Authorization": auth_header},
                    content=request.content,
                )
                return await self._inner.handle_async_request(retry_request)

        logger.warning("No matching MPP method for: %s", challenge.method)
        return response

    async def aclose(self) -> None:
        await self._inner.aclose()


class SardisMPPClient:
    """MPP client with Sardis policy enforcement.

    Drop-in replacement for mpp.client.Client that adds:
    - 12-check policy evaluation on every payment
    - Payment audit records
    - Configurable payment methods (Tempo, Stripe, Lightning)

    Args:
        methods: List of MPP payment methods (TempoMethod, etc.)
        policy_checker: Sardis policy evaluation function
        on_payment: Callback for payment audit records
    """

    def __init__(
        self,
        methods: Sequence[Method],
        policy_checker: PolicyChecker | None = None,
        on_payment: Callable[[MPPPaymentRecord], None] | None = None,
    ) -> None:
        self._methods = list(methods)
        self._policy_checker = policy_checker
        self._on_payment = on_payment
        self._payment_records: list[MPPPaymentRecord] = []

        def _record_payment(record: MPPPaymentRecord) -> None:
            self._payment_records.append(record)
            if on_payment:
                on_payment(record)

        transport = SardisPolicyTransport(
            methods=methods,
            policy_checker=policy_checker,
            on_payment=_record_payment,
        )
        self._http = httpx.AsyncClient(transport=transport)

    async def get(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._http.get(url, **kwargs)

    async def post(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._http.post(url, **kwargs)

    async def put(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._http.put(url, **kwargs)

    async def delete(self, url: str, **kwargs: Any) -> httpx.Response:
        return await self._http.delete(url, **kwargs)

    async def request(self, method: str, url: str, **kwargs: Any) -> httpx.Response:
        return await self._http.request(method, url, **kwargs)

    async def close(self) -> None:
        await self._http.aclose()

    @property
    def payment_records(self) -> list[MPPPaymentRecord]:
        """All payment records from this client session."""
        return list(self._payment_records)

    @property
    def total_spent(self) -> Decimal:
        """Total amount spent across all payments."""
        return sum(
            (Decimal(r.amount) for r in self._payment_records if r.policy_result == "ALLOWED"),
            Decimal("0"),
        )


# ---------------------------------------------------------------------------
# Protocol v1.0 enhancements
# ---------------------------------------------------------------------------


class MPPSessionManager:
    """Maps Sardis spending mandates to MPP session parameters.

    NLP policies → MPP session params:
      max_per_tx → maxDeposit
      expires_at → session expiry
      merchant_scope → allowed services

    Also provides anomaly detection on voucher flow
    and force-close for policy violations.
    """

    def __init__(self, policy_checker: PolicyChecker | None = None) -> None:
        self._policy_checker = policy_checker
        self._sessions: dict[str, dict[str, Any]] = {}
        self._anomaly_threshold = Decimal("3.0")  # 3x average spend = anomaly

    def mandate_to_session_params(self, mandate) -> dict[str, Any]:
        """Convert a Sardis SpendingMandate to MPP session parameters."""
        params: dict[str, Any] = {}

        if mandate.amount_per_tx:
            params["maxDeposit"] = str(mandate.amount_per_tx)
        if mandate.amount_daily:
            params["dailyLimit"] = str(mandate.amount_daily)
        if mandate.expires_at:
            params["expiry"] = int(mandate.expires_at.timestamp())

        # Map merchant scope to allowed services
        allowed = mandate.merchant_scope.get("allowed", [])
        if allowed:
            params["allowedServices"] = allowed

        params["mandateId"] = mandate.id
        params["agentId"] = mandate.agent_id

        return params

    def track_payment(self, session_id: str, amount: Decimal) -> None:
        """Track a payment for anomaly detection."""
        if session_id not in self._sessions:
            self._sessions[session_id] = {
                "payments": [],
                "total": Decimal("0"),
                "count": 0,
            }

        sess = self._sessions[session_id]
        sess["payments"].append(amount)
        sess["total"] += amount
        sess["count"] += 1

    def check_anomaly(self, session_id: str, amount: Decimal) -> bool:
        """Check if a payment amount is anomalous for this session.

        Returns True if the amount is suspicious (> 3x rolling average).
        """
        sess = self._sessions.get(session_id)
        if not sess or sess["count"] < 5:
            return False  # Not enough data

        avg = sess["total"] / sess["count"]
        return amount > avg * self._anomaly_threshold

    async def force_close(self, session_id: str, reason: str) -> None:
        """Force-close an MPP session that violates policy.

        Logs the violation and marks the session as terminated.
        """
        logger.warning(
            "Force-closing MPP session %s: %s", session_id, reason,
        )
        if session_id in self._sessions:
            self._sessions[session_id]["status"] = "force_closed"
            self._sessions[session_id]["close_reason"] = reason

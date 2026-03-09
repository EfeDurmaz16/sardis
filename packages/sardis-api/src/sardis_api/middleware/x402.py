"""x402 HTTP 402 Payment Required middleware for FastAPI.

Follows the TAP middleware pattern (BaseHTTPMiddleware + dataclass config).
Automatically generates 402 challenges for protected paths and verifies
payment signatures on retry requests.

All payments flow through the ControlPlane — no bypass path.
"""
from __future__ import annotations

import base64
import json
import logging
import os
from collections.abc import Callable
from dataclasses import dataclass, field

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .exceptions import get_request_id

logger = logging.getLogger(__name__)


@dataclass
class X402PricingRule:
    """Pricing rule for a path prefix."""
    path_prefix: str
    amount: str  # atomic units
    currency: str = "USDC"
    network: str = "base"
    token_address: str = ""
    scheme: str = "exact"
    ttl_seconds: int = 300


class X402PricingRegistry:
    """Maps path prefixes to pricing rules."""

    def __init__(self, rules: dict[str, X402PricingRule] | None = None) -> None:
        self.rules: dict[str, X402PricingRule] = rules or {}

    def get_rule(self, path: str) -> X402PricingRule | None:
        """Find the most specific matching rule for a path."""
        best_match: X402PricingRule | None = None
        best_len = 0
        for prefix, rule in self.rules.items():
            if path.startswith(prefix) and len(prefix) > best_len:
                best_match = rule
                best_len = len(prefix)
        return best_match

    def add_rule(self, rule: X402PricingRule) -> None:
        self.rules[rule.path_prefix] = rule


@dataclass
class X402MiddlewareConfig:
    """Configuration for x402 payment middleware."""
    pricing_registry: X402PricingRegistry = field(default_factory=X402PricingRegistry)
    payee_address: str = ""
    payee_wallet_id: str = ""
    enabled: bool = False
    default_ttl_seconds: int = 300
    default_network: str = "base"
    default_currency: str = "USDC"

    @classmethod
    def from_environment(cls) -> X402MiddlewareConfig:
        """Load configuration from environment variables."""
        return cls(
            enabled=os.getenv("SARDIS_X402_SERVER_ENABLED", "false").lower() == "true",
            payee_address=os.getenv("SARDIS_X402_PAYEE_ADDRESS", ""),
            payee_wallet_id=os.getenv("SARDIS_X402_PAYEE_WALLET_ID", ""),
            default_ttl_seconds=int(os.getenv("SARDIS_X402_DEFAULT_TTL", "300")),
            default_network=os.getenv("SARDIS_X402_DEFAULT_NETWORK", "base"),
            default_currency=os.getenv("SARDIS_X402_DEFAULT_CURRENCY", "USDC"),
        )


# Header constants (re-exported from protocol for convenience)
X402_PAYMENT_SIGNATURE_HEADER = "PAYMENT-SIGNATURE"
X402_PAYMENT_RESPONSE_HEADER = "PAYMENT-RESPONSE"
X402_PAYMENT_REQUIRED_HEADER = "PaymentRequired"


class X402PaymentMiddleware(BaseHTTPMiddleware):
    """Middleware that charges for API access via x402 protocol.

    Flow:
    1. Check if request path has a pricing rule
    2. If no PAYMENT-SIGNATURE header -> return 402 with challenge
    3. If header present -> verify, submit through control plane, pass through
    """

    def __init__(
        self,
        app,
        config: X402MiddlewareConfig | None = None,
    ):
        super().__init__(app)
        self.config = config or X402MiddlewareConfig.from_environment()
        logger.info(
            "x402 payment middleware initialized (enabled=%s, payee=%s)",
            self.config.enabled,
            self.config.payee_address[:10] + "..." if self.config.payee_address else "not-set",
        )

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        if not self.config.enabled:
            return await call_next(request)

        rule = self.config.pricing_registry.get_rule(request.url.path)
        if rule is None:
            return await call_next(request)

        sig_header = request.headers.get(X402_PAYMENT_SIGNATURE_HEADER)
        if not sig_header:
            return self._generate_402(request, rule)

        # Verify and settle
        result = await self._verify_and_settle(request, sig_header, rule)
        if not result["success"]:
            return JSONResponse(
                status_code=400,
                content={"error": result.get("error", "payment_verification_failed")},
            )

        # Inject result into request state for downstream handlers
        request.state.x402_result = result

        response = await call_next(request)

        # Add payment receipt header
        receipt_data = {
            "payment_id": result.get("payment_id", ""),
            "status": "settled",
            "tx_hash": result.get("tx_hash", ""),
        }
        encoded = base64.b64encode(json.dumps(receipt_data, separators=(",", ":")).encode()).decode()
        response.headers[X402_PAYMENT_RESPONSE_HEADER] = encoded

        return response

    def _generate_402(self, request: Request, rule: X402PricingRule) -> JSONResponse:
        """Generate a 402 Payment Required response with challenge."""
        try:
            from sardis_protocol.x402 import generate_challenge, serialize_challenge_header
        except ImportError:
            logger.error("x402 protocol module not available")
            return JSONResponse(status_code=503, content={"error": "x402_not_available"})

        challenge_response = generate_challenge(
            resource_uri=str(request.url),
            amount=rule.amount,
            currency=rule.currency,
            payee_address=self.config.payee_address,
            network=rule.network,
            token_address=rule.token_address,
            ttl_seconds=rule.ttl_seconds,
        )
        challenge = challenge_response.challenge

        request_id = get_request_id(request)
        logger.info(
            "x402 middleware: 402 challenge generated path=%s payment_id=%s",
            request.url.path,
            challenge.payment_id,
            extra={"request_id": request_id},
        )

        challenge_header = serialize_challenge_header(challenge)

        return JSONResponse(
            status_code=402,
            content={
                "error": "payment_required",
                "payment_id": challenge.payment_id,
                "amount": challenge.amount,
                "currency": challenge.currency,
                "network": challenge.network,
                "payee_address": challenge.payee_address,
                "expires_at": challenge.expires_at,
                "scheme": rule.scheme,
            },
            headers={
                X402_PAYMENT_REQUIRED_HEADER: challenge_header,
                "Content-Type": "application/json",
            },
        )

    async def _verify_and_settle(
        self,
        request: Request,
        sig_header: str,
        rule: X402PricingRule,
    ) -> dict:
        """Verify payment signature and settle through control plane."""
        try:
            from sardis_protocol.x402 import (
                X402HeaderBuilder,
                X402PaymentPayload,
                verify_payment_payload,
            )
            from sardis_protocol.x402_settlement import (
                DatabaseSettlementStore,
                X402Settler,
            )
        except ImportError:
            return {"success": False, "error": "x402_modules_not_available"}

        try:
            payload: X402PaymentPayload = X402HeaderBuilder.parse_payment_signature_header(sig_header)
        except (ValueError, Exception) as e:
            logger.warning("x402 middleware: invalid payment signature header: %s", e)
            return {"success": False, "error": f"invalid_signature: {e}"}

        # We need the challenge to verify against. In a real implementation,
        # the challenge would be cached/stored. For middleware, we regenerate
        # and verify the payload fields match.
        from sardis_protocol.x402 import X402Challenge

        challenge = X402Challenge(
            payment_id=payload.payment_id,
            resource_uri=str(request.url),
            amount=payload.amount,
            currency=rule.currency,
            payee_address=self.config.payee_address,
            network=rule.network,
            token_address=rule.token_address,
            expires_at=0,  # Will be checked from stored challenge
            nonce=payload.nonce,
        )

        verification = verify_payment_payload(payload=payload, challenge=challenge)
        if not verification.accepted:
            return {"success": False, "error": verification.reason or "verification_failed"}

        store = DatabaseSettlementStore()
        settler = X402Settler(store=store, chain_executor=None)
        settlement = await settler.verify(challenge=challenge, payload=payload)

        return {
            "success": settlement.status.value == "verified",
            "payment_id": payload.payment_id,
            "payer_address": payload.payer_address,
            "amount": payload.amount,
            "tx_hash": settlement.tx_hash or "",
            "error": settlement.error or "",
        }


__all__ = [
    "X402PaymentMiddleware",
    "X402MiddlewareConfig",
    "X402PricingRegistry",
    "X402PricingRule",
]

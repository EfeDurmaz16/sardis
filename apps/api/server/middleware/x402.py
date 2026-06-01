"""x402 HTTP 402 Payment Required middleware for FastAPI.

Follows the TAP middleware pattern (BaseHTTPMiddleware + dataclass config).
Automatically generates 402 challenges for protected paths and verifies
payment signatures on retry requests.

EXPERIMENTAL / PARTIAL ADAPTER — not certified x402 conformance.
The wire format diverges from the canonical x402 spec
(X-PAYMENT / X-PAYMENT-RESPONSE / accepts:[PaymentRequirements] / EIP-3009),
the EIP-3009 signature is not verified, and this path does not perform
on-chain settlement or a fail-closed control-plane policy check. Use the
x402 wallet path (routes/wallets/lifecycle.py) for mandate-bound settlement.
See docs/productization/research/PROTOCOL_STRATEGY.md (x402, fix-then-keep).
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


# Header constants.
# Canonical x402 v1 headers (the real, interoperable transport):
X402_X_PAYMENT_HEADER = "X-PAYMENT"
X402_X_PAYMENT_RESPONSE_HEADER = "X-PAYMENT-RESPONSE"
# Legacy Sardis-native headers (kept for backward compatibility):
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

        # Prefer the canonical X-PAYMENT header; fall back to the legacy
        # PAYMENT-SIGNATURE header for backward compatibility.
        x_payment = request.headers.get(X402_X_PAYMENT_HEADER)
        sig_header = request.headers.get(X402_PAYMENT_SIGNATURE_HEADER)
        if not x_payment and not sig_header:
            return self._generate_402(request, rule)

        if x_payment:
            result = await self._verify_and_settle_canonical(request, x_payment, rule)
        else:
            result = await self._verify_and_settle(request, sig_header, rule)

        if not result["success"]:
            # Canonical x402: settlement failure is signaled with HTTP 402 plus
            # the X-PAYMENT-RESPONSE header (transport spec). Legacy callers got a
            # 400; preserve that for the legacy header path.
            if x_payment:
                return JSONResponse(
                    status_code=402,
                    content={
                        "x402Version": 1,
                        "error": result.get("error", "payment_verification_failed"),
                    },
                    headers={
                        X402_X_PAYMENT_RESPONSE_HEADER: self._encode_settlement_response(
                            success=False,
                            transaction="",
                            network=result.get("network", rule.network),
                            payer=result.get("payer_address", ""),
                            error_reason=result.get("error"),
                        )
                    },
                )
            return JSONResponse(
                status_code=400,
                content={"error": result.get("error", "payment_verification_failed")},
            )

        # Inject result into request state for downstream handlers
        request.state.x402_result = result

        response = await call_next(request)

        # Canonical settlement-result header (X-PAYMENT-RESPONSE).
        response.headers[X402_X_PAYMENT_RESPONSE_HEADER] = self._encode_settlement_response(
            success=True,
            transaction=result.get("tx_hash", ""),
            network=result.get("network", rule.network),
            payer=result.get("payer_address", ""),
        )
        # Legacy receipt header (kept for backward compatibility).
        receipt_data = {
            "payment_id": result.get("payment_id", ""),
            "status": "settled",
            "tx_hash": result.get("tx_hash", ""),
        }
        encoded = base64.b64encode(json.dumps(receipt_data, separators=(",", ":")).encode()).decode()
        response.headers[X402_PAYMENT_RESPONSE_HEADER] = encoded

        return response

    @staticmethod
    def _encode_settlement_response(
        *,
        success: bool,
        transaction: str,
        network: str,
        payer: str,
        error_reason: str | None = None,
    ) -> str:
        """Build the canonical base64 X-PAYMENT-RESPONSE header value."""
        from sardis.protocol.x402_canonical import (
            SettlementResponse,
            encode_x_payment_response_header,
            sardis_network_to_canonical,
        )

        try:
            canonical_net = sardis_network_to_canonical(network)
        except Exception:
            canonical_net = network
        return encode_x_payment_response_header(
            SettlementResponse(
                success=success,
                transaction=transaction or "",
                network=canonical_net,
                payer=payer or "",
                error_reason=error_reason if not success else None,
            )
        )

    def _generate_402(self, request: Request, rule: X402PricingRule) -> JSONResponse:
        """Generate a 402 Payment Required response with challenge."""
        try:
            from sardis.protocol.x402 import generate_challenge, serialize_challenge_header
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

        # Canonical x402 v1 accepts:[PaymentRequirements] (spec §5.1) — the real,
        # interoperable 402 body that x402-fetch / CDP clients read. Legacy flat
        # keys (error/payment_id/amount/...) and the PaymentRequired header are
        # retained alongside for backward compatibility.
        canonical_accepts = self._build_canonical_accepts(request, rule)
        content: dict = {
            "x402Version": 1,
            "error": "payment_required",
            "accepts": canonical_accepts,
            # legacy flat fields:
            "payment_id": challenge.payment_id,
            "amount": challenge.amount,
            "currency": challenge.currency,
            "network": challenge.network,
            "payee_address": challenge.payee_address,
            "expires_at": challenge.expires_at,
            "scheme": rule.scheme,
        }

        return JSONResponse(
            status_code=402,
            content=content,
            headers={
                X402_PAYMENT_REQUIRED_HEADER: challenge_header,
                "Content-Type": "application/json",
            },
        )

    def _build_canonical_accepts(self, request: Request, rule: X402PricingRule) -> list[dict]:
        """Build the canonical accepts:[PaymentRequirements] array for a 402."""
        from sardis.protocol.x402_canonical import PaymentRequirements

        try:
            canonical_net = self._canonical_network(rule.network)
        except Exception:
            canonical_net = rule.network

        # EIP-712 token domain (name/version) for the extra field, sourced from
        # Sardis's hardcoded USDC domains (never client-supplied).
        extra: dict | None = None
        asset = rule.token_address
        try:
            from sardis.protocol.x402_erc3009 import resolve_eip712_domain

            domain = resolve_eip712_domain(rule.network)
            extra = {"name": domain["name"], "version": domain["version"]}
            if not asset:
                asset = domain["verifyingContract"]
        except Exception:
            pass

        req = PaymentRequirements(
            scheme=rule.scheme,
            network=canonical_net,
            max_amount_required=rule.amount,
            asset=asset or "",
            pay_to=self.config.payee_address,
            resource=str(request.url),
            description=f"Access to {request.url.path}",
            max_timeout_seconds=rule.ttl_seconds,
            mime_type="application/json",
            output_schema=None,
            extra=extra,
        )
        return [req.to_dict()]

    @staticmethod
    def _canonical_network(network: str) -> str:
        from sardis.protocol.x402_canonical import sardis_network_to_canonical

        return sardis_network_to_canonical(network)

    async def _verify_and_settle_canonical(
        self,
        request: Request,
        x_payment_header: str,
        rule: X402PricingRule,
    ) -> dict:
        """Verify a canonical X-PAYMENT header and settle through the control plane.

        Decodes the canonical PaymentPayload, binds it to the rule-derived
        PaymentRequirements, runs the EIP-3009 verifier (fail-closed), then
        settles on-chain via the existing settler.
        """
        try:
            from sardis.protocol.x402_canonical import (
                PaymentRequirements,
                X402WireError,
                decode_x_payment_header,
            )
        except ImportError:
            return {"success": False, "error": "x402_modules_not_available"}

        try:
            payload = decode_x_payment_header(x_payment_header)
        except X402WireError as exc:
            logger.warning("x402 middleware: invalid X-PAYMENT header: %s", exc)
            return {"success": False, "error": exc.code.value}

        try:
            canonical_net = self._canonical_network(rule.network)
        except Exception:
            canonical_net = rule.network

        asset = rule.token_address
        extra: dict | None = None
        try:
            from sardis.protocol.x402_erc3009 import resolve_eip712_domain

            domain = resolve_eip712_domain(rule.network)
            extra = {"name": domain["name"], "version": domain["version"]}
            if not asset:
                asset = domain["verifyingContract"]
        except Exception:
            pass

        requirements = PaymentRequirements(
            scheme=rule.scheme,
            network=canonical_net,
            max_amount_required=rule.amount,
            asset=asset or "",
            pay_to=self.config.payee_address,
            resource=str(request.url),
            description=f"Access to {request.url.path}",
            max_timeout_seconds=rule.ttl_seconds,
            extra=extra,
        )

        # Reuse the route's canonical verifier (single source of money-path truth).
        from server.routes.protocol.x402 import _verify_canonical_payment

        is_valid, invalid_reason, payer = _verify_canonical_payment(payload, requirements)
        if not is_valid:
            return {
                "success": False,
                "error": invalid_reason,
                "payer_address": payer or "",
                "network": rule.network,
            }

        # Settle on-chain via the existing settler.
        try:
            from sardis.chain.executor import ChainExecutor
            from sardis.protocol.x402 import X402Challenge, X402PaymentPayload
            from sardis.protocol.x402_settlement import (
                DatabaseSettlementStore,
                X402Settlement,
                X402Settler,
                X402SettlementStatus,
            )
        except ImportError:
            return {"success": False, "error": "x402_modules_not_available"}

        auth = payload.authorization
        challenge = X402Challenge(
            payment_id=f"x402c_{auth.nonce}",
            resource_uri=str(request.url),
            amount=rule.amount,
            currency=rule.currency,
            payee_address=self.config.payee_address,
            network=rule.network,
            token_address=asset or "",
            expires_at=int(auth.valid_before),
            nonce=auth.nonce,
        )
        native_payload = X402PaymentPayload(
            payment_id=challenge.payment_id,
            payer_address=payer,
            amount=auth.value,
            nonce=auth.nonce,
            signature=payload.signature,
            authorization=auth.to_dict(),
        )
        try:
            store = DatabaseSettlementStore()
            settler = X402Settler(store=store, chain_executor=ChainExecutor())
            settlement = X402Settlement(
                payment_id=challenge.payment_id,
                status=X402SettlementStatus.VERIFIED,
                challenge=challenge,
                payload=native_payload,
            )
            await store.save(settlement)
            settled = await settler.settle(settlement)
        except Exception as exc:
            logger.warning("x402 middleware: canonical settle failed: %s", exc)
            return {
                "success": False,
                "error": "unexpected_settle_error",
                "payer_address": payer,
                "network": rule.network,
            }

        return {
            "success": settled.status == X402SettlementStatus.SETTLED,
            "payment_id": challenge.payment_id,
            "payer_address": payer,
            "amount": auth.value,
            "tx_hash": settled.tx_hash or "",
            "network": rule.network,
            "error": settled.error or "",
        }

    async def _verify_and_settle(
        self,
        request: Request,
        sig_header: str,
        rule: X402PricingRule,
    ) -> dict:
        """Verify payment signature and settle through control plane."""
        try:
            from sardis.protocol.x402 import (
                X402HeaderBuilder,
                X402PaymentPayload,
                verify_payment_payload,
            )
            from sardis.protocol.x402_settlement import (
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
        from sardis.protocol.x402 import X402Challenge

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
    "X402_X_PAYMENT_HEADER",
    "X402_X_PAYMENT_RESPONSE_HEADER",
]

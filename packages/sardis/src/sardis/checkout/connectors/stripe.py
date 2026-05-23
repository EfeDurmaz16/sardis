"""Stripe PSP connector."""
from __future__ import annotations

import hashlib
import hmac
import os
from typing import Any

import httpx

from sardis.checkout.connectors.base import PSPConnector
from sardis.checkout.models import CheckoutRequest, CheckoutResponse, PaymentStatus, PSPType


class StripeConnector(PSPConnector):
    """Stripe payment connector."""

    def __init__(
        self,
        api_key: str,
        webhook_secret: str | None = None,
        api_base: str = "https://api.stripe.com/v1",
    ):
        self.api_key = api_key
        self.webhook_secret = webhook_secret
        self.api_base = api_base.rstrip("/")
        self._client = httpx.AsyncClient(
            base_url=self.api_base,
            auth=(api_key, ""),
            timeout=30.0,
        )

    @property
    def psp_type(self) -> PSPType:
        return PSPType.STRIPE

    def _resolve_payment_method_types(
        self,
        requested: list[str] | None = None,
    ) -> list[str]:
        """Resolve Stripe payment method types from request or config.

        Apple Pay and Google Pay work through the 'card' type with wallet
        detection in Stripe — no separate type needed.
        """
        configured = os.getenv(
            "SARDIS_CHECKOUT_PAYMENT_METHODS", "card,apple_pay,google_pay,link"
        ).split(",")
        methods = requested or configured

        # Map to Stripe payment_method_types
        # Apple Pay and Google Pay are handled by 'card' with wallet detection
        stripe_types: list[str] = []
        for m in methods:
            m = m.strip()
            if m in ("card", "apple_pay", "google_pay"):
                if "card" not in stripe_types:
                    stripe_types.append("card")
            elif m == "klarna":
                stripe_types.append("klarna")
            elif m == "link":
                stripe_types.append("link")
            elif m == "paypal":
                stripe_types.append("paypal")
        return stripe_types or ["card"]

    async def create_checkout_session(
        self,
        request: CheckoutRequest,
    ) -> CheckoutResponse:
        """Create Stripe Checkout session."""
        # Convert amount to cents (Stripe uses minor units)
        amount_cents = int(request.amount * 100)

        # Prepare metadata
        stripe_metadata = {
            "agent_id": request.agent_id,
            "wallet_id": request.wallet_id,
            "mandate_id": request.mandate_id,
            **request.metadata,
        }

        # Create session
        payload = {
            "mode": "payment",
            "payment_method_types": self._resolve_payment_method_types(
                getattr(request, "payment_methods", None)
            ),
            "payment_method_options": {
                "card": {
                    "request_three_d_secure": "automatic",
                },
            },
            "line_items": [
                {
                    "price_data": {
                        "currency": request.currency.lower(),
                        "product_data": {
                            "name": request.description or f"Agent Payment - {request.agent_id}",
                            "metadata": stripe_metadata,
                        },
                        "unit_amount": amount_cents,
                    },
                    "quantity": 1,
                }
            ],
            "metadata": stripe_metadata,
        }

        if request.success_url:
            payload["success_url"] = request.success_url
        if request.cancel_url:
            payload["cancel_url"] = request.cancel_url

        response = await self._client.post(
            "/checkout/sessions",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        return CheckoutResponse(
            checkout_id=data["id"],
            redirect_url=data["url"],
            status=PaymentStatus.PENDING,
            psp_name="stripe",
            amount=request.amount,
            currency=request.currency,
            agent_id=request.agent_id,
            mandate_id=request.mandate_id,
            metadata=stripe_metadata,
        )

    async def verify_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> bool:
        """Verify Stripe webhook signature."""
        if not self.webhook_secret:
            return False

        try:
            # Stripe signature format: "t=timestamp,v1=signature"
            # We need to extract the signature part
            sig_parts = signature.split(",")
            sig_dict = {}
            for part in sig_parts:
                key, value = part.split("=", 1)
                sig_dict[key] = value

            timestamp = sig_dict.get("t", "")
            signature_v1 = sig_dict.get("v1", "")

            # Create expected signature
            signed_payload = f"{timestamp}.{payload.decode()}"
            expected_sig = hmac.new(
                self.webhook_secret.encode(),
                signed_payload.encode(),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected_sig, signature_v1)
        except Exception:
            return False

    async def get_payment_status(
        self,
        session_id: str,
    ) -> PaymentStatus:
        """Get Stripe checkout session status."""
        response = await self._client.get(f"/checkout/sessions/{session_id}")
        response.raise_for_status()
        data = response.json()

        payment_status = data.get("payment_status", "unpaid")

        status_map = {
            "paid": PaymentStatus.COMPLETED,
            "unpaid": PaymentStatus.PENDING,
            "no_payment_required": PaymentStatus.COMPLETED,
        }

        return status_map.get(payment_status, PaymentStatus.PENDING)

    async def handle_webhook(
        self,
        payload: dict[str, Any],
        headers: dict[str, str],
        raw_payload: bytes | None = None,
    ) -> dict[str, Any]:
        """Handle Stripe webhook with proper signature verification.

        Args:
            payload: Parsed JSON payload.
            headers: HTTP headers from the request.
            raw_payload: Raw request body bytes (required for signature verification).

        Raises:
            RuntimeError: If webhook secret is not configured in production.
            ValueError: If signature is present but invalid.
        """
        import logging

        logger = logging.getLogger("sardis.checkout.stripe")
        signature = headers.get("stripe-signature", "")
        is_production = os.getenv("SARDIS_ENV", "dev") in ("production", "prod", "staging")
        webhook_secret = self.webhook_secret or os.getenv("SARDIS_STRIPE_WEBHOOK_SECRET")

        if not webhook_secret:
            if is_production:
                raise RuntimeError(
                    "SARDIS_STRIPE_WEBHOOK_SECRET is not configured. "
                    "Webhook signature verification is required in production."
                )
            logger.warning(
                "SARDIS_STRIPE_WEBHOOK_SECRET not configured — skipping signature "
                "verification. This is only acceptable in dev/test environments."
            )
        elif signature and raw_payload is not None:
            # Verify the Stripe webhook signature
            is_valid = await self._verify_stripe_signature(raw_payload, signature, webhook_secret)
            if not is_valid:
                raise ValueError(
                    "Invalid Stripe webhook signature. The request may have been "
                    "tampered with or the webhook secret is incorrect."
                )
        elif signature and raw_payload is None:
            logger.warning(
                "Stripe signature present but raw_payload not provided — "
                "cannot verify signature. Pass raw request body bytes."
            )
            if is_production:
                raise ValueError(
                    "raw_payload is required for webhook signature verification in production."
                )

        # Parse event
        event_type = payload.get("type", "")
        data = payload.get("data", {})
        object_data = data.get("object", {})

        # Normalize to common format
        normalized = {
            "event_type": event_type,
            "session_id": object_data.get("id", ""),
            "payment_status": object_data.get("payment_status", ""),
            "amount": object_data.get("amount_total", 0) / 100,  # Convert from cents
            "currency": object_data.get("currency", ""),
            "metadata": object_data.get("metadata", {}),
        }

        return normalized

    async def _verify_stripe_signature(
        self,
        raw_payload: bytes,
        signature: str,
        webhook_secret: str,
        tolerance: int = 300,
    ) -> bool:
        """Verify Stripe webhook signature using HMAC-SHA256.

        Implements the same algorithm as stripe.Webhook.construct_event():
        1. Extract timestamp and signature from header
        2. Compute expected signature: HMAC-SHA256(secret, "{timestamp}.{payload}")
        3. Compare signatures using constant-time comparison
        4. Verify timestamp is within tolerance window

        Args:
            raw_payload: Raw request body bytes.
            signature: Stripe-Signature header value.
            webhook_secret: Webhook endpoint secret (whsec_...).
            tolerance: Maximum age of the event in seconds (default: 300).

        Returns:
            True if the signature is valid.
        """
        import time

        try:
            sig_parts = signature.split(",")
            sig_dict: dict[str, str] = {}
            for part in sig_parts:
                key, value = part.strip().split("=", 1)
                sig_dict[key] = value

            timestamp_str = sig_dict.get("t", "")
            signature_v1 = sig_dict.get("v1", "")

            if not timestamp_str or not signature_v1:
                return False

            # Check timestamp tolerance to prevent replay attacks
            timestamp = int(timestamp_str)
            if abs(time.time() - timestamp) > tolerance:
                return False

            # Compute expected signature
            signed_payload = f"{timestamp_str}.{raw_payload.decode('utf-8')}"
            expected_sig = hmac.new(
                webhook_secret.encode("utf-8"),
                signed_payload.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()

            return hmac.compare_digest(expected_sig, signature_v1)
        except Exception:
            return False

    async def parse_webhook_event(
        self,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Parse Stripe webhook event (legacy method)."""
        return await self.handle_webhook(payload, {})

    async def close(self):
        """Close HTTP client."""
        await self._client.aclose()

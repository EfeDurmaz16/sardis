"""Stripe MPP Payment Method — fiat payments via Shared Payment Tokens.

Implements the MPP Method protocol for Stripe SPT-based payments.
When a server returns 402 with a stripe.charge challenge, this method:
1. Creates/retrieves an SPT from the agent's spending mandate
2. Returns a Credential with the SPT token
3. The server uses the SPT to create a PaymentIntent

This enables AI agents to pay for services using traditional payment
methods (cards, wallets) through the MPP protocol, alongside the
Tempo crypto payment method.

Reference:
- https://docs.stripe.com/payments/machine/mpp
- https://docs.stripe.com/agentic-commerce/concepts/shared-payment-tokens

Usage::

    from sardis_mpp.stripe_method import SardisStripeMPPMethod

    stripe_method = SardisStripeMPPMethod(
        api_key="sk_...",
        mandate_id="mandate_abc123",
    )

    client = SardisMPPClient(
        methods=[tempo_method, stripe_method],
        policy_checker=policy_fn,
    )
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger("sardis.mpp.stripe")


@dataclass
class StripeChallenge:
    """Parsed Stripe MPP challenge from 402 response."""
    amount: str = ""
    currency: str = "usd"
    description: str = ""
    network_id: str = "internal"
    payment_method_types: list[str] = field(default_factory=lambda: ["card"])


@dataclass
class StripeSPTCredential:
    """Credential containing a Stripe SPT for payment."""
    spt_id: str = ""
    source: str = "sardis"

    def to_authorization(self) -> str:
        """Format as HTTP Authorization header value."""
        return f"Payment method=stripe.charge token={self.spt_id}"


class SardisStripeMPPMethod:
    """MPP Method implementation for Stripe fiat payments.

    Uses Stripe SPTs (Shared Payment Tokens) to pay for
    402-gated services. Integrates with Sardis spending mandates
    for policy enforcement before any payment.
    """

    name = "stripe.charge"

    def __init__(
        self,
        api_key: str | None = None,
        mandate_id: str | None = None,
        payment_method: str = "pm_card_visa",
        network_id: str = "internal",
        sardis_url: str = "",
    ) -> None:
        self._api_key = api_key or os.getenv("STRIPE_SECRET_KEY", "")
        self._mandate_id = mandate_id
        self._payment_method = payment_method
        self._network_id = network_id
        self._sardis_url = sardis_url or os.getenv(
            "SARDIS_API_URL", "https://api.sardis.sh"
        )

    async def create_credential(self, challenge) -> StripeSPTCredential:
        """Create a Stripe SPT credential from an MPP challenge.

        1. Parse the challenge amount/currency
        2. Create an SPT via Stripe API (with mandate-derived limits)
        3. Return credential with SPT ID
        """
        import httpx

        amount = getattr(challenge, "amount", "0")
        currency = getattr(challenge, "currency", "usd")

        # Grant SPT via Sardis API (which enforces mandate limits)
        if self._sardis_url and self._mandate_id:
            try:
                sardis_key = os.getenv("SARDIS_API_KEY", "")
                async with httpx.AsyncClient(timeout=15) as client:
                    resp = await client.post(
                        f"{self._sardis_url}/api/v2/spt/grant",
                        headers={"Authorization": f"Bearer {sardis_key}"},
                        json={
                            "mandate_id": self._mandate_id,
                            "payment_method": self._payment_method,
                            "seller_network_id": self._network_id,
                        },
                    )
                    if resp.status_code == 201:
                        data = resp.json()
                        spt_id = data.get("stripe_spt_id") or data.get("token_id", "")
                        logger.info("Created SPT %s for %s %s", spt_id, amount, currency)
                        return StripeSPTCredential(spt_id=spt_id)
            except Exception as e:
                logger.warning("Failed to grant SPT via Sardis: %s", e)

        # Direct Stripe API fallback (test mode)
        if self._api_key:
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.post(
                        "https://api.stripe.com/v1/test_helpers/shared_payment/granted_tokens",
                        auth=(self._api_key, ""),
                        data={
                            "payment_method": self._payment_method,
                            "usage_limits[currency]": currency,
                            "usage_limits[max_amount]": str(int(float(amount) * 100)),
                        },
                    )
                    if resp.status_code == 200:
                        spt_id = resp.json().get("id", "")
                        return StripeSPTCredential(spt_id=spt_id)
            except Exception as e:
                logger.error("Stripe SPT creation failed: %s", e)

        raise RuntimeError("Cannot create Stripe SPT: no API key or Sardis API available")

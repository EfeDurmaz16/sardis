"""Stripe Connect Express provider for Sardis Connect.

Handles merchant onboarding, account status sync, and settlement
via Stripe Connect transfers + automatic payouts.

Environment variables:
    STRIPE_API_KEY: Platform secret key (sk_live_... or sk_test_...)
    SARDIS_STRIPE_CONNECT_WEBHOOK_SECRET: Webhook secret for Connect events
    SARDIS_CONNECT_RETURN_URL: Return URL after onboarding (default: https://app.sardis.sh/merchants/{merchant_id}/connect/complete)
    SARDIS_CONNECT_REFRESH_URL: Refresh URL for expired links (default: https://app.sardis.sh/merchants/{merchant_id}/connect/refresh)
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ConnectAccount:
    """Result of creating or retrieving a Stripe Connect Express account."""
    account_id: str
    charges_enabled: bool
    payouts_enabled: bool
    details_submitted: bool
    onboarding_state: str  # not_started | pending | complete | restricted | rejected
    disabled_reason: str | None
    current_deadline: datetime | None
    requirements_currently_due: list[str]
    requirements_past_due: list[str]


@dataclass(slots=True)
class AccountLink:
    """Stripe Account Link for merchant onboarding redirect."""
    url: str
    expires_at: datetime


@dataclass(slots=True)
class TransferResult:
    """Result of a Stripe Connect transfer."""
    transfer_id: str
    amount_cents: int
    currency: str
    destination: str


class StripeConnectProvider:
    """Stripe Connect Express integration for merchant onboarding and settlement."""

    def __init__(self, api_key: str | None = None) -> None:
        try:
            import stripe as stripe_mod
        except ImportError:
            raise ImportError(
                "Stripe SDK not installed. Install with: pip install stripe>=7.0.0"
            )

        self._api_key = api_key or os.environ.get("STRIPE_API_KEY")
        if not self._api_key:
            raise ValueError("Stripe API key required. Set STRIPE_API_KEY or pass api_key.")

        self._stripe = stripe_mod
        self._stripe.api_key = self._api_key
        self._is_test = self._api_key.startswith("sk_test_")

        self._return_url_template = os.environ.get(
            "SARDIS_CONNECT_RETURN_URL",
            "https://app.sardis.sh/merchants/{merchant_id}/connect/complete",
        )
        self._refresh_url_template = os.environ.get(
            "SARDIS_CONNECT_REFRESH_URL",
            "https://app.sardis.sh/merchants/{merchant_id}/connect/refresh",
        )

    async def create_express_account(
        self,
        *,
        email: str | None = None,
        business_name: str | None = None,
        country: str = "US",
        mcc_code: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> ConnectAccount:
        """Create a Stripe Connect Express account for a merchant."""
        import asyncio

        params: dict[str, Any] = {
            "type": "express",
            "country": country,
            "capabilities": {
                "card_payments": {"requested": True},
                "transfers": {"requested": True},
            },
        }
        if email:
            params["email"] = email
        if business_name:
            params["business_profile"] = {"name": business_name}
            if mcc_code:
                params["business_profile"]["mcc"] = mcc_code
        if metadata:
            params["metadata"] = metadata

        account = await asyncio.to_thread(self._stripe.Account.create, **params)
        return self._account_to_result(account)

    async def create_account_link(
        self,
        account_id: str,
        merchant_id: str,
        link_type: str = "account_onboarding",
    ) -> AccountLink:
        """Create an Account Link for onboarding or updating account info.

        Account Links are single-use and expire quickly (minutes, not hours).
        The refresh_url handler must create a new link and redirect.
        """
        import asyncio

        return_url = self._return_url_template.format(merchant_id=merchant_id)
        refresh_url = self._refresh_url_template.format(merchant_id=merchant_id)

        link = await asyncio.to_thread(
            self._stripe.AccountLink.create,
            account=account_id,
            refresh_url=refresh_url,
            return_url=return_url,
            type=link_type,
            collection_options={
                "fields": "eventually_due",
                "future_requirements": "include",
            },
        )
        return AccountLink(
            url=link.url,
            expires_at=datetime.fromtimestamp(link.expires_at, tz=UTC),
        )

    async def get_account_status(self, account_id: str) -> ConnectAccount:
        """Retrieve current status of a Connect Express account."""
        import asyncio

        account = await asyncio.to_thread(self._stripe.Account.retrieve, account_id)
        return self._account_to_result(account)

    async def create_transfer(
        self,
        *,
        account_id: str,
        amount_cents: int,
        currency: str = "usd",
        description: str | None = None,
        metadata: dict[str, str] | None = None,
        source_transaction: str | None = None,
        transfer_group: str | None = None,
    ) -> TransferResult:
        """Create a transfer to a connected account.

        For Sardis Connect settlement: after an agent pays via stablecoin,
        we transfer the equivalent fiat amount to the merchant's Stripe account.
        Stripe's automatic payout schedule then sends it to their bank.
        """
        import asyncio

        params: dict[str, Any] = {
            "amount": amount_cents,
            "currency": currency,
            "destination": account_id,
        }
        if description:
            params["description"] = description
        if metadata:
            params["metadata"] = metadata
        if source_transaction:
            params["source_transaction"] = source_transaction
        if transfer_group:
            params["transfer_group"] = transfer_group

        transfer = await asyncio.to_thread(self._stripe.Transfer.create, **params)
        return TransferResult(
            transfer_id=transfer.id,
            amount_cents=transfer.amount,
            currency=transfer.currency,
            destination=transfer.destination,
        )

    def verify_webhook_signature(
        self, payload: bytes, sig_header: str, secret: str | None = None
    ) -> dict[str, Any]:
        """Verify and parse a Stripe webhook event.

        Returns the parsed event dict. Raises on invalid signature.
        """
        webhook_secret = secret or os.environ.get("SARDIS_STRIPE_CONNECT_WEBHOOK_SECRET")
        if not webhook_secret:
            raise ValueError("Stripe Connect webhook secret not configured")

        event = self._stripe.Webhook.construct_event(
            payload.decode("utf-8") if isinstance(payload, bytes) else payload,
            sig_header,
            webhook_secret,
        )
        return event

    def _account_to_result(self, account: Any) -> ConnectAccount:
        """Map a Stripe Account object to our ConnectAccount dataclass."""
        reqs = getattr(account, "requirements", None)
        currently_due = list(reqs.currently_due) if reqs and reqs.currently_due else []
        past_due = list(reqs.past_due) if reqs and reqs.past_due else []
        disabled_reason = reqs.disabled_reason if reqs else None

        deadline = None
        if reqs and reqs.current_deadline:
            deadline = datetime.fromtimestamp(reqs.current_deadline, tz=UTC)

        # Determine onboarding state
        if disabled_reason and disabled_reason.startswith("rejected"):
            state = "rejected"
        elif disabled_reason or past_due:
            state = "restricted"
        elif account.charges_enabled and account.payouts_enabled:
            state = "complete"
        elif account.details_submitted:
            state = "pending"
        else:
            state = "not_started"

        return ConnectAccount(
            account_id=account.id,
            charges_enabled=account.charges_enabled,
            payouts_enabled=account.payouts_enabled,
            details_submitted=account.details_submitted,
            onboarding_state=state,
            disabled_reason=disabled_reason,
            current_deadline=deadline,
            requirements_currently_due=currently_due,
            requirements_past_due=past_due,
        )

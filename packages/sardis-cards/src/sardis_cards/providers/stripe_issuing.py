"""Stripe Issuing card provider implementation."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from datetime import datetime, timezone
from decimal import Decimal
from typing import Awaitable, Optional
import os

from .base import CardProvider
from ..models import Card, CardTransaction, CardType, CardStatus, TransactionStatus, FundingSource


class StripeIssuingProvider(CardProvider):
    """
    Stripe Issuing virtual card provider.

    Requires the 'stripe' extra: pip install sardis-cards[stripe]

    Features:
    - $0.10 per virtual card creation
    - Real-time authorization webhooks (< 3 second response)
    - Granular spending controls (per-tx, daily, monthly, merchant category)
    - Card funding from Issuing balance
    - Simulation mode for sandbox testing

    Environment variables:
        STRIPE_API_KEY: Secret API key for Stripe (sk_test_... or sk_live_...)
        STRIPE_WEBHOOK_SECRET: Webhook signing secret for authorization events
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        policy_evaluator: Optional[Callable[[str, Decimal, str, str], Awaitable[tuple[bool, str]]]] = None,
    ) -> None:
        try:
            import stripe
        except ImportError:
            raise ImportError(
                "Stripe SDK not installed. Install with: pip install sardis-cards[stripe]"
            )

        self._api_key = api_key or os.environ.get("STRIPE_API_KEY")
        if not self._api_key:
            raise ValueError("Stripe API key required. Set STRIPE_API_KEY or pass api_key.")

        self._webhook_secret = webhook_secret or os.environ.get("STRIPE_WEBHOOK_SECRET")
        self._is_test_mode = self._api_key.startswith("sk_test_")
        self._policy_evaluator = policy_evaluator

        # Initialize Stripe client
        self._stripe = stripe
        self._stripe.api_key = self._api_key

    @property
    def name(self) -> str:
        return "stripe_issuing"

    def _map_card_status(self, stripe_status: str) -> CardStatus:
        """Map Stripe card status to our CardStatus enum."""
        mapping = {
            "inactive": CardStatus.PENDING,
            "active": CardStatus.ACTIVE,
            "canceled": CardStatus.CANCELLED,
        }
        return mapping.get(stripe_status, CardStatus.PENDING)

    def _map_card_type(self, stripe_type: str) -> CardType:
        """Map Stripe card type to our CardType enum."""
        # Stripe doesn't have explicit card types, we infer from usage
        mapping = {
            "virtual": CardType.MULTI_USE,
            "physical": CardType.MULTI_USE,
        }
        return mapping.get(stripe_type, CardType.MULTI_USE)

    def _map_tx_status(self, stripe_status: str) -> TransactionStatus:
        """Map Stripe authorization status to our TransactionStatus enum."""
        mapping = {
            "pending": TransactionStatus.PENDING,
            "closed": TransactionStatus.SETTLED,
            "reversed": TransactionStatus.REVERSED,
        }
        return mapping.get(stripe_status, TransactionStatus.PENDING)

    def _stripe_card_to_model(self, stripe_card, wallet_id: str = "") -> Card:
        """Convert Stripe card object to our Card model."""
        # Extract spending controls
        spending_controls = stripe_card.get("spending_controls", {})
        spending_limits = spending_controls.get("spending_limits", [])

        # Parse spending limits
        limit_per_tx = Decimal("500.00")
        limit_daily = Decimal("2000.00")
        limit_monthly = Decimal("10000.00")

        for limit in spending_limits:
            amount = Decimal(str(limit.get("amount", 0) / 100))
            interval = limit.get("interval")

            if interval == "per_authorization":
                limit_per_tx = amount
            elif interval == "daily":
                limit_daily = amount
            elif interval == "monthly":
                limit_monthly = amount

        # Determine card status
        status = self._map_card_status(stripe_card.get("status", "inactive"))

        # Check if frozen (Stripe uses cancellation_reason = "lost" for temporary freeze)
        cancellation_reason = stripe_card.get("cancellation_reason")
        if status == CardStatus.CANCELLED and cancellation_reason == "lost":
            status = CardStatus.FROZEN

        return Card(
            card_id=f"card_{stripe_card['id'][5:21]}" if stripe_card['id'].startswith('ic_') else f"card_{stripe_card['id'][:16]}",
            wallet_id=wallet_id,
            provider=self.name,
            provider_card_id=stripe_card["id"],
            card_number_last4=stripe_card.get("last4", ""),
            expiry_month=stripe_card.get("exp_month", 0),
            expiry_year=stripe_card.get("exp_year", 0),
            card_type=self._map_card_type(stripe_card.get("type", "virtual")),
            status=status,
            funding_source=FundingSource.STABLECOIN,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
            created_at=datetime.fromtimestamp(stripe_card.get("created", 0), tz=timezone.utc),
        )

    def _stripe_auth_to_model(self, stripe_auth) -> CardTransaction:
        """Convert Stripe authorization object to our CardTransaction model."""
        # Determine status
        if stripe_auth.get("approved"):
            if stripe_auth.get("status") == "closed":
                status = TransactionStatus.SETTLED
            else:
                status = TransactionStatus.APPROVED
        else:
            status = TransactionStatus.DECLINED

        # Extract merchant data
        merchant_data = stripe_auth.get("merchant_data", {})

        return CardTransaction(
            transaction_id=f"ctx_{stripe_auth['id'][7:23]}" if stripe_auth['id'].startswith('iauth_') else f"ctx_{stripe_auth['id'][:16]}",
            card_id=stripe_auth.get("card", ""),
            provider_tx_id=stripe_auth["id"],
            amount=Decimal(str(stripe_auth.get("amount", 0) / 100)),
            currency=stripe_auth.get("currency", "usd").upper(),
            merchant_name=merchant_data.get("name", ""),
            merchant_category=merchant_data.get("category", ""),
            merchant_id=merchant_data.get("network_id", ""),
            status=status,
            decline_reason=stripe_auth.get("request_history", [{}])[-1].get("reason") if not stripe_auth.get("approved") else None,
            created_at=datetime.fromtimestamp(stripe_auth.get("created", 0), tz=timezone.utc),
        )

    @staticmethod
    def _split_name(full_name: str) -> tuple[str, str]:
        """Split a full name into first and last name parts."""
        parts = full_name.strip().split(None, 1)
        if len(parts) == 1:
            return parts[0], ""
        return parts[0], parts[1]

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
        cardholder_name: Optional[str] = None,
        cardholder_email: Optional[str] = None,
        cardholder_phone: Optional[str] = None,
        reuse_cardholder_id: Optional[str] = None,
    ) -> Card:
        # Build spending controls
        spending_limits = []

        if limit_per_tx > 0:
            spending_limits.append({
                "amount": int(limit_per_tx * 100),
                "interval": "per_authorization",
            })

        if limit_daily > 0:
            spending_limits.append({
                "amount": int(limit_daily * 100),
                "interval": "daily",
            })

        if limit_monthly > 0:
            spending_limits.append({
                "amount": int(limit_monthly * 100),
                "interval": "monthly",
            })

        spending_controls = {
            "spending_limits": spending_limits,
        }

        # Add merchant lock if specified
        if locked_merchant_id and card_type == CardType.MERCHANT_LOCKED:
            spending_controls["allowed_merchants"] = [locked_merchant_id]

        # No blocked categories by default — policy engine handles restrictions

        # Resolve cardholder: reuse existing or create a new one.
        # cardholder = the responsible human (org owner) who registered the agent.
        if reuse_cardholder_id:
            cardholder_id = reuse_cardholder_id
        else:
            # Resolve display values, falling back to "Sardis Agent" defaults for
            # backward compatibility when no real cardholder info is supplied.
            display_name = cardholder_name or "Sardis Agent"
            email = cardholder_email or f"agent-{wallet_id[:8]}@sardis.sh"
            phone = cardholder_phone or "+15555550100"
            first_name, last_name = self._split_name(display_name)
            if not last_name:
                last_name = "Agent"

            cardholder = await asyncio.to_thread(
                self._stripe.issuing.Cardholder.create,
                type="individual",
                name=display_name,
                email=email,
                phone_number=phone,
                individual={
                    "first_name": first_name,
                    "last_name": last_name,
                    "dob": {"day": 1, "month": 1, "year": 1990},
                },
                billing={
                    "address": {
                        "line1": "123 Main St",
                        "city": "San Francisco",
                        "state": "CA",
                        "postal_code": "94102",
                        "country": "US",
                    }
                },
                metadata={
                    "wallet_id": wallet_id,
                    "managed_by": "sardis",
                },
            )
            cardholder_id = cardholder.id

        # Create the card
        stripe_card = await asyncio.to_thread(
            self._stripe.issuing.Card.create,
            cardholder=cardholder_id,
            currency="usd",
            type="virtual",
            status="inactive",  # Activate after cardholder verification
            spending_controls=spending_controls,
            metadata={
                "wallet_id": wallet_id,
                "card_type": card_type.value,
                "managed_by": "sardis",
            },
        )

        card = self._stripe_card_to_model(stripe_card, wallet_id)
        card.limit_per_tx = limit_per_tx
        card.limit_daily = limit_daily
        card.limit_monthly = limit_monthly
        card.locked_merchant_id = locked_merchant_id
        card.status = CardStatus.ACTIVE
        card.activated_at = datetime.now(timezone.utc)

        return card

    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        try:
            stripe_card = await asyncio.to_thread(
                self._stripe.issuing.Card.retrieve, provider_card_id
            )
            return self._stripe_card_to_model(stripe_card)
        except Exception:
            return None

    async def activate_card(self, provider_card_id: str) -> Card:
        stripe_card = await asyncio.to_thread(
            self._stripe.issuing.Card.modify,
            provider_card_id,
            status="active",
        )
        card = self._stripe_card_to_model(stripe_card)
        card.activated_at = datetime.now(timezone.utc)
        return card

    async def freeze_card(self, provider_card_id: str) -> Card:
        # Stripe doesn't have a "freeze" state, we use cancel with reason "lost"
        # This allows us to distinguish from permanent cancellation
        stripe_card = await asyncio.to_thread(
            self._stripe.issuing.Card.modify,
            provider_card_id,
            status="canceled",
            cancellation_reason="lost",
        )
        card = self._stripe_card_to_model(stripe_card)
        card.status = CardStatus.FROZEN
        card.frozen_at = datetime.now(timezone.utc)
        return card

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        # Stripe doesn't support re-activating canceled cards
        # We need to create a replacement card
        # For now, raise an error - integrators should create a new card
        raise NotImplementedError(
            "Stripe Issuing does not support unfreezing cards. "
            "Create a new card instead via create_card()."
        )

    async def cancel_card(self, provider_card_id: str) -> Card:
        stripe_card = await asyncio.to_thread(
            self._stripe.issuing.Card.modify,
            provider_card_id,
            status="canceled",
            cancellation_reason="design_changed",  # Permanent cancellation
        )
        card = self._stripe_card_to_model(stripe_card)
        card.cancelled_at = datetime.now(timezone.utc)
        return card

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        # Get current card to preserve existing limits
        current_card = await self.get_card(provider_card_id)
        if not current_card:
            raise ValueError(f"Card not found: {provider_card_id}")

        # Build updated spending limits
        spending_limits = []

        per_tx = limit_per_tx or current_card.limit_per_tx
        daily = limit_daily or current_card.limit_daily
        monthly = limit_monthly or current_card.limit_monthly

        if per_tx > 0:
            spending_limits.append({
                "amount": int(per_tx * 100),
                "interval": "per_authorization",
            })

        if daily > 0:
            spending_limits.append({
                "amount": int(daily * 100),
                "interval": "daily",
            })

        if monthly > 0:
            spending_limits.append({
                "amount": int(monthly * 100),
                "interval": "monthly",
            })

        stripe_card = await asyncio.to_thread(
            self._stripe.issuing.Card.modify,
            provider_card_id,
            spending_controls={
                "spending_limits": spending_limits,
            },
        )

        card = self._stripe_card_to_model(stripe_card)
        card.limit_per_tx = per_tx
        card.limit_daily = daily
        card.limit_monthly = monthly

        return card

    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        """
        Fund a card via Stripe Issuing balance.

        Stripe Issuing uses account-level funding. All cards draw from
        the Issuing balance, which is separate from the main Stripe balance.

        For Sardis, the flow is:
        1. User deposits stablecoin to Sardis
        2. Sardis off-ramps to fiat via Bridge/Zero Hash
        3. Fiat is transferred to Stripe Issuing balance via Treasury
        4. Card spending limits control access to this balance

        This method handles step 4: ensuring the card has sufficient limits.
        The actual balance transfer happens via Stripe Treasury API.

        Args:
            provider_card_id: The Stripe card ID (ic_...)
            amount: Amount in USD to add to available balance
        """
        # Get current card state
        card = await self.get_card(provider_card_id)
        if not card:
            raise ValueError(f"Card not found: {provider_card_id}")

        # Update the card's daily limit to reflect new funding
        # This is a simplified approach - production systems should track
        # balance separately and enforce it via authorization webhooks
        new_daily_limit = card.limit_daily + amount

        updated_card = await self.update_limits(
            provider_card_id,
            limit_daily=new_daily_limit,
        )

        updated_card.funded_amount = card.funded_amount + amount

        return updated_card

    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        # List authorizations for this card
        stripe_auths = await asyncio.to_thread(
            self._stripe.issuing.Authorization.list,
            card=provider_card_id,
            limit=limit,
        )

        transactions = []
        for auth in stripe_auths.data:
            transactions.append(self._stripe_auth_to_model(auth))

        return transactions

    async def get_transaction(
        self,
        provider_tx_id: str,
    ) -> Optional[CardTransaction]:
        try:
            stripe_auth = await asyncio.to_thread(
                self._stripe.issuing.Authorization.retrieve, provider_tx_id
            )
            return self._stripe_auth_to_model(stripe_auth)
        except Exception:
            return None

    async def handle_authorization_webhook(
        self,
        payload: bytes,
        signature: str,
    ) -> dict:
        """
        Handle real-time authorization webhook from Stripe.

        Stripe sends issuing_authorization.request events in real-time
        when a card is used. We must respond within 3 seconds with
        approve or decline.

        Args:
            payload: Raw webhook payload bytes
            signature: Stripe signature header value

        Returns:
            Response dict to send back to Stripe: {"approved": bool}
        """
        if not self._webhook_secret:
            raise ValueError("Webhook secret not configured")

        try:
            # Verify webhook signature
            event = self._stripe.Webhook.construct_event(
                payload, signature, self._webhook_secret
            )
        except Exception as e:
            raise ValueError(f"Webhook signature verification failed: {e}")

        # Handle authorization request
        if event["type"] == "issuing_authorization.request":
            authorization = event["data"]["object"]

            # Extract authorization details
            card_id = authorization.get("card")
            amount = Decimal(str(authorization.get("amount", 0) / 100))
            merchant_data = authorization.get("merchant_data", {})
            merchant_id = merchant_data.get("network_id", "")
            mcc_code = merchant_data.get("category_code", "0000")
            merchant_name = merchant_data.get("name", "")

            # Get card details
            card = await self.get_card(card_id)
            if not card:
                return {"approved": False}

            # Invoke SpendingPolicy engine if a policy_evaluator is wired in.
            # This check happens BEFORE the basic card.can_authorize() so that
            # policy denials are surfaced with a meaningful reason.
            if self._policy_evaluator is not None:
                policy_ok, policy_reason = await self._policy_evaluator(
                    card.wallet_id, amount, mcc_code, merchant_name
                )
                if not policy_ok:
                    return {
                        "approved": False,
                        "metadata": {
                            "wallet_id": card.wallet_id,
                            "reason": policy_reason,
                        },
                    }

            # Check authorization rules
            can_authorize, reason = card.can_authorize(amount, merchant_id)

            return {
                "approved": can_authorize,
                "metadata": {
                    "wallet_id": card.wallet_id,
                    "reason": reason if not can_authorize else "OK",
                },
            }

        return {"approved": False}

    async def simulate_authorization(
        self,
        provider_card_id: str,
        amount: Decimal,
        merchant_name: str = "TEST MERCHANT",
        merchant_category: str = "5812",  # Restaurant
    ) -> CardTransaction:
        """
        Simulate a card authorization (test mode only).

        Useful for testing card functionality without real transactions.
        """
        if not self._is_test_mode:
            raise ValueError("Simulations only available in test mode")

        # Create test authorization
        stripe_auth = await asyncio.to_thread(
            self._stripe.issuing.Authorization.create,
            card=provider_card_id,
            amount=int(amount * 100),
            currency="usd",
            merchant_data={
                "name": merchant_name,
                "category": merchant_category,
            },
        )

        return self._stripe_auth_to_model(stripe_auth)

    async def get_issuing_balance(self) -> Decimal:
        """
        Get the available Stripe Issuing balance.

        This is the total funds available for all cards to spend.
        Used for reconciliation and balance monitoring.
        """
        try:
            balance = await asyncio.to_thread(
                self._stripe.Balance.retrieve
            )

            # Issuing balance is tracked separately
            issuing_balance = balance.get("issuing", {})
            available = issuing_balance.get("available", [])

            # Sum all available amounts (usually just USD)
            total = Decimal("0")
            for balance_item in available:
                if balance_item.get("currency") == "usd":
                    total += Decimal(str(balance_item.get("amount", 0) / 100))

            return total
        except Exception:
            return Decimal("0")

    async def provision_apple_pay(self, provider_card_id: str) -> dict:
        """Create Apple Pay provisioning data for a Sardis-issued card.

        Returns an ephemeral key and provisioning payload that a mobile
        SDK uses to add the card to Apple Wallet via push provisioning.
        """
        import stripe
        stripe.api_key = self._api_key

        # Create an ephemeral key scoped to the Issuing card
        ephemeral_key = stripe.EphemeralKey.create(
            issuing_card=provider_card_id,
            stripe_version="2024-12-18.acacia",
        )

        return {
            "provider": "stripe_issuing",
            "card_id": provider_card_id,
            "wallet_type": "apple_pay",
            "ephemeral_key": ephemeral_key.to_dict(),
            "provisioning_data": {
                "card_id": provider_card_id,
                "platform": "ios",
            },
        }

    async def provision_google_pay(self, provider_card_id: str) -> dict:
        """Create Google Pay provisioning data for a Sardis-issued card.

        Returns a push provisioning object that a mobile SDK uses
        to add the card to Google Wallet.
        """
        import stripe
        stripe.api_key = self._api_key

        # Create an ephemeral key scoped to the Issuing card
        ephemeral_key = stripe.EphemeralKey.create(
            issuing_card=provider_card_id,
            stripe_version="2024-12-18.acacia",
        )

        return {
            "provider": "stripe_issuing",
            "card_id": provider_card_id,
            "wallet_type": "google_pay",
            "ephemeral_key": ephemeral_key.to_dict(),
            "provisioning_data": {
                "card_id": provider_card_id,
                "platform": "android",
            },
        }

    async def reveal_card_details(
        self,
        provider_card_id: str,
        *,
        reason: str = "secure_checkout_executor",
    ) -> dict:
        """
        Stripe card detail reveal is intentionally unsupported in this backend path.

        Stripe Issuing card number retrieval is designed for client-side ephemeral key
        flows (e.g., Issuing Elements), not long-lived server-side PAN handling.
        """
        raise NotImplementedError(
            "Stripe Issuing PAN reveal is not enabled on the server path. "
            "Use Stripe Issuing Elements or a dedicated PCI-controlled executor."
        )

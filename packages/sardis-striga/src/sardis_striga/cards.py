"""Striga card provider — EEA virtual Visa (EUR-denominated)."""
from __future__ import annotations

import logging
from datetime import UTC, datetime
from decimal import Decimal

from sardis_cards.models import Card, CardStatus, CardTransaction, CardType, TransactionStatus

from .client import StrigaClient
from .models import StrigaCardStatus

logger = logging.getLogger(__name__)

# Import ABC conditionally to avoid circular imports at module level
from sardis_cards.providers.base import CardProvider


class StrigaCardProvider(CardProvider):
    """
    Striga card provider for EEA virtual Visa cards.

    Issues EUR-denominated virtual Visa cards via Striga API.
    Striga requires KYC-linked cardholders for compliance.
    Supports Apple Pay / Google Pay tokenization.
    """

    def __init__(self, client: StrigaClient, default_user_id: str = ""):
        self._client = client
        self._default_user_id = default_user_id

    @property
    def name(self) -> str:
        return "striga"

    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: str | None = None,
    ) -> Card:
        """Create a EUR-denominated virtual Visa card via Striga."""
        result = await self._client.request(
            "POST",
            "/cards",
            {
                "userId": self._default_user_id,
                "walletId": wallet_id,
                "cardType": "virtual",
                "currency": "EUR",
                "spendingLimit": int(limit_per_tx * 100),
                "dailyLimit": int(limit_daily * 100),
                "monthlyLimit": int(limit_monthly * 100),
            },
        )

        return Card(
            card_id=result.get("cardId", ""),
            wallet_id=wallet_id,
            provider="striga",
            provider_card_id=result.get("cardId", ""),
            card_number_last4=result.get("lastFour", ""),
            expiry_month=result.get("expiryMonth", 0),
            expiry_year=result.get("expiryYear", 0),
            card_type=card_type,
            status=CardStatus.PENDING,
            locked_merchant_id=locked_merchant_id,
            limit_per_tx=limit_per_tx,
            limit_daily=limit_daily,
            limit_monthly=limit_monthly,
        )

    async def get_card(self, provider_card_id: str) -> Card | None:
        """Get card details from Striga."""
        try:
            result = await self._client.request("GET", f"/cards/{provider_card_id}")
        except Exception:
            return None

        return self._parse_card(result)

    async def activate_card(self, provider_card_id: str) -> Card:
        """Activate a pending Striga card."""
        result = await self._client.request(
            "POST", f"/cards/{provider_card_id}/activate"
        )
        return self._parse_card(result)

    async def freeze_card(self, provider_card_id: str) -> Card:
        """Freeze a Striga card."""
        result = await self._client.request(
            "POST", f"/cards/{provider_card_id}/freeze"
        )
        return self._parse_card(result)

    async def unfreeze_card(self, provider_card_id: str) -> Card:
        """Unfreeze a Striga card."""
        result = await self._client.request(
            "POST", f"/cards/{provider_card_id}/unfreeze"
        )
        return self._parse_card(result)

    async def cancel_card(self, provider_card_id: str) -> Card:
        """Cancel a Striga card permanently."""
        result = await self._client.request(
            "POST", f"/cards/{provider_card_id}/cancel"
        )
        return self._parse_card(result)

    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Decimal | None = None,
        limit_daily: Decimal | None = None,
        limit_monthly: Decimal | None = None,
    ) -> Card:
        """Update spending limits on a Striga card."""
        body: dict = {}
        if limit_per_tx is not None:
            body["spendingLimit"] = int(limit_per_tx * 100)
        if limit_daily is not None:
            body["dailyLimit"] = int(limit_daily * 100)
        if limit_monthly is not None:
            body["monthlyLimit"] = int(limit_monthly * 100)

        result = await self._client.request(
            "PUT", f"/cards/{provider_card_id}/limits", body
        )
        return self._parse_card(result)

    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        """Fund a Striga card (EUR)."""
        result = await self._client.request(
            "POST",
            f"/cards/{provider_card_id}/fund",
            {"amount": int(amount * 100), "currency": "EUR"},
        )
        return self._parse_card(result)

    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        """List transactions for a Striga card."""
        result = await self._client.request(
            "GET",
            f"/cards/{provider_card_id}/transactions",
            params={"limit": limit, "offset": offset},
        )

        transactions = []
        for tx_data in result.get("transactions", []):
            transactions.append(self._parse_transaction(tx_data))
        return transactions

    async def get_transaction(
        self,
        provider_tx_id: str,
    ) -> CardTransaction | None:
        """Get a specific transaction from Striga."""
        try:
            result = await self._client.request(
                "GET", f"/transactions/{provider_tx_id}"
            )
            return self._parse_transaction(result)
        except Exception:
            return None

    # --- Apple Pay / Google Pay tokenization ---

    async def create_apple_pay_token(self, provider_card_id: str) -> dict:
        """Get Apple Pay provisioning data for a Striga card."""
        return await self._client.request(
            "POST", f"/cards/{provider_card_id}/tokenize/apple-pay"
        )

    async def create_google_pay_token(self, provider_card_id: str) -> dict:
        """Get Google Pay provisioning data for a Striga card."""
        return await self._client.request(
            "POST", f"/cards/{provider_card_id}/tokenize/google-pay"
        )

    # --- Internal helpers ---

    def _parse_card(self, data: dict) -> Card:
        """Parse Striga card response into Card model."""
        status_map = {
            "created": CardStatus.PENDING,
            "active": CardStatus.ACTIVE,
            "frozen": CardStatus.FROZEN,
            "cancelled": CardStatus.CANCELLED,
            "expired": CardStatus.EXPIRED,
        }

        raw_status = data.get("status", "created")
        card_status = status_map.get(raw_status, CardStatus.PENDING)

        return Card(
            card_id=data.get("cardId", ""),
            wallet_id=data.get("walletId", ""),
            provider="striga",
            provider_card_id=data.get("cardId", ""),
            card_number_last4=data.get("lastFour", ""),
            expiry_month=data.get("expiryMonth", 0),
            expiry_year=data.get("expiryYear", 0),
            card_type=CardType.MULTI_USE,
            status=card_status,
            limit_per_tx=Decimal(str(data.get("spendingLimit", 0))) / 100,
            limit_daily=Decimal(str(data.get("dailyLimit", 0))) / 100,
            limit_monthly=Decimal(str(data.get("monthlyLimit", 0))) / 100,
            funded_amount=Decimal(str(data.get("balance", 0))) / 100,
        )

    def _parse_transaction(self, data: dict) -> CardTransaction:
        """Parse Striga transaction response into CardTransaction model."""
        status_map = {
            "pending": TransactionStatus.PENDING,
            "approved": TransactionStatus.APPROVED,
            "settled": TransactionStatus.SETTLED,
            "declined": TransactionStatus.DECLINED,
            "reversed": TransactionStatus.REVERSED,
        }

        raw_status = data.get("status", "pending")
        tx_status = status_map.get(raw_status, TransactionStatus.PENDING)

        return CardTransaction(
            transaction_id=data.get("transactionId", ""),
            card_id=data.get("cardId", ""),
            provider_tx_id=data.get("transactionId", ""),
            amount=Decimal(str(data.get("amount", 0))) / 100,
            currency=data.get("currency", "EUR"),
            merchant_name=data.get("merchantName", ""),
            merchant_category=data.get("merchantMcc", ""),
            merchant_id=data.get("merchantId", ""),
            status=tx_status,
        )

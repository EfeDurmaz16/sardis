"""Lithic card provider implementation."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import os

from .base import CardProvider
from ..models import Card, CardTransaction, CardType, CardStatus, TransactionStatus, FundingSource


class LithicProvider(CardProvider):
    """
    Lithic virtual card provider.
    
    Requires the 'lithic' extra: pip install sardis-cards[lithic]
    
    Environment variables:
        LITHIC_API_KEY: API key for Lithic
        LITHIC_ENVIRONMENT: 'sandbox' or 'production' (default: sandbox)
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        environment: Optional[str] = None,
    ) -> None:
        try:
            import lithic
        except ImportError:
            raise ImportError(
                "Lithic SDK not installed. Install with: pip install sardis-cards[lithic]"
            )
        
        self._api_key = api_key or os.environ.get("LITHIC_API_KEY")
        if not self._api_key:
            raise ValueError("Lithic API key required. Set LITHIC_API_KEY or pass api_key.")
        
        self._environment = environment or os.environ.get("LITHIC_ENVIRONMENT", "sandbox")
        
        # Initialize Lithic client
        self._client = lithic.Lithic(
            api_key=self._api_key,
            environment=self._environment,
        )
    
    @property
    def name(self) -> str:
        return "lithic"
    
    def _map_card_status(self, lithic_state: str) -> CardStatus:
        """Map Lithic card state to our CardStatus enum."""
        mapping = {
            "PENDING_ACTIVATION": CardStatus.PENDING,
            "OPEN": CardStatus.ACTIVE,
            "PAUSED": CardStatus.FROZEN,
            "CLOSED": CardStatus.CANCELLED,
        }
        return mapping.get(lithic_state, CardStatus.PENDING)
    
    def _map_card_type(self, lithic_type: str) -> CardType:
        """Map Lithic card type to our CardType enum."""
        mapping = {
            "SINGLE_USE": CardType.SINGLE_USE,
            "MERCHANT_LOCKED": CardType.MERCHANT_LOCKED,
            "UNLOCKED": CardType.MULTI_USE,
        }
        return mapping.get(lithic_type, CardType.MULTI_USE)
    
    def _map_tx_status(self, lithic_status: str) -> TransactionStatus:
        """Map Lithic transaction status to our TransactionStatus enum."""
        mapping = {
            "PENDING": TransactionStatus.PENDING,
            "APPROVED": TransactionStatus.APPROVED,
            "DECLINED": TransactionStatus.DECLINED,
            "REVERSED": TransactionStatus.REVERSED,
            "SETTLED": TransactionStatus.SETTLED,
        }
        return mapping.get(lithic_status, TransactionStatus.PENDING)
    
    def _lithic_card_to_model(self, lithic_card, wallet_id: str = "") -> Card:
        """Convert Lithic card object to our Card model."""
        return Card(
            card_id=f"card_{lithic_card.token[:16]}",
            wallet_id=wallet_id,
            provider=self.name,
            provider_card_id=lithic_card.token,
            card_number_last4=lithic_card.last_four,
            expiry_month=lithic_card.exp_month,
            expiry_year=lithic_card.exp_year,
            card_type=self._map_card_type(lithic_card.type),
            status=self._map_card_status(lithic_card.state),
            funding_source=FundingSource.STABLECOIN,
            limit_per_tx=Decimal(str(lithic_card.spend_limit / 100)) if lithic_card.spend_limit else Decimal("500"),
            limit_daily=Decimal(str(lithic_card.spend_limit / 100)) if lithic_card.spend_limit else Decimal("2000"),
            limit_monthly=Decimal("10000"),
        )
    
    def _lithic_tx_to_model(self, lithic_tx) -> CardTransaction:
        """Convert Lithic transaction object to our CardTransaction model."""
        return CardTransaction(
            transaction_id=f"ctx_{lithic_tx.token[:16]}",
            card_id=lithic_tx.card.token if lithic_tx.card else "",
            provider_tx_id=lithic_tx.token,
            amount=Decimal(str(lithic_tx.amount / 100)),
            currency=lithic_tx.merchant.currency if lithic_tx.merchant else "USD",
            merchant_name=lithic_tx.merchant.descriptor if lithic_tx.merchant else "",
            merchant_category=lithic_tx.merchant.mcc if lithic_tx.merchant else "",
            status=self._map_tx_status(lithic_tx.status),
            created_at=lithic_tx.created or datetime.now(timezone.utc),
        )
    
    async def create_card(
        self,
        wallet_id: str,
        card_type: CardType,
        limit_per_tx: Decimal,
        limit_daily: Decimal,
        limit_monthly: Decimal,
        locked_merchant_id: Optional[str] = None,
    ) -> Card:
        # Map our card type to Lithic type
        lithic_type = {
            CardType.SINGLE_USE: "SINGLE_USE",
            CardType.MULTI_USE: "UNLOCKED",
            CardType.MERCHANT_LOCKED: "MERCHANT_LOCKED",
        }.get(card_type, "UNLOCKED")
        
        # Convert limit to cents
        spend_limit = int(limit_daily * 100)
        
        lithic_card = self._client.cards.create(
            type=lithic_type,
            spend_limit=spend_limit,
            spend_limit_duration="TRANSACTION",
            memo=f"Sardis wallet: {wallet_id}",
        )
        
        card = self._lithic_card_to_model(lithic_card, wallet_id)
        card.limit_per_tx = limit_per_tx
        card.limit_daily = limit_daily
        card.limit_monthly = limit_monthly
        card.locked_merchant_id = locked_merchant_id
        
        return card
    
    async def get_card(self, provider_card_id: str) -> Optional[Card]:
        try:
            lithic_card = self._client.cards.retrieve(provider_card_id)
            return self._lithic_card_to_model(lithic_card)
        except Exception:
            return None
    
    async def activate_card(self, provider_card_id: str) -> Card:
        lithic_card = self._client.cards.update(
            provider_card_id,
            state="OPEN",
        )
        card = self._lithic_card_to_model(lithic_card)
        card.activated_at = datetime.now(timezone.utc)
        return card
    
    async def freeze_card(self, provider_card_id: str) -> Card:
        lithic_card = self._client.cards.update(
            provider_card_id,
            state="PAUSED",
        )
        card = self._lithic_card_to_model(lithic_card)
        card.frozen_at = datetime.now(timezone.utc)
        return card
    
    async def unfreeze_card(self, provider_card_id: str) -> Card:
        lithic_card = self._client.cards.update(
            provider_card_id,
            state="OPEN",
        )
        return self._lithic_card_to_model(lithic_card)
    
    async def cancel_card(self, provider_card_id: str) -> Card:
        lithic_card = self._client.cards.update(
            provider_card_id,
            state="CLOSED",
        )
        card = self._lithic_card_to_model(lithic_card)
        card.cancelled_at = datetime.now(timezone.utc)
        return card
    
    async def update_limits(
        self,
        provider_card_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_daily: Optional[Decimal] = None,
        limit_monthly: Optional[Decimal] = None,
    ) -> Card:
        # Lithic uses a single spend_limit, we use the daily limit
        spend_limit = int((limit_daily or Decimal("2000")) * 100)
        
        lithic_card = self._client.cards.update(
            provider_card_id,
            spend_limit=spend_limit,
        )
        
        card = self._lithic_card_to_model(lithic_card)
        if limit_per_tx:
            card.limit_per_tx = limit_per_tx
        if limit_daily:
            card.limit_daily = limit_daily
        if limit_monthly:
            card.limit_monthly = limit_monthly
        
        return card
    
    async def fund_card(
        self,
        provider_card_id: str,
        amount: Decimal,
    ) -> Card:
        # Lithic funding is typically done at the account level
        # For now, we just return the card with updated funded_amount
        card = await self.get_card(provider_card_id)
        if card:
            card.funded_amount += amount
        return card
    
    async def list_transactions(
        self,
        provider_card_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[CardTransaction]:
        # Lithic uses pagination differently
        lithic_txs = self._client.transactions.list(
            card_token=provider_card_id,
            page_size=limit,
        )
        
        return [self._lithic_tx_to_model(tx) for tx in lithic_txs]
    
    async def get_transaction(
        self,
        provider_tx_id: str,
    ) -> Optional[CardTransaction]:
        try:
            lithic_tx = self._client.transactions.retrieve(provider_tx_id)
            return self._lithic_tx_to_model(lithic_tx)
        except Exception:
            return None

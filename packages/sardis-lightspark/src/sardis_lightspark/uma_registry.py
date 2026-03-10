"""UMA registry — maps wallet_id to UMA address, resolves agents by UMA."""
from __future__ import annotations

import logging
from typing import Any

from .client import GridClient
from .config import LightsparkConfig
from .models import UMAAddress, UMAAddressStatus
from .uma import UMAService

logger = logging.getLogger(__name__)


class UMARegistry:
    """
    Registry for UMA addresses mapped to Sardis wallets.

    Provides:
    - wallet_id → UMA address mapping
    - UMA address → wallet resolution
    - Incoming payment handling
    """

    def __init__(self, uma_service: UMAService):
        self._uma = uma_service
        self._wallet_to_uma: dict[str, UMAAddress] = {}
        self._address_to_wallet: dict[str, str] = {}

    async def register_agent(
        self,
        wallet_id: str,
        agent_id: str,
        currency: str = "USD",
    ) -> UMAAddress:
        """
        Register a UMA address for an agent wallet.

        Creates $<agent_id>@sardis.sh and stores the mapping.

        Args:
            wallet_id: Sardis wallet ID
            agent_id: Agent identifier
            currency: Default currency

        Returns:
            Created UMAAddress
        """
        address = await self._uma.create_address(
            wallet_id=wallet_id,
            agent_id=agent_id,
            currency=currency,
        )

        self._wallet_to_uma[wallet_id] = address
        self._address_to_wallet[address.address] = wallet_id

        logger.info(f"Registered UMA address {address.address} for wallet {wallet_id}")
        return address

    def resolve_wallet(self, uma_address: str) -> str | None:
        """
        Resolve a UMA address to a wallet ID.

        Args:
            uma_address: UMA address to resolve

        Returns:
            wallet_id if found, None otherwise
        """
        return self._address_to_wallet.get(uma_address)

    def get_uma_address(self, wallet_id: str) -> UMAAddress | None:
        """Get the UMA address for a wallet."""
        return self._wallet_to_uma.get(wallet_id)

    async def handle_incoming_payment(
        self,
        uma_address: str,
        amount_cents: int,
        currency: str,
        sender_address: str | None = None,
    ) -> dict[str, Any]:
        """
        Handle an incoming UMA payment.

        Resolves the recipient wallet and returns processing info.

        Args:
            uma_address: Recipient UMA address
            amount_cents: Payment amount in cents
            currency: Payment currency
            sender_address: Optional sender UMA address

        Returns:
            Dict with wallet_id and processing status
        """
        wallet_id = self.resolve_wallet(uma_address)
        if not wallet_id:
            logger.warning(f"No wallet found for UMA address: {uma_address}")
            return {
                "status": "rejected",
                "reason": "unknown_address",
                "uma_address": uma_address,
            }

        logger.info(
            f"Incoming UMA payment: {uma_address} <- {sender_address or 'unknown'}, "
            f"amount={amount_cents} {currency}"
        )

        return {
            "status": "accepted",
            "wallet_id": wallet_id,
            "uma_address": uma_address,
            "amount_cents": amount_cents,
            "currency": currency,
            "sender_address": sender_address,
        }

    def list_registered(self) -> list[UMAAddress]:
        """List all registered UMA addresses."""
        return list(self._wallet_to_uma.values())

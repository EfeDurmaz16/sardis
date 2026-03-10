"""Lightspark UMA address management — $agent@sardis.sh."""
from __future__ import annotations

import logging
from typing import Any

from .client import GridClient
from .config import LightsparkConfig
from .exceptions import GridUMAResolutionError
from .models import UMAAddress, UMAAddressStatus

logger = logging.getLogger(__name__)


class UMAService:
    """
    UMA address management for Sardis agents.

    Creates and manages UMA addresses ($agent_id@sardis.sh) for
    agent-to-agent payments via Lightspark Grid.
    """

    def __init__(self, client: GridClient, config: LightsparkConfig):
        self._client = client
        self._domain = config.uma_domain

    async def create_address(
        self,
        wallet_id: str,
        agent_id: str,
        currency: str = "USD",
    ) -> UMAAddress:
        """
        Create a UMA address for an agent.

        Format: $<agent_id>@sardis.sh

        Args:
            wallet_id: Sardis wallet ID to link
            agent_id: Agent identifier (becomes local part)
            currency: Default currency for receiving payments

        Returns:
            UMAAddress with the created address
        """
        address = f"${agent_id}@{self._domain}"

        result = await self._client.request(
            "POST",
            "/uma/addresses",
            {
                "address": address,
                "walletId": wallet_id,
                "currency": currency.upper(),
            },
        )

        return UMAAddress(
            uma_id=result.get("id", result.get("umaId", "")),
            address=address,
            wallet_id=wallet_id,
            currency=currency.upper(),
            status=UMAAddressStatus.ACTIVE,
        )

    async def resolve_address(self, uma_address: str) -> UMAAddress:
        """
        Resolve a UMA address to its details.

        Args:
            uma_address: UMA address to resolve (e.g., $agent@sardis.sh)

        Returns:
            UMAAddress with resolved details

        Raises:
            GridUMAResolutionError: If address cannot be resolved
        """
        try:
            result = await self._client.request(
                "GET",
                "/uma/resolve",
                params={"address": uma_address},
            )
        except Exception as e:
            raise GridUMAResolutionError(
                f"Failed to resolve UMA address: {uma_address}"
            ) from e

        return UMAAddress(
            uma_id=result.get("id", ""),
            address=uma_address,
            wallet_id=result.get("walletId", ""),
            user_id=result.get("userId"),
            currency=result.get("currency", "USD"),
            status=UMAAddressStatus.ACTIVE,
        )

    async def send_payment(
        self,
        from_wallet_id: str,
        to_address: str,
        amount_cents: int,
        currency: str = "USD",
        reference: str | None = None,
    ) -> dict[str, Any]:
        """
        Send payment to a UMA address.

        Args:
            from_wallet_id: Source wallet ID
            to_address: Destination UMA address
            amount_cents: Amount in cents
            currency: Currency code
            reference: Optional payment reference

        Returns:
            Transfer result with transaction ID
        """
        body: dict[str, Any] = {
            "fromWalletId": from_wallet_id,
            "toAddress": to_address,
            "amount": amount_cents,
            "currency": currency.upper(),
        }
        if reference:
            body["reference"] = reference

        return await self._client.request("POST", "/uma/send", body)

    async def get_address(self, wallet_id: str) -> UMAAddress | None:
        """Get UMA address for a wallet."""
        try:
            result = await self._client.request(
                "GET", f"/uma/addresses/wallet/{wallet_id}"
            )
            return UMAAddress(
                uma_id=result.get("id", ""),
                address=result.get("address", ""),
                wallet_id=wallet_id,
                currency=result.get("currency", "USD"),
                status=UMAAddressStatus.ACTIVE,
            )
        except Exception:
            return None

    async def deactivate_address(self, uma_id: str) -> bool:
        """Deactivate a UMA address."""
        try:
            await self._client.request("POST", f"/uma/addresses/{uma_id}/deactivate")
            return True
        except Exception as e:
            logger.error(f"Failed to deactivate UMA address {uma_id}: {e}")
            return False

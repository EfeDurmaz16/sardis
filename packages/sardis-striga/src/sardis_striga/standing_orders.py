"""Striga standing orders — recurring swap/withdrawal automation."""
from __future__ import annotations

import logging
from typing import Any

from .client import StrigaClient
from .models import StandingOrder, StandingOrderFrequency, StandingOrderStatus

logger = logging.getLogger(__name__)


class StrigaStandingOrderManager:
    """
    Manages recurring standing orders via Striga API.

    Supports:
    - Recurring EURC→EUR swaps
    - Recurring SEPA withdrawals
    - Subscription-to-standing-order sync
    """

    def __init__(self, client: StrigaClient):
        self._client = client

    async def create_standing_order(
        self,
        user_id: str,
        wallet_id: str,
        source_currency: str,
        target_currency: str,
        amount_cents: int,
        frequency: StandingOrderFrequency = StandingOrderFrequency.MONTHLY,
    ) -> StandingOrder:
        """Create a new standing order for recurring swaps/withdrawals."""
        result = await self._client.request(
            "POST",
            "/wallets/standing-orders",
            {
                "userId": user_id,
                "walletId": wallet_id,
                "sourceCurrency": source_currency,
                "targetCurrency": target_currency,
                "amount": amount_cents,
                "frequency": frequency.value,
            },
        )

        return self._parse_standing_order(result)

    async def get_standing_order(self, order_id: str) -> StandingOrder | None:
        """Get standing order details."""
        try:
            result = await self._client.request(
                "GET", f"/wallets/standing-orders/{order_id}"
            )
            return self._parse_standing_order(result)
        except Exception:
            return None

    async def cancel_standing_order(self, order_id: str) -> bool:
        """Cancel a standing order."""
        try:
            await self._client.request(
                "POST", f"/wallets/standing-orders/{order_id}/cancel"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to cancel standing order {order_id}: {e}")
            return False

    async def pause_standing_order(self, order_id: str) -> bool:
        """Pause a standing order."""
        try:
            await self._client.request(
                "POST", f"/wallets/standing-orders/{order_id}/pause"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to pause standing order {order_id}: {e}")
            return False

    async def resume_standing_order(self, order_id: str) -> bool:
        """Resume a paused standing order."""
        try:
            await self._client.request(
                "POST", f"/wallets/standing-orders/{order_id}/resume"
            )
            return True
        except Exception as e:
            logger.error(f"Failed to resume standing order {order_id}: {e}")
            return False

    async def list_standing_orders(
        self,
        user_id: str,
        wallet_id: str | None = None,
    ) -> list[StandingOrder]:
        """List standing orders for a user/wallet."""
        params: dict[str, Any] = {"userId": user_id}
        if wallet_id:
            params["walletId"] = wallet_id

        result = await self._client.request(
            "GET", "/wallets/standing-orders", params=params
        )

        return [
            self._parse_standing_order(order)
            for order in result.get("standingOrders", [])
        ]

    async def sync_subscription_to_standing_order(
        self,
        user_id: str,
        wallet_id: str,
        subscription_amount_cents: int,
        subscription_currency: str,
        billing_cycle: str,
    ) -> StandingOrder:
        """
        Sync a Sardis subscription to a Striga standing order.

        Creates or updates a standing order that matches the subscription's
        billing cycle and amount.
        """
        frequency_map = {
            "weekly": StandingOrderFrequency.WEEKLY,
            "monthly": StandingOrderFrequency.MONTHLY,
            "quarterly": StandingOrderFrequency.MONTHLY,  # Execute monthly, 3x
            "annual": StandingOrderFrequency.MONTHLY,  # Execute monthly, 12x
        }

        frequency = frequency_map.get(billing_cycle, StandingOrderFrequency.MONTHLY)

        return await self.create_standing_order(
            user_id=user_id,
            wallet_id=wallet_id,
            source_currency="EURC",
            target_currency=subscription_currency,
            amount_cents=subscription_amount_cents,
            frequency=frequency,
        )

    def _parse_standing_order(self, data: dict[str, Any]) -> StandingOrder:
        """Parse Striga standing order response."""
        from datetime import UTC, datetime

        status_map = {
            "active": StandingOrderStatus.ACTIVE,
            "paused": StandingOrderStatus.PAUSED,
            "cancelled": StandingOrderStatus.CANCELLED,
            "completed": StandingOrderStatus.COMPLETED,
        }

        freq_map = {
            "daily": StandingOrderFrequency.DAILY,
            "weekly": StandingOrderFrequency.WEEKLY,
            "monthly": StandingOrderFrequency.MONTHLY,
        }

        return StandingOrder(
            order_id=data.get("orderId", data.get("id", "")),
            wallet_id=data.get("walletId", ""),
            user_id=data.get("userId", ""),
            frequency=freq_map.get(data.get("frequency", "monthly"), StandingOrderFrequency.MONTHLY),
            status=status_map.get(data.get("status", "active"), StandingOrderStatus.ACTIVE),
            source_currency=data.get("sourceCurrency", "EURC"),
            target_currency=data.get("targetCurrency", "EUR"),
            amount_cents=int(data.get("amount", 0)),
            execution_count=int(data.get("executionCount", 0)),
        )

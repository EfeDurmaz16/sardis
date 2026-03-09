"""
Transactions resource for Sardis SDK.

This module provides both async and sync interfaces for transaction operations.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from pydantic import BaseModel

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from decimal import Decimal

    from ..client import TimeoutConfig


class GasEstimate(BaseModel):
    """Gas estimation result."""

    gas_limit: int
    gas_price_gwei: Decimal
    max_fee_gwei: Decimal
    max_priority_fee_gwei: Decimal
    estimated_cost_wei: int
    estimated_cost_usd: Decimal | None = None


class TransactionStatus(BaseModel):
    """Transaction status."""

    tx_hash: str
    chain: str
    status: str  # pending, submitted, confirming, confirmed, failed
    block_number: int | None = None
    confirmations: int = 0


class ChainInfo(BaseModel):
    """Chain information."""

    name: str
    chain_id: int
    native_token: str
    block_time: int
    explorer: str


class AsyncTransactionsResource(AsyncBaseResource):
    """Async resource for transaction operations.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # List supported chains
            chains = await client.transactions.list_chains()

            # Estimate gas
            estimate = await client.transactions.estimate_gas(
                chain="base",
                to_address="0x...",
                amount=Decimal("100.00"),
            )
        ```
    """

    async def list_chains(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[ChainInfo]:
        """List supported blockchain networks.

        Args:
            timeout: Optional request timeout

        Returns:
            List of chain information
        """
        response = await self._get("/api/v2/transactions/chains", timeout=timeout)
        return [ChainInfo.model_validate(c) for c in response.get("chains", [])]

    async def estimate_gas(
        self,
        chain: str,
        to_address: str,
        amount: Decimal,
        token: str = "USDC",
        timeout: float | TimeoutConfig | None = None,
    ) -> GasEstimate:
        """Estimate gas for a transaction.

        Args:
            chain: Target chain (e.g., "base_sepolia")
            to_address: Recipient address
            amount: Amount to send
            token: Token type (default: USDC)
            timeout: Optional request timeout

        Returns:
            Gas estimation
        """
        response = await self._post(
            "/api/v2/transactions/estimate-gas",
            {
                "chain": chain,
                "to_address": to_address,
                "amount": str(amount),
                "token": token,
            },
            timeout=timeout,
        )
        return GasEstimate.model_validate(response)

    async def get_status(
        self,
        tx_hash: str,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> TransactionStatus:
        """Get the status of a transaction.

        Args:
            tx_hash: Transaction hash
            chain: Chain name
            timeout: Optional request timeout

        Returns:
            Transaction status
        """
        response = await self._get(
            f"/api/v2/transactions/status/{tx_hash}",
            params={"chain": chain},
            timeout=timeout,
        )
        return TransactionStatus.model_validate(response)

    async def list_tokens(
        self,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[dict[str, Any]]:
        """List supported tokens on a chain.

        Args:
            chain: Chain name
            timeout: Optional request timeout

        Returns:
            List of token information
        """
        response = await self._get(f"/api/v2/transactions/tokens/{chain}", timeout=timeout)
        return response.get("tokens", [])


class TransactionsResource(SyncBaseResource):
    """Sync resource for transaction operations.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # List supported chains
            chains = client.transactions.list_chains()

            # Estimate gas
            estimate = client.transactions.estimate_gas(
                chain="base",
                to_address="0x...",
                amount=Decimal("100.00"),
            )
        ```
    """

    def list_chains(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[ChainInfo]:
        """List supported blockchain networks.

        Args:
            timeout: Optional request timeout

        Returns:
            List of chain information
        """
        response = self._get("/api/v2/transactions/chains", timeout=timeout)
        return [ChainInfo.model_validate(c) for c in response.get("chains", [])]

    def estimate_gas(
        self,
        chain: str,
        to_address: str,
        amount: Decimal,
        token: str = "USDC",
        timeout: float | TimeoutConfig | None = None,
    ) -> GasEstimate:
        """Estimate gas for a transaction.

        Args:
            chain: Target chain (e.g., "base_sepolia")
            to_address: Recipient address
            amount: Amount to send
            token: Token type (default: USDC)
            timeout: Optional request timeout

        Returns:
            Gas estimation
        """
        response = self._post(
            "/api/v2/transactions/estimate-gas",
            {
                "chain": chain,
                "to_address": to_address,
                "amount": str(amount),
                "token": token,
            },
            timeout=timeout,
        )
        return GasEstimate.model_validate(response)

    def get_status(
        self,
        tx_hash: str,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> TransactionStatus:
        """Get the status of a transaction.

        Args:
            tx_hash: Transaction hash
            chain: Chain name
            timeout: Optional request timeout

        Returns:
            Transaction status
        """
        response = self._get(
            f"/api/v2/transactions/status/{tx_hash}",
            params={"chain": chain},
            timeout=timeout,
        )
        return TransactionStatus.model_validate(response)

    def list_tokens(
        self,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[dict[str, Any]]:
        """List supported tokens on a chain.

        Args:
            chain: Chain name
            timeout: Optional request timeout

        Returns:
            List of token information
        """
        response = self._get(f"/api/v2/transactions/tokens/{chain}", timeout=timeout)
        return response.get("tokens", [])


__all__ = [
    "AsyncTransactionsResource",
    "ChainInfo",
    "GasEstimate",
    "TransactionStatus",
    "TransactionsResource",
]

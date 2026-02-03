"""
Wallets resource for Sardis SDK.

This module provides both async and sync interfaces for managing wallets.
Wallets hold funds and execute payments for agents.
"""
from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from ..models import Wallet, WalletBalance, WalletCreate, WalletTransferResponse
from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import AsyncSardisClient, SardisClient, TimeoutConfig


class AsyncWalletsResource(AsyncBaseResource):
    """Async resource for managing wallets.

    Wallets hold funds and execute payments. Each wallet:
    - Belongs to an Agent
    - Supports multiple tokens (USDC, USDT, etc.)
    - Has configurable spending limits
    - Is non-custodial (MPC-based)

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a wallet
            wallet = await client.wallets.create(
                agent_id="agent_123",
                currency="USDC",
            )

            # Get wallet balance
            balance = await client.wallets.get_balance("wallet_123")

            # List wallets for an agent
            wallets = await client.wallets.list(agent_id="agent_123")
        ```
    """

    async def create(
        self,
        agent_id: str,
        mpc_provider: str = "turnkey",
        currency: str = "USDC",
        chain: Optional[str] = None,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Create a new non-custodial wallet for an agent.

        Args:
            agent_id: ID of the owner agent
            mpc_provider: MPC provider ("turnkey", "fireblocks", or "local")
            currency: Base currency code (default: USDC)
            chain: Optional chain identifier (e.g., "base_sepolia", "base")
            limit_per_tx: Per-transaction spending limit
            limit_total: Total spending limit
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created Wallet object
        """
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "mpc_provider": mpc_provider,
            "currency": currency,
        }

        if chain is not None:
            payload["chain"] = chain
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_total is not None:
            payload["limit_total"] = str(limit_total)
        if metadata is not None:
            payload["metadata"] = metadata

        data = await self._post("wallets", payload, timeout=timeout)
        return Wallet.model_validate(data)

    async def get(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Get a wallet by ID.

        Args:
            wallet_id: The ID of the wallet to retrieve
            timeout: Optional request timeout

        Returns:
            The Wallet object
        """
        data = await self._get(f"wallets/{wallet_id}", timeout=timeout)
        return Wallet.model_validate(data)

    async def list(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Wallet]:
        """List wallets.

        Args:
            agent_id: Filter by owner agent ID
            limit: Maximum number of wallets to return
            timeout: Optional request timeout

        Returns:
            List of Wallet objects
        """
        params: Dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id

        data = await self._get("wallets", params=params, timeout=timeout)

        if isinstance(data, list):
            return [Wallet.model_validate(item) for item in data]
        return [Wallet.model_validate(item) for item in data.get("wallets", data.get("items", []))]

    async def get_balance(
        self,
        wallet_id: str,
        chain: str = "base",
        token: str = "USDC",
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WalletBalance:
        """Get wallet balance from chain (non-custodial, read-only).

        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            token: The token symbol (e.g., USDC, USDT)
            timeout: Optional request timeout

        Returns:
            WalletBalance object with balance from chain
        """
        params = {"chain": chain, "token": token}
        data = await self._get(f"wallets/{wallet_id}/balance", params=params, timeout=timeout)
        return WalletBalance.model_validate(data)

    async def get_addresses(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, str]:
        """Get all wallet addresses (chain -> address mapping).

        Args:
            wallet_id: The wallet ID
            timeout: Optional request timeout

        Returns:
            Dictionary mapping chain names to addresses
        """
        return await self._get(f"wallets/{wallet_id}/addresses", timeout=timeout)

    async def set_address(
        self,
        wallet_id: str,
        chain: str,
        address: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Set wallet address for a chain.

        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            address: Wallet address on the chain
            timeout: Optional request timeout

        Returns:
            Updated Wallet object
        """
        payload = {"chain": chain, "address": address}
        data = await self._post(f"wallets/{wallet_id}/addresses", payload, timeout=timeout)
        return Wallet.model_validate(data)

    async def update(
        self,
        wallet_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Update a wallet.

        Args:
            wallet_id: The wallet ID
            limit_per_tx: New per-transaction spending limit
            limit_total: New total spending limit
            is_active: Enable/disable the wallet
            metadata: New metadata
            timeout: Optional request timeout

        Returns:
            Updated Wallet object
        """
        payload: Dict[str, Any] = {}
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_total is not None:
            payload["limit_total"] = str(limit_total)
        if is_active is not None:
            payload["is_active"] = is_active
        if metadata is not None:
            payload["metadata"] = metadata

        data = await self._patch(f"wallets/{wallet_id}", payload, timeout=timeout)
        return Wallet.model_validate(data)

    async def transfer(
        self,
        wallet_id: str,
        *,
        destination: str,
        amount: Decimal,
        token: str = "USDC",
        chain: str = "base_sepolia",
        domain: str = "localhost",
        memo: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WalletTransferResponse:
        """Transfer stablecoins from a wallet (agent is sender)."""
        payload: Dict[str, Any] = {
            "destination": destination,
            "amount": str(amount),
            "token": token,
            "chain": chain,
            "domain": domain,
        }
        if memo is not None:
            payload["memo"] = memo
        data = await self._post(f"wallets/{wallet_id}/transfer", payload, timeout=timeout)
        return WalletTransferResponse.model_validate(data)


class WalletsResource(SyncBaseResource):
    """Sync resource for managing wallets.

    Wallets hold funds and execute payments. Each wallet:
    - Belongs to an Agent
    - Supports multiple tokens (USDC, USDT, etc.)
    - Has configurable spending limits
    - Is non-custodial (MPC-based)

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a wallet
            wallet = client.wallets.create(
                agent_id="agent_123",
                currency="USDC",
            )

            # Get wallet balance
            balance = client.wallets.get_balance("wallet_123")

            # List wallets for an agent
            wallets = client.wallets.list(agent_id="agent_123")
        ```
    """

    def create(
        self,
        agent_id: str,
        mpc_provider: str = "turnkey",
        currency: str = "USDC",
        chain: Optional[str] = None,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Create a new non-custodial wallet for an agent.

        Args:
            agent_id: ID of the owner agent
            mpc_provider: MPC provider ("turnkey", "fireblocks", or "local")
            currency: Base currency code (default: USDC)
            chain: Optional chain identifier (e.g., "base_sepolia", "base")
            limit_per_tx: Per-transaction spending limit
            limit_total: Total spending limit
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created Wallet object
        """
        payload: Dict[str, Any] = {
            "agent_id": agent_id,
            "mpc_provider": mpc_provider,
            "currency": currency,
        }

        if chain is not None:
            payload["chain"] = chain
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_total is not None:
            payload["limit_total"] = str(limit_total)
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._post("wallets", payload, timeout=timeout)
        return Wallet.model_validate(data)

    def get(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Get a wallet by ID.

        Args:
            wallet_id: The ID of the wallet to retrieve
            timeout: Optional request timeout

        Returns:
            The Wallet object
        """
        data = self._get(f"wallets/{wallet_id}", timeout=timeout)
        return Wallet.model_validate(data)

    def list(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> List[Wallet]:
        """List wallets.

        Args:
            agent_id: Filter by owner agent ID
            limit: Maximum number of wallets to return
            timeout: Optional request timeout

        Returns:
            List of Wallet objects
        """
        params: Dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id

        data = self._get("wallets", params=params, timeout=timeout)

        if isinstance(data, list):
            return [Wallet.model_validate(item) for item in data]
        return [Wallet.model_validate(item) for item in data.get("wallets", data.get("items", []))]

    def get_balance(
        self,
        wallet_id: str,
        chain: str = "base",
        token: str = "USDC",
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WalletBalance:
        """Get wallet balance from chain (non-custodial, read-only).

        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            token: The token symbol (e.g., USDC, USDT)
            timeout: Optional request timeout

        Returns:
            WalletBalance object with balance from chain
        """
        params = {"chain": chain, "token": token}
        data = self._get(f"wallets/{wallet_id}/balance", params=params, timeout=timeout)
        return WalletBalance.model_validate(data)

    def get_addresses(
        self,
        wallet_id: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, str]:
        """Get all wallet addresses (chain -> address mapping).

        Args:
            wallet_id: The wallet ID
            timeout: Optional request timeout

        Returns:
            Dictionary mapping chain names to addresses
        """
        return self._get(f"wallets/{wallet_id}/addresses", timeout=timeout)

    def set_address(
        self,
        wallet_id: str,
        chain: str,
        address: str,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Set wallet address for a chain.

        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            address: Wallet address on the chain
            timeout: Optional request timeout

        Returns:
            Updated Wallet object
        """
        payload = {"chain": chain, "address": address}
        data = self._post(f"wallets/{wallet_id}/addresses", payload, timeout=timeout)
        return Wallet.model_validate(data)

    def update(
        self,
        wallet_id: str,
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
        is_active: Optional[bool] = None,
        metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Wallet:
        """Update a wallet.

        Args:
            wallet_id: The wallet ID
            limit_per_tx: New per-transaction spending limit
            limit_total: New total spending limit
            is_active: Enable/disable the wallet
            metadata: New metadata
            timeout: Optional request timeout

        Returns:
            Updated Wallet object
        """
        payload: Dict[str, Any] = {}
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_total is not None:
            payload["limit_total"] = str(limit_total)
        if is_active is not None:
            payload["is_active"] = is_active
        if metadata is not None:
            payload["metadata"] = metadata

        data = self._patch(f"wallets/{wallet_id}", payload, timeout=timeout)
        return Wallet.model_validate(data)

    def transfer(
        self,
        wallet_id: str,
        *,
        destination: str,
        amount: Decimal,
        token: str = "USDC",
        chain: str = "base_sepolia",
        domain: str = "localhost",
        memo: Optional[str] = None,
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> WalletTransferResponse:
        """Transfer stablecoins from a wallet (agent is sender)."""
        payload: Dict[str, Any] = {
            "destination": destination,
            "amount": str(amount),
            "token": token,
            "chain": chain,
            "domain": domain,
        }
        if memo is not None:
            payload["memo"] = memo
        data = self._post(f"wallets/{wallet_id}/transfer", payload, timeout=timeout)
        return WalletTransferResponse.model_validate(data)


__all__ = [
    "AsyncWalletsResource",
    "WalletsResource",
]

from __future__ import annotations

from decimal import Decimal
from typing import Any, List, Optional

from ..models import Wallet, WalletCreate, WalletBalance
from .base import Resource


class WalletsResource(Resource):
    """
    Resource for managing wallets.
    
    Wallets hold funds and execute payments. Each wallet:
    - Belongs to an Agent
    - Supports multiple tokens (USDC, USDT, etc.)
    - Has configurable spending limits
    """
    
    async def create(
        self,
        agent_id: str,
        mpc_provider: str = "turnkey",
        currency: str = "USDC",
        limit_per_tx: Optional[Decimal] = None,
        limit_total: Optional[Decimal] = None,
    ) -> Wallet:
        """
        Create a new non-custodial wallet for an agent.
        
        Args:
            agent_id: ID of the owner agent
            mpc_provider: MPC provider ("turnkey", "fireblocks", or "local")
            currency: Base currency code (default: USDC)
            limit_per_tx: Per-transaction spending limit
            limit_total: Total spending limit
            
        Returns:
            The created Wallet object
        """
        payload = {
            "agent_id": agent_id,
            "mpc_provider": mpc_provider,
            "currency": currency,
        }
        
        if limit_per_tx is not None:
            payload["limit_per_tx"] = str(limit_per_tx)
        if limit_total is not None:
            payload["limit_total"] = str(limit_total)
            
        data = await self._client._request("POST", "wallets", json=payload)
        return Wallet.parse_obj(data)

    async def get(self, wallet_id: str) -> Wallet:
        """
        Get a wallet by ID.
        
        Args:
            wallet_id: The ID of the wallet to retrieve
            
        Returns:
            The Wallet object
        """
        data = await self._client._request("GET", f"wallets/{wallet_id}")
        return Wallet.parse_obj(data)

    async def list(
        self,
        agent_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Wallet]:
        """
        List wallets.
        
        Args:
            agent_id: Filter by owner agent ID
            limit: Maximum number of wallets to return
            
        Returns:
            List of Wallet objects
        """
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
            
        data = await self._client._request("GET", "wallets", params=params)
        return [Wallet.parse_obj(item) for item in data]

    async def get_balance(
        self,
        wallet_id: str,
        chain: str = "base",
        token: str = "USDC",
    ) -> WalletBalance:
        """
        Get wallet balance from chain (non-custodial, read-only).
        
        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            token: The token symbol (e.g., USDC, USDT)
            
        Returns:
            WalletBalance object with balance from chain
        """
        params = {
            "chain": chain,
            "token": token,
        }
        data = await self._client._request(
            "GET",
            f"wallets/{wallet_id}/balance",
            params=params,
        )
        return WalletBalance.parse_obj(data)
    
    async def get_addresses(self, wallet_id: str) -> dict[str, str]:
        """
        Get all wallet addresses (chain -> address mapping).
        
        Args:
            wallet_id: The wallet ID
            
        Returns:
            Dictionary mapping chain names to addresses
        """
        data = await self._client._request("GET", f"wallets/{wallet_id}/addresses")
        return data
    
    async def set_address(
        self,
        wallet_id: str,
        chain: str,
        address: str,
    ) -> Wallet:
        """
        Set wallet address for a chain.
        
        Args:
            wallet_id: The wallet ID
            chain: Chain identifier (e.g., "base", "polygon")
            address: Wallet address on the chain
            
        Returns:
            Updated Wallet object
        """
        payload = {
            "chain": chain,
            "address": address,
        }
        data = await self._client._request(
            "POST",
            f"wallets/{wallet_id}/addresses",
            json=payload,
        )
        return Wallet.parse_obj(data)

    # Note: fund() method removed - non-custodial wallets don't support funding
    # Balances are managed on-chain, not in our database

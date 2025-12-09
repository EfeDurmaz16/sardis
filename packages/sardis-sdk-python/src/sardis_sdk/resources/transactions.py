"""Transactions resource for Sardis SDK."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel

from .base import BaseResource


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


class TransactionsResource(BaseResource):
    """Resource for transaction operations."""
    
    async def list_chains(self) -> list[ChainInfo]:
        """
        List supported blockchain networks.
        
        Returns:
            List of chain information
        """
        response = await self._get("/api/v2/transactions/chains")
        return [ChainInfo.model_validate(c) for c in response.get("chains", [])]
    
    async def estimate_gas(
        self,
        chain: str,
        to_address: str,
        amount: Decimal,
        token: str = "USDC",
    ) -> GasEstimate:
        """
        Estimate gas for a transaction.
        
        Args:
            chain: Target chain (e.g., "base_sepolia")
            to_address: Recipient address
            amount: Amount to send
            token: Token type (default: USDC)
            
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
        )
        return GasEstimate.model_validate(response)
    
    async def get_status(self, tx_hash: str, chain: str) -> TransactionStatus:
        """
        Get the status of a transaction.
        
        Args:
            tx_hash: Transaction hash
            chain: Chain name
            
        Returns:
            Transaction status
        """
        response = await self._get(
            f"/api/v2/transactions/status/{tx_hash}",
            params={"chain": chain},
        )
        return TransactionStatus.model_validate(response)
    
    async def list_tokens(self, chain: str) -> list[dict[str, Any]]:
        """
        List supported tokens on a chain.
        
        Args:
            chain: Chain name
            
        Returns:
            List of token information
        """
        response = await self._get(f"/api/v2/transactions/tokens/{chain}")
        return response.get("tokens", [])

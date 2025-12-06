"""Ledger resource for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field

from .base import BaseResource


class LedgerEntry(BaseModel):
    """A ledger entry."""
    
    tx_id: str
    mandate_id: Optional[str] = None
    from_wallet: Optional[str] = None
    to_wallet: Optional[str] = None
    amount: Decimal
    currency: str
    chain: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    audit_anchor: Optional[str] = None
    created_at: datetime


class LedgerResource(BaseResource):
    """Resource for ledger operations."""
    
    async def list_entries(
        self,
        wallet_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[LedgerEntry]:
        """
        List ledger entries.
        
        Args:
            wallet_id: Filter by wallet ID
            limit: Maximum number of entries
            offset: Pagination offset
            
        Returns:
            List of ledger entries
        """
        params = {"limit": limit, "offset": offset}
        if wallet_id:
            params["wallet_id"] = wallet_id
        response = await self._get("/api/v2/ledger/entries", params=params)
        return [LedgerEntry.model_validate(e) for e in response.get("entries", [])]
    
    async def get_entry(self, tx_id: str) -> LedgerEntry:
        """
        Get a ledger entry by transaction ID.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Ledger entry
        """
        response = await self._get(f"/api/v2/ledger/entries/{tx_id}")
        return LedgerEntry.model_validate(response)
    
    async def verify_entry(self, tx_id: str) -> dict[str, bool]:
        """
        Verify a ledger entry's audit anchor.
        
        Args:
            tx_id: Transaction ID
            
        Returns:
            Verification result
        """
        return await self._get(f"/api/v2/ledger/entries/{tx_id}/verify")

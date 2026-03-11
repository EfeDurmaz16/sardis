"""
OFAC sanctioned address screening provider.

Loads sanctioned crypto addresses from the OFAC SDN list (via 0xB10C/ofac-sanctioned-digital-currency-addresses)
into an in-memory set for O(1) lookups. Refreshes daily. Zero cost, MIT-licensed data.

Address lists: https://github.com/0xB10C/ofac-sanctioned-digital-currency-addresses
"""
from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

from sardis_compliance.sanctions import (
    EntityType,
    SanctionsList,
    SanctionsProvider,
    SanctionsRisk,
    ScreeningResult,
    TransactionScreeningRequest,
    WalletScreeningRequest,
)

logger = logging.getLogger(__name__)

# Raw GitHub URLs for OFAC address lists (EVM-compatible chains)
OFAC_LIST_URLS = {
    "ETH": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_ETH.json",
    "USDC": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_USDC.json",
    "USDT": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_USDT.json",
    "ARB": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_ARB.json",
    "BSC": "https://raw.githubusercontent.com/0xB10C/ofac-sanctioned-digital-currency-addresses/lists/sanctioned_addresses_BSC.json",
}


class OFACAddressProvider(SanctionsProvider):
    """
    Screens wallet addresses against OFAC SDN sanctioned crypto addresses.

    Loads lists from GitHub (0xB10C repo) on startup, refreshes on a configurable
    interval. All addresses normalized to lowercase for O(1) set lookups.

    Cost: $0/year. Data source: US Treasury OFAC SDN list.
    """

    def __init__(
        self,
        refresh_interval_seconds: int = 86400,  # 24 hours
        custom_blocklist: set[str] | None = None,
    ):
        self._sanctioned_addresses: set[str] = set()
        self._custom_blocklist: set[str] = {a.lower() for a in (custom_blocklist or set())}
        self._refresh_interval = refresh_interval_seconds
        self._last_refresh: datetime | None = None
        self._refresh_lock = asyncio.Lock()
        self._loaded = False

    @property
    def address_count(self) -> int:
        """Number of sanctioned addresses loaded."""
        return len(self._sanctioned_addresses)

    async def _ensure_loaded(self) -> None:
        """Load addresses if not yet loaded or stale."""
        now = datetime.now(UTC)
        if self._loaded and self._last_refresh:
            age = (now - self._last_refresh).total_seconds()
            if age < self._refresh_interval:
                return

        async with self._refresh_lock:
            # Double-check after acquiring lock
            if self._loaded and self._last_refresh:
                age = (now - self._last_refresh).total_seconds()
                if age < self._refresh_interval:
                    return
            await self._refresh_lists()

    async def _refresh_lists(self) -> None:
        """Download and merge all OFAC address lists."""
        import httpx

        new_addresses: set[str] = set()
        errors: list[str] = []

        async with httpx.AsyncClient(timeout=30) as client:
            for ticker, url in OFAC_LIST_URLS.items():
                try:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    addresses = resp.json()
                    normalized = {addr.lower() for addr in addresses if isinstance(addr, str)}
                    new_addresses.update(normalized)
                    logger.info("OFAC: loaded %d addresses from %s list", len(normalized), ticker)
                except Exception as e:
                    errors.append(f"{ticker}: {e}")
                    logger.warning("OFAC: failed to load %s list: %s", ticker, e)

        if new_addresses:
            self._sanctioned_addresses = new_addresses
            self._last_refresh = datetime.now(UTC)
            self._loaded = True
            logger.info(
                "OFAC: total %d unique sanctioned addresses loaded (%d errors)",
                len(self._sanctioned_addresses),
                len(errors),
            )
        elif not self._loaded:
            logger.error("OFAC: failed to load any address lists: %s", errors)
            # Keep existing addresses if we had some; fail-closed if first load fails
            self._loaded = False

    def _is_sanctioned(self, address: str) -> bool:
        """Check if address is in sanctioned set or custom blocklist."""
        normalized = address.lower()
        return normalized in self._sanctioned_addresses or normalized in self._custom_blocklist

    async def screen_wallet(self, request: WalletScreeningRequest) -> ScreeningResult:
        """Screen a wallet address against OFAC SDN list."""
        await self._ensure_loaded()

        if not self._loaded:
            # Fail-closed: block if we can't load lists
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=False,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="ofac_sdn",
                reason="OFAC address lists unavailable — fail-closed",
            )

        if self._is_sanctioned(request.address):
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="ofac_sdn",
                matches=[{"list": "OFAC SDN", "address": request.address.lower()}],
                reason="Address is on OFAC SDN sanctioned list",
                lists_checked=[SanctionsList.OFAC],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.address,
            entity_type=EntityType.WALLET,
            provider="ofac_sdn",
            lists_checked=[SanctionsList.OFAC],
        )

    async def screen_transaction(self, request: TransactionScreeningRequest) -> ScreeningResult:
        """Screen both sides of a transaction against OFAC SDN."""
        from_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.from_address, chain=request.chain)
        )
        to_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.to_address, chain=request.chain)
        )

        if from_result.should_block or to_result.should_block:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="ofac_sdn",
                matches=from_result.matches + to_result.matches,
                reason="Transaction involves OFAC-sanctioned address",
                lists_checked=[SanctionsList.OFAC],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="ofac_sdn",
            lists_checked=[SanctionsList.OFAC],
        )

    async def add_to_blocklist(self, address: str, reason: str) -> bool:
        """Add address to custom blocklist."""
        self._custom_blocklist.add(address.lower())
        logger.info("OFAC custom blocklist: added %s (%s)", address, reason)
        return True

    async def remove_from_blocklist(self, address: str) -> bool:
        """Remove address from custom blocklist."""
        self._custom_blocklist.discard(address.lower())
        logger.info("OFAC custom blocklist: removed %s", address)
        return True

    async def force_refresh(self) -> int:
        """Force refresh of OFAC lists. Returns count of loaded addresses."""
        await self._refresh_lists()
        return len(self._sanctioned_addresses)

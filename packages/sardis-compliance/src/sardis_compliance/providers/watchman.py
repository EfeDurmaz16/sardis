"""
Moov Watchman sanctions screening provider.

Self-hosted HTTP API for screening entities/names against OFAC, EU, UN, UK
sanctions lists. Uses Jaro-Winkler fuzzy matching (same algorithm as US Treasury).

Requires: Docker sidecar running `moov/watchman` on port 8084.
Repo: https://github.com/moov-io/watchman
License: Apache-2.0
Cost: $0/year — self-hosted.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
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


@dataclass
class WatchmanEntityMatch:
    """A match returned by Watchman search."""
    name: str
    entity_type: str
    source_list: str
    source_id: str
    match_score: float
    remarks: str | None = None


class WatchmanProvider(SanctionsProvider):
    """
    Screens entities against sanctions lists via Moov Watchman HTTP API.

    Primary use: name/entity screening (KYC onboarding, merchant onboarding).
    Also supports crypto address screening via the `cryptoAddress` parameter.

    Deploy: `docker run -p 8084:8084 moov/watchman`
    """

    def __init__(
        self,
        base_url: str | None = None,
        min_match_score: float = 0.85,
    ):
        """
        Args:
            base_url: Watchman API URL. Falls back to SARDIS_WATCHMAN_URL env var,
                      then localhost:8084.
            min_match_score: Minimum Jaro-Winkler match score (0.0-1.0) to flag.
        """
        self._base_url = (
            base_url
            or os.getenv("SARDIS_WATCHMAN_URL")
            or "http://localhost:8084"
        ).rstrip("/")
        self._min_match = min_match_score
        self._custom_blocklist: set[str] = set()

    async def _search(
        self,
        name: str | None = None,
        entity_type: str = "person",
        crypto_address: str | None = None,
        crypto_currency: str = "ETH",
        limit: int = 5,
    ) -> list[WatchmanEntityMatch]:
        """Search Watchman for matching entities."""
        import httpx

        params: dict[str, Any] = {
            "limit": str(limit),
            "minMatch": str(self._min_match),
        }
        if name:
            params["name"] = name
            params["type"] = entity_type
        if crypto_address:
            params["cryptoAddress[]"] = f"{crypto_currency}:{crypto_address}"

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(f"{self._base_url}/v2/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        except httpx.ConnectError:
            logger.warning("Watchman unavailable at %s", self._base_url)
            return []
        except Exception as e:
            logger.warning("Watchman search failed: %s", e)
            return []

        matches = []
        for entity in data.get("entities", []):
            matches.append(WatchmanEntityMatch(
                name=entity.get("name", ""),
                entity_type=entity.get("entityType", "unknown"),
                source_list=entity.get("sourceList", "unknown"),
                source_id=entity.get("sourceID", ""),
                match_score=entity.get("match", 0.0),
                remarks=entity.get("remarks"),
            ))
        return matches

    def _matches_to_risk(self, matches: list[WatchmanEntityMatch]) -> SanctionsRisk:
        """Convert Watchman matches to a risk level."""
        if not matches:
            return SanctionsRisk.LOW
        best_score = max(m.match_score for m in matches)
        if best_score >= 0.95:
            return SanctionsRisk.BLOCKED
        if best_score >= 0.90:
            return SanctionsRisk.SEVERE
        if best_score >= 0.85:
            return SanctionsRisk.HIGH
        return SanctionsRisk.MEDIUM

    async def screen_wallet(self, request: WalletScreeningRequest) -> ScreeningResult:
        """Screen a wallet address via Watchman crypto address search."""
        address = request.address.lower()

        # Check custom blocklist first
        if address in self._custom_blocklist:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=True,
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="watchman",
                matches=[{"list": "custom_blocklist", "address": address}],
                reason="Address is on internal blocklist",
            )

        # Search by crypto address
        matches = await self._search(crypto_address=request.address)

        if matches:
            risk = self._matches_to_risk(matches)
            return ScreeningResult(
                risk_level=risk,
                is_sanctioned=risk in (SanctionsRisk.BLOCKED, SanctionsRisk.SEVERE),
                entity_id=request.address,
                entity_type=EntityType.WALLET,
                provider="watchman",
                matches=[
                    {
                        "list": m.source_list,
                        "name": m.name,
                        "score": m.match_score,
                        "source_id": m.source_id,
                    }
                    for m in matches
                ],
                reason=f"Watchman match: {matches[0].name} ({matches[0].match_score:.0%})",
                lists_checked=[SanctionsList.ALL],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.address,
            entity_type=EntityType.WALLET,
            provider="watchman",
            lists_checked=[SanctionsList.ALL],
        )

    async def screen_entity(
        self,
        name: str,
        entity_type: str = "person",
    ) -> ScreeningResult:
        """
        Screen an entity name against sanctions lists.

        Use for KYC onboarding and merchant verification.
        """
        matches = await self._search(name=name, entity_type=entity_type)

        if matches:
            risk = self._matches_to_risk(matches)
            return ScreeningResult(
                risk_level=risk,
                is_sanctioned=risk in (SanctionsRisk.BLOCKED, SanctionsRisk.SEVERE),
                entity_id=name,
                entity_type=EntityType.INDIVIDUAL if entity_type == "person" else EntityType.ORGANIZATION,
                provider="watchman",
                matches=[
                    {
                        "list": m.source_list,
                        "name": m.name,
                        "score": m.match_score,
                        "source_id": m.source_id,
                    }
                    for m in matches
                ],
                reason=f"Watchman name match: {matches[0].name} ({matches[0].match_score:.0%})",
                lists_checked=[SanctionsList.ALL],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=name,
            entity_type=EntityType.INDIVIDUAL if entity_type == "person" else EntityType.ORGANIZATION,
            provider="watchman",
            lists_checked=[SanctionsList.ALL],
        )

    async def screen_transaction(self, request: TransactionScreeningRequest) -> ScreeningResult:
        """Screen both sides of a transaction."""
        from_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.from_address, chain=request.chain)
        )
        to_result = await self.screen_wallet(
            WalletScreeningRequest(address=request.to_address, chain=request.chain)
        )

        if from_result.should_block or to_result.should_block:
            return ScreeningResult(
                risk_level=SanctionsRisk.BLOCKED,
                is_sanctioned=from_result.is_sanctioned or to_result.is_sanctioned,
                entity_id=request.tx_hash,
                entity_type=EntityType.TRANSACTION,
                provider="watchman",
                matches=from_result.matches + to_result.matches,
                reason="Transaction involves sanctioned entity (Watchman)",
                lists_checked=[SanctionsList.ALL],
            )

        return ScreeningResult(
            risk_level=SanctionsRisk.LOW,
            is_sanctioned=False,
            entity_id=request.tx_hash,
            entity_type=EntityType.TRANSACTION,
            provider="watchman",
            lists_checked=[SanctionsList.ALL],
        )

    async def add_to_blocklist(self, address: str, reason: str) -> bool:
        self._custom_blocklist.add(address.lower())
        logger.info("Watchman blocklist: added %s (%s)", address, reason)
        return True

    async def remove_from_blocklist(self, address: str) -> bool:
        self._custom_blocklist.discard(address.lower())
        logger.info("Watchman blocklist: removed %s", address)
        return True

    async def health_check(self) -> bool:
        """Check if Watchman is reachable."""
        import httpx

        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{self._base_url}/v2/search?name=test&limit=1")
                return resp.status_code == 200
        except Exception:
            return False

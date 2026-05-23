"""Adapter contracts for provider-agnostic funding rails."""

from __future__ import annotations

from typing import Any, Literal, Protocol

from .funding import FundingRequest, FundingResult

FundingRail = Literal["fiat", "stablecoin"]


class FundingRailAdapter(Protocol):
    """Contract for funding providers used by routing/orchestration layers."""

    @property
    def provider(self) -> str:
        ...

    @property
    def rail(self) -> FundingRail:
        ...

    async def fund(self, request: FundingRequest) -> FundingResult:
        ...

    async def quote(self, request: FundingRequest) -> dict[str, Any]:
        """Optional quote surface for providers that support explicit pre-funding quotes."""
        raise NotImplementedError

    async def status(self, transfer_id: str) -> dict[str, Any]:
        """Optional transfer status lookup for providers with async settlement lifecycles."""
        raise NotImplementedError

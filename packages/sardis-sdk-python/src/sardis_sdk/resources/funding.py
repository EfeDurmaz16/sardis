"""
Funding resource for Sardis SDK.

Sardis Protocol v1.0 -- Funding commitments and cells provide a structured
way to pre-fund agent wallets. A commitment locks a total value from a vault
reference, and cells are the subdivisions that agents can draw against.

This module provides both async and sync interfaces.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    import builtins
    from decimal import Decimal

    from ..client import TimeoutConfig


class AsyncFundingResource(AsyncBaseResource):
    """Async resource for funding commitments and cells.

    Funding commitments represent pre-allocated capital from a vault.
    Cells are subdivisions of a commitment that agents can draw against.

    Example:
        ```python
        async with AsyncSardisClient(api_key="...") as client:
            # Create a funding commitment
            commitment = await client.funding.create_commitment(
                vault_ref="vault_abc",
                total_value=Decimal("10000.00"),
                currency="USDC",
                cell_strategy="equal",
            )

            # List cells for a commitment
            cells = await client.funding.list_cells(
                commitment_id=commitment["id"],
            )

            # Split a cell into smaller denominations
            result = await client.funding.split_cell(
                cell_id="cell_xyz",
                amounts=[Decimal("100.00"), Decimal("200.00")],
            )
        ```
    """

    async def create_commitment(
        self,
        vault_ref: str,
        total_value: Decimal,
        currency: str = "USDC",
        cell_strategy: str = "equal",
        cell_count: int | None = None,
        cell_amounts: builtins.list[Decimal] | None = None,
        chain: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a new funding commitment from a vault.

        Args:
            vault_ref: Reference to the source vault
            total_value: Total value to commit
            currency: Currency code (default: USDC)
            cell_strategy: How to subdivide ("equal", "custom", "single")
            cell_count: Number of cells for "equal" strategy
            cell_amounts: Explicit cell amounts for "custom" strategy
            chain: Optional chain identifier
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created funding commitment
        """
        payload: dict[str, Any] = {
            "vault_ref": vault_ref,
            "total_value": str(total_value),
            "currency": currency,
            "cell_strategy": cell_strategy,
        }

        if cell_count is not None:
            payload["cell_count"] = cell_count
        if cell_amounts is not None:
            payload["cell_amounts"] = [str(a) for a in cell_amounts]
        if chain is not None:
            payload["chain"] = chain
        if metadata is not None:
            payload["metadata"] = metadata

        return await self._post("funding/commitments", payload, timeout=timeout)

    async def list_commitments(
        self,
        status: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List funding commitments.

        Args:
            status: Filter by status (e.g., "active", "depleted", "cancelled")
            limit: Maximum number of commitments to return
            timeout: Optional request timeout

        Returns:
            List of funding commitments
        """
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status

        data = await self._get("funding/commitments", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("commitments", data.get("items", []))

    async def list_cells(
        self,
        commitment_id: str | None = None,
        status: str | None = None,
        currency: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List funding cells.

        Args:
            commitment_id: Filter by parent commitment ID
            status: Filter by status (e.g., "available", "locked", "spent")
            currency: Filter by currency code
            limit: Maximum number of cells to return
            timeout: Optional request timeout

        Returns:
            List of funding cells
        """
        params: dict[str, Any] = {"limit": limit}
        if commitment_id is not None:
            params["commitment_id"] = commitment_id
        if status is not None:
            params["status"] = status
        if currency is not None:
            params["currency"] = currency

        data = await self._get("funding/cells", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("cells", data.get("items", []))

    async def split_cell(
        self,
        cell_id: str,
        amounts: builtins.list[Decimal],
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Split a funding cell into smaller cells.

        Args:
            cell_id: The cell to split
            amounts: List of amounts for the new cells (must sum to original)
            timeout: Optional request timeout

        Returns:
            Result containing the new cells
        """
        payload: dict[str, Any] = {
            "amounts": [str(a) for a in amounts],
        }

        return await self._post(
            f"funding/cells/{cell_id}/split", payload, timeout=timeout
        )

    async def merge_cells(
        self,
        cell_ids: builtins.list[str],
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Merge multiple funding cells into one.

        Args:
            cell_ids: List of cell IDs to merge (must share same commitment)
            timeout: Optional request timeout

        Returns:
            The merged cell
        """
        payload: dict[str, Any] = {
            "cell_ids": cell_ids,
        }

        return await self._post("funding/cells/merge", payload, timeout=timeout)


class FundingResource(SyncBaseResource):
    """Sync resource for funding commitments and cells.

    Funding commitments represent pre-allocated capital from a vault.
    Cells are subdivisions of a commitment that agents can draw against.

    Example:
        ```python
        with SardisClient(api_key="...") as client:
            # Create a funding commitment
            commitment = client.funding.create_commitment(
                vault_ref="vault_abc",
                total_value=Decimal("10000.00"),
                currency="USDC",
                cell_strategy="equal",
            )

            # List cells for a commitment
            cells = client.funding.list_cells(
                commitment_id=commitment["id"],
            )

            # Split a cell into smaller denominations
            result = client.funding.split_cell(
                cell_id="cell_xyz",
                amounts=[Decimal("100.00"), Decimal("200.00")],
            )
        ```
    """

    def create_commitment(
        self,
        vault_ref: str,
        total_value: Decimal,
        currency: str = "USDC",
        cell_strategy: str = "equal",
        cell_count: int | None = None,
        cell_amounts: builtins.list[Decimal] | None = None,
        chain: str | None = None,
        metadata: dict[str, Any] | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a new funding commitment from a vault.

        Args:
            vault_ref: Reference to the source vault
            total_value: Total value to commit
            currency: Currency code (default: USDC)
            cell_strategy: How to subdivide ("equal", "custom", "single")
            cell_count: Number of cells for "equal" strategy
            cell_amounts: Explicit cell amounts for "custom" strategy
            chain: Optional chain identifier
            metadata: Optional metadata dictionary
            timeout: Optional request timeout

        Returns:
            The created funding commitment
        """
        payload: dict[str, Any] = {
            "vault_ref": vault_ref,
            "total_value": str(total_value),
            "currency": currency,
            "cell_strategy": cell_strategy,
        }

        if cell_count is not None:
            payload["cell_count"] = cell_count
        if cell_amounts is not None:
            payload["cell_amounts"] = [str(a) for a in cell_amounts]
        if chain is not None:
            payload["chain"] = chain
        if metadata is not None:
            payload["metadata"] = metadata

        return self._post("funding/commitments", payload, timeout=timeout)

    def list_commitments(
        self,
        status: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List funding commitments.

        Args:
            status: Filter by status (e.g., "active", "depleted", "cancelled")
            limit: Maximum number of commitments to return
            timeout: Optional request timeout

        Returns:
            List of funding commitments
        """
        params: dict[str, Any] = {"limit": limit}
        if status is not None:
            params["status"] = status

        data = self._get("funding/commitments", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("commitments", data.get("items", []))

    def list_cells(
        self,
        commitment_id: str | None = None,
        status: str | None = None,
        currency: str | None = None,
        limit: int = 100,
        timeout: float | TimeoutConfig | None = None,
    ) -> builtins.list[dict[str, Any]]:
        """List funding cells.

        Args:
            commitment_id: Filter by parent commitment ID
            status: Filter by status (e.g., "available", "locked", "spent")
            currency: Filter by currency code
            limit: Maximum number of cells to return
            timeout: Optional request timeout

        Returns:
            List of funding cells
        """
        params: dict[str, Any] = {"limit": limit}
        if commitment_id is not None:
            params["commitment_id"] = commitment_id
        if status is not None:
            params["status"] = status
        if currency is not None:
            params["currency"] = currency

        data = self._get("funding/cells", params=params, timeout=timeout)

        if isinstance(data, list):
            return data
        return data.get("cells", data.get("items", []))

    def split_cell(
        self,
        cell_id: str,
        amounts: builtins.list[Decimal],
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Split a funding cell into smaller cells.

        Args:
            cell_id: The cell to split
            amounts: List of amounts for the new cells (must sum to original)
            timeout: Optional request timeout

        Returns:
            Result containing the new cells
        """
        payload: dict[str, Any] = {
            "amounts": [str(a) for a in amounts],
        }

        return self._post(
            f"funding/cells/{cell_id}/split", payload, timeout=timeout
        )

    def merge_cells(
        self,
        cell_ids: builtins.list[str],
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Merge multiple funding cells into one.

        Args:
            cell_ids: List of cell IDs to merge (must share same commitment)
            timeout: Optional request timeout

        Returns:
            The merged cell
        """
        payload: dict[str, Any] = {
            "cell_ids": cell_ids,
        }

        return self._post("funding/cells/merge", payload, timeout=timeout)


__all__ = [
    "AsyncFundingResource",
    "FundingResource",
]

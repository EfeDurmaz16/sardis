"""Evidence resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncEvidenceResource(AsyncBaseResource):
    """Access audit evidence, transaction records, and policy decisions."""

    async def get_transaction(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get full evidence package for a transaction.

        Args:
            tx_id: The transaction ID.
            timeout: Optional timeout override.
        """
        return await self._get(f"evidence/transactions/{tx_id}", timeout=timeout)

    async def list_policy_decisions(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[dict[str, Any]]:
        """List policy decisions with optional agent filter.

        Args:
            agent_id: Optional agent ID to filter decisions.
            limit: Maximum number of decisions to return.
            timeout: Optional timeout override.
        """
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        data = await self._get("evidence/policy-decisions", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("decisions", data.get("items", []))

    async def get_policy_decision(
        self,
        decision_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a specific policy decision record.

        Args:
            decision_id: The policy decision ID.
            timeout: Optional timeout override.
        """
        return await self._get(f"evidence/policy-decisions/{decision_id}", timeout=timeout)

    async def export_decision(
        self,
        decision_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Export a policy decision as a signed evidence bundle.

        Args:
            decision_id: The policy decision ID to export.
            timeout: Optional timeout override.
        """
        return await self._post(
            f"evidence/policy-decisions/{decision_id}/export",
            timeout=timeout,
        )


class EvidenceResource(SyncBaseResource):
    """Access audit evidence, transaction records, and policy decisions."""

    def get_transaction(
        self,
        tx_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get full evidence package for a transaction.

        Args:
            tx_id: The transaction ID.
            timeout: Optional timeout override.
        """
        return self._get(f"evidence/transactions/{tx_id}", timeout=timeout)

    def list_policy_decisions(
        self,
        *,
        agent_id: str | None = None,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[dict[str, Any]]:
        """List policy decisions with optional agent filter.

        Args:
            agent_id: Optional agent ID to filter decisions.
            limit: Maximum number of decisions to return.
            timeout: Optional timeout override.
        """
        params: dict[str, Any] = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        data = self._get("evidence/policy-decisions", params=params, timeout=timeout)
        if isinstance(data, list):
            return data
        return data.get("decisions", data.get("items", []))

    def get_policy_decision(
        self,
        decision_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get a specific policy decision record.

        Args:
            decision_id: The policy decision ID.
            timeout: Optional timeout override.
        """
        return self._get(f"evidence/policy-decisions/{decision_id}", timeout=timeout)

    def export_decision(
        self,
        decision_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Export a policy decision as a signed evidence bundle.

        Args:
            decision_id: The policy decision ID to export.
            timeout: Optional timeout override.
        """
        return self._post(
            f"evidence/policy-decisions/{decision_id}/export",
            timeout=timeout,
        )

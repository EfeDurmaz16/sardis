"""Kill switch resource for Sardis SDK."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


class AsyncKillSwitchResource(AsyncBaseResource):
    """Emergency kill switch controls for rails and chains."""

    async def status(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get current kill switch status for all rails and chains."""
        return await self._get("kill-switch/status", timeout=timeout)

    async def activate_rail(
        self,
        rail: str,
        reason: str,
        *,
        notes: str | None = None,
        auto_reactivate: int | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Activate (disable) a payment rail.

        Args:
            rail: The rail identifier to disable (e.g. "usdc", "card").
            reason: Required reason for the kill switch activation.
            notes: Optional operator notes.
            auto_reactivate: Optional seconds until automatic reactivation.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {"rail": rail, "reason": reason}
        if notes:
            payload["notes"] = notes
        if auto_reactivate is not None:
            payload["auto_reactivate"] = auto_reactivate
        return await self._post("kill-switch/rails/activate", payload, timeout=timeout)

    async def deactivate_rail(
        self,
        rail: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Deactivate (re-enable) a payment rail.

        Args:
            rail: The rail identifier to re-enable.
            timeout: Optional timeout override.
        """
        return await self._post("kill-switch/rails/deactivate", {"rail": rail}, timeout=timeout)

    async def activate_chain(
        self,
        chain: str,
        reason: str,
        *,
        notes: str | None = None,
        auto_reactivate: int | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Activate (disable) a blockchain chain.

        Args:
            chain: The chain identifier to disable (e.g. "base", "polygon").
            reason: Required reason for the kill switch activation.
            notes: Optional operator notes.
            auto_reactivate: Optional seconds until automatic reactivation.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {"chain": chain, "reason": reason}
        if notes:
            payload["notes"] = notes
        if auto_reactivate is not None:
            payload["auto_reactivate"] = auto_reactivate
        return await self._post("kill-switch/chains/activate", payload, timeout=timeout)

    async def deactivate_chain(
        self,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Deactivate (re-enable) a blockchain chain.

        Args:
            chain: The chain identifier to re-enable.
            timeout: Optional timeout override.
        """
        return await self._post("kill-switch/chains/deactivate", {"chain": chain}, timeout=timeout)


class KillSwitchResource(SyncBaseResource):
    """Emergency kill switch controls for rails and chains."""

    def status(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get current kill switch status for all rails and chains."""
        return self._get("kill-switch/status", timeout=timeout)

    def activate_rail(
        self,
        rail: str,
        reason: str,
        *,
        notes: str | None = None,
        auto_reactivate: int | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Activate (disable) a payment rail.

        Args:
            rail: The rail identifier to disable (e.g. "usdc", "card").
            reason: Required reason for the kill switch activation.
            notes: Optional operator notes.
            auto_reactivate: Optional seconds until automatic reactivation.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {"rail": rail, "reason": reason}
        if notes:
            payload["notes"] = notes
        if auto_reactivate is not None:
            payload["auto_reactivate"] = auto_reactivate
        return self._post("kill-switch/rails/activate", payload, timeout=timeout)

    def deactivate_rail(
        self,
        rail: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Deactivate (re-enable) a payment rail.

        Args:
            rail: The rail identifier to re-enable.
            timeout: Optional timeout override.
        """
        return self._post("kill-switch/rails/deactivate", {"rail": rail}, timeout=timeout)

    def activate_chain(
        self,
        chain: str,
        reason: str,
        *,
        notes: str | None = None,
        auto_reactivate: int | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Activate (disable) a blockchain chain.

        Args:
            chain: The chain identifier to disable (e.g. "base", "polygon").
            reason: Required reason for the kill switch activation.
            notes: Optional operator notes.
            auto_reactivate: Optional seconds until automatic reactivation.
            timeout: Optional timeout override.
        """
        payload: dict[str, Any] = {"chain": chain, "reason": reason}
        if notes:
            payload["notes"] = notes
        if auto_reactivate is not None:
            payload["auto_reactivate"] = auto_reactivate
        return self._post("kill-switch/chains/activate", payload, timeout=timeout)

    def deactivate_chain(
        self,
        chain: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Deactivate (re-enable) a blockchain chain.

        Args:
            chain: The chain identifier to re-enable.
            timeout: Optional timeout override.
        """
        return self._post("kill-switch/chains/deactivate", {"chain": chain}, timeout=timeout)

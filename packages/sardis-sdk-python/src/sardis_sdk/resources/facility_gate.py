"""Facility Gate resource for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from .base import AsyncBaseResource, SyncBaseResource

if TYPE_CHECKING:
    from ..client import TimeoutConfig


def _audit_export_params(
    *,
    occurred_from: datetime | str | None = None,
    occurred_to: datetime | str | None = None,
    event_type: str | None = None,
    limit: int = 500,
) -> dict[str, Any]:
    params: dict[str, Any] = {"limit": limit}
    if occurred_from:
        params["occurred_from"] = occurred_from.isoformat() if isinstance(occurred_from, datetime) else occurred_from
    if occurred_to:
        params["occurred_to"] = occurred_to.isoformat() if isinstance(occurred_to, datetime) else occurred_to
    if event_type:
        params["event_type"] = event_type
    return params


class AsyncFacilityGateResource(AsyncBaseResource):
    """Programmable facility access for agents."""

    async def create_request(
        self,
        payload: dict[str, Any],
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a Facility Gate spend request."""
        return await self._post("facility-requests", payload, timeout=timeout)

    async def attach_evidence(
        self,
        request_id: str,
        evidence: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Attach evidence references to a facility request."""
        payload: dict[str, Any] = {"evidence": evidence}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return await self._post(f"facility-requests/{request_id}/evidence", payload, timeout=timeout)

    async def authorize(
        self,
        request_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Evaluate and record a facility authorization decision."""
        return await self._post(f"facility-requests/{request_id}/authorize", timeout=timeout)

    async def execute(
        self,
        request_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Execute an approved authorization through the configured adapter."""
        return await self._post(f"facility-requests/{request_id}/execute", timeout=timeout)

    async def audit(
        self,
        request_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get audit reconstruction for a facility request."""
        return await self._get(f"facility-requests/{request_id}/audit", timeout=timeout)

    async def export_audit(
        self,
        request_id: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Export a request-level audit packet."""
        return await self._get(f"facility-requests/{request_id}/audit/export", timeout=timeout)

    async def export_events(
        self,
        *,
        occurred_from: datetime | str | None = None,
        occurred_to: datetime | str | None = None,
        event_type: str | None = None,
        limit: int = 500,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Export organization-level Facility Gate events and decision packets."""
        return await self._get(
            "facility-requests/audit/exports",
            params=_audit_export_params(
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                event_type=event_type,
                limit=limit,
            ),
            timeout=timeout,
        )

    async def list(
        self,
        *,
        limit: int = 50,
        timeout: float | TimeoutConfig | None = None,
    ) -> list[dict[str, Any]]:
        """List Facility Gate request states."""
        data = await self._get("facility-requests", params={"limit": limit}, timeout=timeout)
        return data.get("requests", data.get("items", []))

    async def manual_review(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """List requests waiting for human review."""
        return await self._get("facility-requests/manual-review", timeout=timeout)

    async def record_approval(
        self,
        request_id: str,
        *,
        approved: bool,
        reviewed_by: str,
        reason: str | None = None,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Record a Facility Gate approval outcome."""
        payload: dict[str, Any] = {"approved": approved, "reviewed_by": reviewed_by}
        if reason:
            payload["reason"] = reason
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return await self._post(f"facility-requests/{request_id}/approval", payload, timeout=timeout)

    async def revoke(
        self,
        *,
        scope: str,
        target_id: str,
        reason: str,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Create a facility revocation event."""
        payload: dict[str, Any] = {"scope": scope, "target_id": target_id, "reason": reason}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return await self._post("facility-requests/revocations", payload, timeout=timeout)

    async def exceptions(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """List Facility Gate exception events."""
        return await self._get("facility-requests/exceptions", timeout=timeout)

    async def resolve_exception(
        self,
        *,
        event_id: str,
        resolved_by: str,
        resolution: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Append an auditable exception resolution event."""
        return await self._post(
            "facility-requests/exceptions/resolve",
            {"event_id": event_id, "resolved_by": resolved_by, "resolution": resolution},
            timeout=timeout,
        )

    async def limits(
        self,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        """Get Facility Gate limiter summary."""
        return await self._get("facility-requests/limits", timeout=timeout)


class FacilityGateResource(SyncBaseResource):
    """Programmable facility access for agents."""

    def create_request(self, payload: dict[str, Any], timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._post("facility-requests", payload, timeout=timeout)

    def attach_evidence(
        self,
        request_id: str,
        evidence: list[dict[str, Any]],
        *,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"evidence": evidence}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return self._post(f"facility-requests/{request_id}/evidence", payload, timeout=timeout)

    def authorize(self, request_id: str, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._post(f"facility-requests/{request_id}/authorize", timeout=timeout)

    def execute(self, request_id: str, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._post(f"facility-requests/{request_id}/execute", timeout=timeout)

    def audit(self, request_id: str, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._get(f"facility-requests/{request_id}/audit", timeout=timeout)

    def export_audit(self, request_id: str, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._get(f"facility-requests/{request_id}/audit/export", timeout=timeout)

    def export_events(
        self,
        *,
        occurred_from: datetime | str | None = None,
        occurred_to: datetime | str | None = None,
        event_type: str | None = None,
        limit: int = 500,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        return self._get(
            "facility-requests/audit/exports",
            params=_audit_export_params(
                occurred_from=occurred_from,
                occurred_to=occurred_to,
                event_type=event_type,
                limit=limit,
            ),
            timeout=timeout,
        )

    def list(self, *, limit: int = 50, timeout: float | TimeoutConfig | None = None) -> list[dict[str, Any]]:
        data = self._get("facility-requests", params={"limit": limit}, timeout=timeout)
        return data.get("requests", data.get("items", []))

    def manual_review(self, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._get("facility-requests/manual-review", timeout=timeout)

    def record_approval(
        self,
        request_id: str,
        *,
        approved: bool,
        reviewed_by: str,
        reason: str | None = None,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"approved": approved, "reviewed_by": reviewed_by}
        if reason:
            payload["reason"] = reason
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return self._post(f"facility-requests/{request_id}/approval", payload, timeout=timeout)

    def revoke(
        self,
        *,
        scope: str,
        target_id: str,
        reason: str,
        idempotency_key: str | None = None,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {"scope": scope, "target_id": target_id, "reason": reason}
        if idempotency_key:
            payload["idempotency_key"] = idempotency_key
        return self._post("facility-requests/revocations", payload, timeout=timeout)

    def exceptions(self, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._get("facility-requests/exceptions", timeout=timeout)

    def resolve_exception(
        self,
        *,
        event_id: str,
        resolved_by: str,
        resolution: str,
        timeout: float | TimeoutConfig | None = None,
    ) -> dict[str, Any]:
        return self._post(
            "facility-requests/exceptions/resolve",
            {"event_id": event_id, "resolved_by": resolved_by, "resolution": resolution},
            timeout=timeout,
        )

    def limits(self, timeout: float | TimeoutConfig | None = None) -> dict[str, Any]:
        return self._get("facility-requests/limits", timeout=timeout)

"""Replay and projection verification helpers for Facility Gate events."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from server.repositories.facility_gate_repository import FacilityGateRepository
from server.routes.operations.metrics import record_facility_projection_replay


@dataclass(frozen=True)
class FacilityProjectionReplayResult:
    organization_id: str
    rebuilt: int
    verified: int
    drifted: int
    dry_run: bool
    drift: list[dict[str, Any]]


class FacilityGateReplayService:
    """Rebuild and verify materialized Facility Gate request projections."""

    def __init__(self, repository: FacilityGateRepository) -> None:
        self._repository = repository

    async def rebuild(
        self,
        *,
        organization_id: str,
        request_id: str | None = None,
        dry_run: bool = True,
    ) -> FacilityProjectionReplayResult:
        aggregate_ids = [request_id] if request_id else await self._repository.list_aggregate_ids(
            organization_id=organization_id
        )
        rebuilt = 0
        drift: list[dict[str, Any]] = []
        for aggregate_id in aggregate_ids:
            expected = await self._repository.replay_request_state(
                organization_id=organization_id,
                request_id=aggregate_id,
                persist=not dry_run,
            )
            if not expected:
                continue
            rebuilt += 1
            verification = await self._repository.verify_request_state_projection(
                organization_id=organization_id,
                request_id=aggregate_id,
            )
            if not verification["ok"]:
                drift.append(verification)

        result = FacilityProjectionReplayResult(
            organization_id=organization_id,
            rebuilt=rebuilt,
            verified=rebuilt - len(drift),
            drifted=len(drift),
            dry_run=dry_run,
            drift=drift,
        )
        record_facility_projection_replay(
            organization_id=organization_id,
            dry_run=dry_run,
            rebuilt=result.rebuilt,
            drifted=result.drifted,
        )
        return result

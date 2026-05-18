#!/usr/bin/env python
"""Replay Facility Gate event projections.

Usage:
  DATABASE_URL=postgresql://... python packages/server-api/scripts/facility_gate_replay.py org_123 --apply
"""
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "sardis-core" / "src"))

from sardis_server.repositories.facility_gate_repository import FacilityGateRepository
from sardis_server.services.facility_gate_replay import FacilityGateReplayService


async def _run() -> None:
    parser = argparse.ArgumentParser(description="Replay Facility Gate request projections")
    parser.add_argument("organization_id")
    parser.add_argument("--request-id")
    parser.add_argument("--apply", action="store_true", help="persist rebuilt projections")
    args = parser.parse_args()

    repo = FacilityGateRepository()
    service = FacilityGateReplayService(repo)
    result = await service.rebuild(
        organization_id=args.organization_id,
        request_id=args.request_id,
        dry_run=not args.apply,
    )
    print(json.dumps(result.__dict__, sort_keys=True, indent=2, default=str))
    if result.drifted:
        raise SystemExit(2)


if __name__ == "__main__":
    asyncio.run(_run())


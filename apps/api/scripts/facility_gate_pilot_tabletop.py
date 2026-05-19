#!/usr/bin/env python
"""Run the Facility Gate pilot tabletop flow against an in-process API.

This harness is intentionally simulator-only. It proves the control-plane
surfaces needed for a pilot without touching live provider rails.

Usage:
  python apps/api/scripts/facility_gate_pilot_tabletop.py
  python apps/api/scripts/facility_gate_pilot_tabletop.py --output tabletop.json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
_API_ROOT = _REPO_ROOT / "apps" / "api"
if _API_ROOT.is_dir() and str(_API_ROOT) not in sys.path:
    sys.path.insert(0, str(_API_ROOT))

for _package in (
    "sardis-core",
    "sardis-protocol",
    "sardis-ledger",
    "sardis-chain",
    "sardis-compliance",
    "sardis-wallet",
    "sardis-cards",
    "sardis-checkout",
    "sardis-striga",
):
    _src = _REPO_ROOT / "packages" / _package / "src"
    if _src.is_dir() and str(_src) not in sys.path:
        sys.path.insert(0, str(_src))

os.environ.setdefault("JWT_SECRET_KEY", "facility-gate-tabletop-test-secret")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_v2_core.facility_gate import Facility, FacilityLimit, SimulatedFacilityAdapter
from sardis_v2_core.spending_mandate import SpendingMandate

from server.authz import Principal, require_principal
from server.repositories.facility_gate_repository import FacilityGateRepository
from server.routes.authority import facility_requests
from server.services.facility_gate_authority import (
    RepositoryBackedFacilityMandateResolver,
    RepositoryBackedFacilityPolicyResolver,
    RepositoryBackedFacilityRecordResolver,
)
from server.services.facility_gate_replay import FacilityGateReplayService


@dataclass(frozen=True)
class TabletopContext:
    client: TestClient
    repository: FacilityGateRepository


@contextmanager
def _facility_gate_env() -> Any:
    keys = {
        "SARDIS_FACILITY_GATE_ENABLED": "true",
        "SARDIS_FACILITY_GATE_ORG_ALLOWLIST": "org_tabletop",
        "SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY": "true",
        "JWT_SECRET_KEY": "facility-gate-tabletop-test-secret",
    }
    previous = {key: os.environ.get(key) for key in keys}
    os.environ.update(keys)
    try:
        yield
    finally:
        for key, value in previous.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def build_tabletop_context() -> TabletopContext:
    app = FastAPI()
    repo = FacilityGateRepository(dsn="memory://")
    adapter = SimulatedFacilityAdapter()

    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key",
        organization_id="org_tabletop",
        scopes=["*"],
    )
    app.dependency_overrides[facility_requests.get_deps] = lambda: facility_requests.FacilityDependencies(
        repository=repo,
        adapter=adapter,
        mandate_resolver=RepositoryBackedFacilityMandateResolver(repo),
        facility_resolver=RepositoryBackedFacilityRecordResolver(repo),
        policy_resolver=RepositoryBackedFacilityPolicyResolver(repo),
    )
    app.include_router(facility_requests.router, prefix="/api/v2/facility-requests")
    return TabletopContext(client=TestClient(app), repository=repo)


def _request_payload(
    *,
    idempotency_key: str,
    amount_minor: int,
    evidence: bool,
    merchant: str = "aws.amazon.com",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "agent_id": "agent_1",
        "sponsor_id": "sponsor_1",
        "facility_id": "fac_1",
        "mandate_id": "mandate_1",
        "merchant": merchant,
        "amount_minor": amount_minor,
        "currency": "USD",
        "category": "cloud",
        "purpose": "cloud infrastructure",
        "task_graph_hash": "sha256:task" if evidence else None,
        "idempotency_key": idempotency_key,
    }
    if evidence:
        payload["evidence"] = [
            {
                "evidence_type": "invoice",
                "content_hash": "sha256:invoice",
                "uri": "s3://tabletop/invoice",
            }
        ]
    return payload


def _require_ok(response: Any, *, step: str, expected: int = 200) -> dict[str, Any]:
    if response.status_code != expected:
        raise RuntimeError(f"{step} failed: {response.status_code} {response.text}")
    return response.json()


async def _seed_authority(repository: FacilityGateRepository) -> None:
    await repository.upsert_facility_record(
        Facility(
            facility_id="fac_1",
            organization_id="org_tabletop",
            sponsor_id="sponsor_1",
            limit=FacilityLimit(per_transaction_minor=500_000, currency="USD"),
            allowed_categories=["cloud"],
            approval_threshold_minor=100_000,
            version=1,
        )
    )
    await repository.upsert_facility_policy_record(
        organization_id="org_tabletop",
        facility_id="fac_1",
        policy_version="facility_policy_tabletop_v1",
        snapshot={
            "allowed_categories": ["cloud"],
            "approval_threshold_minor": 100_000,
            "per_transaction_minor": 500_000,
            "currency": "USD",
        },
        created_by="facility_gate_pilot_tabletop",
    )
    await repository.upsert_facility_mandate_record(
        SpendingMandate(
            principal_id="principal_1",
            issuer_id="principal_1",
            org_id="org_tabletop",
            agent_id="agent_1",
            id="mandate_1",
            amount_per_tx=Decimal("5000"),
            currency="USD",
            allowed_rails=["simulated_card"],
            facility_authority_allowed=True,
            allowed_facility_ids=["fac_1"],
            facility_max_draw=Decimal("5000"),
            facility_scope={"allowed_categories": ["cloud"]},
            version=1,
        ),
        created_by="facility_gate_pilot_tabletop",
    )


def run_tabletop() -> dict[str, Any]:
    with _facility_gate_env():
        context = build_tabletop_context()
        asyncio.run(_seed_authority(context.repository))
        client = context.client

        allowlist_probe = _require_ok(
            client.get("/api/v2/facility-requests"),
            step="verify pilot org allowlist",
        )
        approved_request = _require_ok(
            client.post(
                "/api/v2/facility-requests",
                json=_request_payload(
                    idempotency_key="tabletop_create_approved",
                    amount_minor=75_000,
                    evidence=True,
                ),
            ),
            step="create approved request",
            expected=201,
        )
        approved_request_id = approved_request["request_id"]
        approved_decision = _require_ok(
            client.post(f"/api/v2/facility-requests/{approved_request_id}/authorize"),
            step="authorize approved request",
        )
        execution = _require_ok(
            client.post(f"/api/v2/facility-requests/{approved_request_id}/execute"),
            step="execute approved request",
        )
        duplicate_execution = _require_ok(
            client.post(f"/api/v2/facility-requests/{approved_request_id}/execute"),
            step="duplicate execute approved request",
        )
        audit_export = _require_ok(
            client.get(f"/api/v2/facility-requests/{approved_request_id}/audit/export"),
            step="export approved audit",
        )

        step_up_request = _require_ok(
            client.post(
                "/api/v2/facility-requests",
                json=_request_payload(
                    idempotency_key="tabletop_create_step_up",
                    amount_minor=240_000,
                    evidence=False,
                    merchant="new-cloud-vendor.example",
                ),
            ),
            step="create step-up request",
            expected=201,
        )
        step_up_request_id = step_up_request["request_id"]
        step_up_decision = _require_ok(
            client.post(f"/api/v2/facility-requests/{step_up_request_id}/authorize"),
            step="authorize step-up request",
        )
        manual_review = _require_ok(
            client.get("/api/v2/facility-requests/manual-review"),
            step="list manual review",
        )
        approval = _require_ok(
            client.post(
                f"/api/v2/facility-requests/{step_up_request_id}/approval",
                json={
                    "approved": True,
                    "reviewed_by": "finance_admin",
                    "reason": "pilot tabletop approval",
                },
            ),
            step="record approval",
        )
        approved_after_step_up = _require_ok(
            client.post(f"/api/v2/facility-requests/{step_up_request_id}/authorize"),
            step="resume after approval",
        )

        revoked_request = _require_ok(
            client.post(
                "/api/v2/facility-requests",
                json=_request_payload(
                    idempotency_key="tabletop_create_revoked",
                    amount_minor=50_000,
                    evidence=True,
                ),
            ),
            step="create revoked-path request",
            expected=201,
        )
        revoke = _require_ok(
            client.post(
                "/api/v2/facility-requests/revocations",
                json={"scope": "agent", "target_id": "agent_1", "reason": "pilot tabletop kill switch"},
            ),
            step="revoke agent",
        )
        denied_after_revoke = _require_ok(
            client.post(f"/api/v2/facility-requests/{revoked_request['request_id']}/authorize"),
            step="authorize after revoke",
        )

        replay = asyncio.run(
            FacilityGateReplayService(context.repository).rebuild(
                organization_id="org_tabletop",
                dry_run=True,
            )
        )

        checks = {
            "pilot_org_allowlist_active": allowlist_probe["total"] == 0,
            "approved_request": approved_decision["verdict"] == "approved",
            "execution_created": execution["credential"]["provider"] == "simulated",
            "duplicate_execute_idempotent": duplicate_execution["event_id"] == execution["event_id"],
            "audit_export_hash_chain_ok": audit_export["event_hash_chain"]["ok"] is True,
            "decision_packet_has_hash": bool(audit_export["decision_packet"]["decision_packet_hash"]),
            "decision_packet_has_versions": bool(audit_export["decision_packet"]["policy"]["policy_version"])
            and bool(audit_export["decision_packet"]["facility"]["version_id"])
            and bool(audit_export["decision_packet"]["mandate"]["version_id"]),
            "step_up_required": step_up_decision["verdict"] == "step_up_required",
            "manual_review_visible": manual_review["total"] >= 1,
            "approval_recorded": bool(approval["event_id"]),
            "approval_resume_approved": approved_after_step_up["verdict"] == "approved",
            "revocation_recorded": bool(revoke["event_id"]),
            "revocation_blocks_future_authorization": denied_after_revoke["verdict"] == "denied",
            "projection_replay_clean": replay.drifted == 0 and replay.rebuilt >= 3,
        }

        return {
            "schema_version": "facility_gate_pilot_tabletop_v1",
            "organization_id": "org_tabletop",
            "status": "passed" if all(checks.values()) else "failed",
            "checks": checks,
            "artifacts": {
                "approved_request_id": approved_request_id,
                "approved_decision_id": approved_decision["decision_id"],
                "execution_event_id": execution["event_id"],
                "audit_export_schema_version": audit_export["schema_version"],
                "decision_packet_hash": audit_export["decision_packet"]["decision_packet_hash"],
                "step_up_request_id": step_up_request_id,
                "step_up_decision_id": step_up_decision["decision_id"],
                "approval_event_id": approval["event_id"],
                "revocation_event_id": revoke["event_id"],
                "revoked_request_id": revoked_request["request_id"],
                "replay": replay.__dict__,
            },
        }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Facility Gate pilot tabletop harness")
    parser.add_argument("--output", help="Optional path to write the tabletop report JSON")
    args = parser.parse_args()

    report = run_tabletop()
    encoded = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded + "\n")
    if report["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

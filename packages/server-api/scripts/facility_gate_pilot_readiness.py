#!/usr/bin/env python
"""Evaluate Facility Gate pilot readiness gates.

This script is intentionally conservative: it checks deployment flags and
pilot evidence before a Facility Gate pilot org is enabled. It does not touch
live provider rails.

Usage:
  python packages/server-api/scripts/facility_gate_pilot_readiness.py org_123
  python packages/server-api/scripts/facility_gate_pilot_readiness.py org_123 --run-tabletop --require-alerts
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[3]
for _package in (
    "server-api",
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

REQUIRED_ENV_FLAGS = (
    "SARDIS_FACILITY_GATE_ENABLED",
    "SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY",
)
ORG_ALLOWLIST_ENV = "SARDIS_FACILITY_GATE_ORG_ALLOWLIST"
ALERT_RULES_PATH = _REPO_ROOT / "monitoring" / "facility-gate-prometheus-rules.yml"
GRAFANA_DASHBOARD_PATH = _REPO_ROOT / "ops" / "grafana" / "facility-gate.json"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _check(status: str, message: str, **details: Any) -> dict[str, Any]:
    result: dict[str, Any] = {"status": status, "message": message}
    if details:
        result["details"] = details
    return result


def _parse_allowlist(value: str | None) -> set[str]:
    raw = (value or "").strip()
    if not raw:
        return set()
    return {item.strip() for item in raw.split(",") if item.strip()}


def _load_tabletop_module() -> Any:
    script_path = Path(__file__).with_name("facility_gate_pilot_tabletop.py")
    spec = importlib.util.spec_from_file_location("facility_gate_pilot_tabletop", script_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load Facility Gate tabletop harness")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def evaluate_environment(
    *,
    organization_id: str,
    require_alerts: bool = True,
    run_tabletop: bool = False,
    allow_wildcard: bool = False,
) -> dict[str, Any]:
    checks: dict[str, dict[str, Any]] = {}

    checks["facility_gate_enabled"] = (
        _check("passed", "Facility Gate global flag is enabled")
        if _truthy(os.getenv("SARDIS_FACILITY_GATE_ENABLED"))
        else _check("blocked", "Set SARDIS_FACILITY_GATE_ENABLED=true before pilot")
    )
    checks["persisted_authority"] = (
        _check("passed", "Strict persisted authority mode is enabled")
        if _truthy(os.getenv("SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY"))
        else _check(
            "blocked",
            "Set SARDIS_FACILITY_GATE_REQUIRE_PERSISTED_AUTHORITY=true before pilot",
        )
    )

    allowlist = _parse_allowlist(os.getenv(ORG_ALLOWLIST_ENV))
    if not allowlist:
        checks["org_allowlist"] = _check(
            "blocked",
            f"Set {ORG_ALLOWLIST_ENV}=<pilot_org_ids> before pilot",
        )
    elif "*" in allowlist and not allow_wildcard:
        checks["org_allowlist"] = _check(
            "blocked",
            f"{ORG_ALLOWLIST_ENV}=* is only acceptable in isolated test environments",
        )
    elif "*" in allowlist or organization_id in allowlist:
        checks["org_allowlist"] = _check(
            "passed",
            "Pilot organization is included in the Facility Gate allowlist",
            organization_id=organization_id,
        )
    else:
        checks["org_allowlist"] = _check(
            "blocked",
            "Pilot organization is missing from the Facility Gate allowlist",
            organization_id=organization_id,
            allowlist=sorted(allowlist),
        )

    if require_alerts:
        checks["alert_rules"] = (
            _check("passed", "Facility Gate Prometheus alert rules exist")
            if ALERT_RULES_PATH.exists()
            else _check("blocked", "Facility Gate Prometheus alert rules are missing")
        )
        checks["grafana_dashboard"] = (
            _check("passed", "Facility Gate Grafana dashboard template exists")
            if GRAFANA_DASHBOARD_PATH.exists()
            else _check("blocked", "Facility Gate Grafana dashboard template is missing")
        )
    else:
        checks["alert_rules"] = _check("skipped", "Alert artifact check skipped")
        checks["grafana_dashboard"] = _check("skipped", "Grafana artifact check skipped")

    if run_tabletop:
        try:
            tabletop_report = _load_tabletop_module().run_tabletop()
        except Exception as exc:  # pragma: no cover - defensive CLI path
            checks["tabletop"] = _check("blocked", "Facility Gate tabletop harness failed", error=str(exc))
        else:
            checks["tabletop"] = (
                _check(
                    "passed",
                    "Facility Gate tabletop harness passed",
                    tabletop_status=tabletop_report.get("status"),
                    checks=tabletop_report.get("checks", {}),
                )
                if tabletop_report.get("status") == "passed"
                else _check(
                    "blocked",
                    "Facility Gate tabletop harness did not pass",
                    tabletop_status=tabletop_report.get("status"),
                    checks=tabletop_report.get("checks", {}),
                )
            )
    else:
        checks["tabletop"] = _check("skipped", "Tabletop harness check skipped")

    blocked = [name for name, check in checks.items() if check["status"] == "blocked"]
    return {
        "schema_version": "facility_gate_pilot_readiness_v1",
        "organization_id": organization_id,
        "status": "blocked" if blocked else "passed",
        "blocked": blocked,
        "checks": checks,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate Facility Gate pilot readiness gates")
    parser.add_argument("organization_id", help="Pilot organization ID that will be allowlisted")
    parser.add_argument("--output", help="Optional path to write the readiness report JSON")
    parser.add_argument("--run-tabletop", action="store_true", help="run simulator-only tabletop harness")
    parser.add_argument("--require-alerts", action="store_true", help="require alert and dashboard artifacts")
    parser.add_argument(
        "--allow-wildcard",
        action="store_true",
        help="allow SARDIS_FACILITY_GATE_ORG_ALLOWLIST=* for isolated test environments",
    )
    args = parser.parse_args()

    report = evaluate_environment(
        organization_id=args.organization_id,
        require_alerts=args.require_alerts,
        run_tabletop=args.run_tabletop,
        allow_wildcard=args.allow_wildcard,
    )
    encoded = json.dumps(report, indent=2, sort_keys=True, default=str)
    print(encoded)
    if args.output:
        Path(args.output).write_text(encoded + "\n")
    if report["status"] != "passed":
        raise SystemExit(2)


if __name__ == "__main__":
    main()

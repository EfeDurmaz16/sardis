#!/usr/bin/env python3
"""Generate ops readiness evidence artifact (SLO/alerts/DR proof)."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Dict


RUNBOOK_FILES = [
    "docs/design-partner/ops-slo-alerts-rollback-runbook.md",
    "docs/design-partner/mainnet-proof-and-rollback-runbook.md",
    "docs/design-partner/incident-response-247-drill.md",
    "docs/design-partner/reconciliation-load-chaos-slos.md",
]


def _parse_ts(value: str) -> dt.datetime:
    normalized = value.replace("Z", "+00:00")
    return dt.datetime.fromisoformat(normalized)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8192), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise SystemExit(f"[ops-evidence][fail] missing json file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SystemExit(f"[ops-evidence][fail] invalid json ({path}): {exc}") from exc


def _parse_json_env(name: str, fallback: Dict[str, Any]) -> Dict[str, Any]:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return fallback
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    return fallback


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate ops readiness evidence artifact")
    parser.add_argument(
        "--drill-evidence",
        default="docs/audits/evidence/turnkey-outage-drill-latest.json",
        help="Path to drill evidence json",
    )
    parser.add_argument(
        "--output",
        default="docs/audits/evidence/ops-readiness-latest.json",
        help="Output artifact path",
    )
    parser.add_argument("--max-failover-rto-min", type=float, default=15.0)
    parser.add_argument("--max-recovery-rto-min", type=float, default=60.0)
    parser.add_argument("--max-rpo-sec", type=float, default=0.0)
    args = parser.parse_args()

    drill_payload = _load_json(Path(args.drill_evidence))
    required = [
        "drill_id",
        "incident_started_at",
        "failover_mode_activated_at",
        "primary_recovered_at",
        "measured_rpo_seconds",
    ]
    missing = [field for field in required if field not in drill_payload]
    if missing:
        raise SystemExit(f"[ops-evidence][fail] drill evidence missing fields: {', '.join(missing)}")

    incident_started = _parse_ts(str(drill_payload["incident_started_at"]))
    failover_activated = _parse_ts(str(drill_payload["failover_mode_activated_at"]))
    primary_recovered = _parse_ts(str(drill_payload["primary_recovered_at"]))
    measured_rpo = float(drill_payload["measured_rpo_seconds"])

    failover_rto_min = (failover_activated - incident_started).total_seconds() / 60.0
    recovery_rto_min = (primary_recovered - incident_started).total_seconds() / 60.0

    thresholds = {
        "max_failover_rto_min": args.max_failover_rto_min,
        "max_recovery_rto_min": args.max_recovery_rto_min,
        "max_rpo_sec": args.max_rpo_sec,
    }
    checks = {
        "failover_rto_within_target": failover_rto_min <= args.max_failover_rto_min,
        "recovery_rto_within_target": recovery_rto_min <= args.max_recovery_rto_min,
        "rpo_within_target": measured_rpo <= args.max_rpo_sec,
    }

    runbooks = []
    for file_path in RUNBOOK_FILES:
        path = Path(file_path)
        if not path.exists():
            raise SystemExit(f"[ops-evidence][fail] missing runbook: {file_path}")
        runbooks.append(
            {
                "path": file_path,
                "sha256": _sha256(path),
            }
        )

    severity_channels = _parse_json_env(
        "SARDIS_ALERT_SEVERITY_CHANNELS_JSON",
        {
            "info": ["websocket"],
            "warning": ["websocket", "slack"],
            "critical": ["websocket", "slack", "email", "pagerduty"],
        },
    )
    cooldowns = _parse_json_env(
        "SARDIS_ALERT_CHANNEL_COOLDOWNS_JSON",
        {
            "slack": 180,
            "email": 300,
            "pagerduty": 120,
        },
    )

    artifact = {
        "generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "drill": {
            "source": args.drill_evidence,
            "drill_id": drill_payload["drill_id"],
            "scenario": drill_payload.get("scenario"),
            "owner": drill_payload.get("owner"),
            "failover_rto_min": round(failover_rto_min, 2),
            "recovery_rto_min": round(recovery_rto_min, 2),
            "measured_rpo_sec": measured_rpo,
            "thresholds": thresholds,
            "checks": checks,
        },
        "alert_routing": {
            "severity_channels": severity_channels,
            "channel_cooldowns": cooldowns,
            "pagerduty_configured": bool((os.getenv("PAGERDUTY_ROUTING_KEY", "") or "").strip()),
        },
        "runbooks": runbooks,
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(artifact, indent=2, sort_keys=True), encoding="utf-8")
    print(f"[ops-evidence] wrote artifact: {output_path}")

    if not all(checks.values()):
        raise SystemExit("[ops-evidence][fail] drill metrics exceed configured thresholds")
    print("[ops-evidence] pass")


if __name__ == "__main__":
    main()


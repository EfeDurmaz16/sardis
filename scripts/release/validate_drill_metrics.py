#!/usr/bin/env python3
"""Validate incident drill metrics against RTO/RPO targets."""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path


def _parse_ts(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate DR drill metrics evidence.")
    parser.add_argument("--evidence", required=True, help="Path to drill evidence JSON.")
    parser.add_argument("--max-failover-rto-min", type=float, default=15.0)
    parser.add_argument("--max-recovery-rto-min", type=float, default=60.0)
    parser.add_argument("--max-rpo-sec", type=float, default=0.0)
    args = parser.parse_args()

    evidence_path = Path(args.evidence)
    if not evidence_path.exists():
        raise SystemExit(f"[drill-metrics][fail] evidence file missing: {evidence_path}")

    payload = json.loads(evidence_path.read_text(encoding="utf-8"))
    required = [
        "drill_id",
        "incident_started_at",
        "failover_mode_activated_at",
        "primary_recovered_at",
        "measured_rpo_seconds",
    ]
    missing = [key for key in required if key not in payload]
    if missing:
        raise SystemExit(f"[drill-metrics][fail] evidence missing fields: {', '.join(missing)}")

    incident_started = _parse_ts(str(payload["incident_started_at"]))
    failover_activated = _parse_ts(str(payload["failover_mode_activated_at"]))
    primary_recovered = _parse_ts(str(payload["primary_recovered_at"]))
    measured_rpo = float(payload["measured_rpo_seconds"])

    failover_rto_min = (failover_activated - incident_started).total_seconds() / 60.0
    recovery_rto_min = (primary_recovered - incident_started).total_seconds() / 60.0

    print(f"[drill-metrics] drill_id={payload['drill_id']}")
    print(f"[drill-metrics] failover_rto_min={failover_rto_min:.2f}")
    print(f"[drill-metrics] recovery_rto_min={recovery_rto_min:.2f}")
    print(f"[drill-metrics] measured_rpo_sec={measured_rpo:.2f}")

    failures: list[str] = []
    if failover_rto_min > args.max_failover_rto_min:
        failures.append(
            f"failover_rto_min {failover_rto_min:.2f} > target {args.max_failover_rto_min:.2f}"
        )
    if recovery_rto_min > args.max_recovery_rto_min:
        failures.append(
            f"recovery_rto_min {recovery_rto_min:.2f} > target {args.max_recovery_rto_min:.2f}"
        )
    if measured_rpo > args.max_rpo_sec:
        failures.append(f"measured_rpo_sec {measured_rpo:.2f} > target {args.max_rpo_sec:.2f}")

    if failures:
        for failure in failures:
            print(f"[drill-metrics][fail] {failure}")
        return 1

    print("[drill-metrics] pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

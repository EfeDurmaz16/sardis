#!/usr/bin/env python3
"""Validate design partner readiness checklist gates."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any


VALID_STATUSES = {"pass", "pending", "fail", "waived"}
DEFAULT_CHECKLIST = Path("docs/design-partner/staging-hardening-checklist.json")


@dataclass(frozen=True)
class GateResult:
    gate_id: str
    title: str
    status: str
    evidence: str
    notes: str | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate design partner readiness checklist.")
    parser.add_argument(
        "--scope",
        choices=("engineering", "launch"),
        default="engineering",
        help="Validation scope. engineering checks core technical gates; launch includes operational gates.",
    )
    parser.add_argument(
        "--file",
        default=str(DEFAULT_CHECKLIST),
        help="Checklist JSON file path.",
    )
    parser.add_argument(
        "--max-review-age-days",
        type=int,
        default=30,
        help="Maximum allowed age for last_reviewed date.",
    )
    return parser.parse_args()


def load_checklist(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Checklist file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("Checklist root must be a JSON object.")
    return data


def parse_last_reviewed(data: dict[str, Any], max_age_days: int) -> tuple[date, int]:
    value = data.get("last_reviewed")
    if not isinstance(value, str):
        raise ValueError("Checklist must include string field 'last_reviewed' (YYYY-MM-DD).")
    reviewed = datetime.strptime(value, "%Y-%m-%d").date()
    age = (date.today() - reviewed).days
    if age > max_age_days:
        raise ValueError(
            f"Checklist is stale: last_reviewed={reviewed.isoformat()} "
            f"(age={age} days > max={max_age_days})."
        )
    return reviewed, age


def extract_scope_gates(data: dict[str, Any], scope: str) -> list[GateResult]:
    gates = data.get("gates")
    if not isinstance(gates, list):
        raise ValueError("Checklist must include array field 'gates'.")

    scoped: list[GateResult] = []
    for raw in gates:
        if not isinstance(raw, dict):
            raise ValueError("Each gate must be an object.")

        gate_id = raw.get("id")
        title = raw.get("title")
        status = raw.get("status")
        required_for = raw.get("required_for")
        evidence = raw.get("evidence", "")
        notes = raw.get("notes")

        if not isinstance(gate_id, str) or not gate_id:
            raise ValueError("Gate missing non-empty string 'id'.")
        if not isinstance(title, str) or not title:
            raise ValueError(f"Gate '{gate_id}' missing non-empty string 'title'.")
        if status not in VALID_STATUSES:
            raise ValueError(f"Gate '{gate_id}' has invalid status '{status}'.")
        if not isinstance(required_for, list) or not all(isinstance(x, str) for x in required_for):
            raise ValueError(f"Gate '{gate_id}' must define string array 'required_for'.")
        if not isinstance(evidence, str):
            raise ValueError(f"Gate '{gate_id}' has invalid 'evidence' field.")
        if notes is not None and not isinstance(notes, str):
            raise ValueError(f"Gate '{gate_id}' has invalid 'notes' field.")

        if scope in required_for:
            scoped.append(
                GateResult(
                    gate_id=gate_id,
                    title=title,
                    status=status,
                    evidence=evidence,
                    notes=notes,
                )
            )
    return scoped


def main() -> int:
    args = parse_args()
    checklist_path = Path(args.file)

    data = load_checklist(checklist_path)
    reviewed, age = parse_last_reviewed(data, args.max_review_age_days)
    scoped_gates = extract_scope_gates(data, args.scope)

    if not scoped_gates:
        print(f"[design-partner-readiness] No gates found for scope '{args.scope}'.")
        return 1

    failed: list[GateResult] = []
    for gate in scoped_gates:
        if gate.status not in {"pass", "waived"}:
            failed.append(gate)

    print(
        "[design-partner-readiness] "
        f"scope={args.scope} reviewed={reviewed.isoformat()} age_days={age} "
        f"gates={len(scoped_gates)}"
    )

    for gate in scoped_gates:
        print(
            f"  - {gate.gate_id}: {gate.status} | {gate.title}"
            + (f" | evidence={gate.evidence}" if gate.evidence else "")
        )

    if failed:
        print("[design-partner-readiness] FAILED gates:")
        for gate in failed:
            print(
                f"  - {gate.gate_id}: status={gate.status} "
                + (f"| notes={gate.notes}" if gate.notes else "")
            )
        return 1

    print("[design-partner-readiness] All required gates passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

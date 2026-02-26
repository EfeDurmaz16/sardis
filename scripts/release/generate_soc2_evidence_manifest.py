#!/usr/bin/env python3
"""Generate SOC2/PCI evidence manifest for release artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(8192)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _git_sha(root: Path) -> str:
    try:
        out = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            stderr=subprocess.DEVNULL,
            text=True,
        ).strip()
        return out
    except Exception:
        return "unknown"


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate SOC2 evidence manifest.")
    parser.add_argument("--root", default=".", help="Repository root.")
    parser.add_argument(
        "--output",
        default="artifacts/compliance/soc2-evidence-manifest.json",
        help="Output manifest path.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    output = (root / args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    evidence_files = [
        "docs/design-partner/compliance-execution-track-q1-2026.md",
        "docs/design-partner/pci-approvals-and-db-hardening-checklist.md",
        "docs/design-partner/pci-enclave-and-embedded-card-runbook.md",
        "docs/design-partner/acquirer-sponsor-bank-qsa-ownership.md",
        "docs/audits/control-testing-cadence-q1-2026.md",
        "docs/audits/evidence/turnkey-outage-drill-latest.json",
    ]

    records = []
    missing = []
    for rel_path in evidence_files:
        abs_path = root / rel_path
        if not abs_path.exists():
            missing.append(rel_path)
            continue
        records.append(
            {
                "path": rel_path,
                "sha256": _sha256(abs_path),
                "bytes": abs_path.stat().st_size,
            }
        )

    if missing:
        print(f"[soc2-manifest][fail] missing evidence files: {', '.join(missing)}")
        return 1

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_sha(root),
        "evidence_count": len(records),
        "evidence": records,
    }
    output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"[soc2-manifest] wrote {output.relative_to(root)} with {len(records)} evidence items")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

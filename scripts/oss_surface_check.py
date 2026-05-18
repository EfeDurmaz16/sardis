#!/usr/bin/env python3
"""Fail if private/company material is tracked in the public OSS repo."""

from __future__ import annotations

import subprocess
import sys


BLOCKED_PREFIXES = (
    "docs/audits/evidence/",
    "docs/cdp/",
    "docs/compliance/",
    "docs/gtm/",
    "docs/hiring/",
    "docs/investor/",
    "docs/ops/",
    "docs/outbound/",
    "docs/outreach/",
    "docs/partnerships/",
    "docs/runbooks/",
    "docs/sales/",
    "docs/superpowers/",
    "docs/compliance/soc2/",
    "docs/yc/",
    "scripts/gtm/",
    "scripts/outreach/",
)

BLOCKED_FILES = {
    "docs/business-plan.md",
    "docs/DEPLOYMENT-GUIDE-V2.md",
    "docs/investor-list.xlsx",
    "docs/investor-proof-memo-march-2026.md",
    "docs/PRODUCTION_DEPLOYMENT.md",
    "docs/production-runbook.md",
    "docs/operations/dual-track-deployment.md",
    "docs/audits/claims-evidence.md",
    "docs/audits/control-testing-cadence-q1-2026.md",
    "docs/audits/final-remediation-report.md",
    "docs/audits/prelaunch-remediation-plan.md",
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    blocked: list[str] = []
    for path in tracked_files():
        if path in BLOCKED_FILES or path.startswith(BLOCKED_PREFIXES):
            blocked.append(path)

    if blocked:
        print("Private/company material is tracked in the public OSS repo:")
        for path in blocked:
            print(f"  - {path}")
        print("\nMove these files to a private repository or add a public-safe replacement.")
        return 1

    print("OSS surface check passed: no blocked private/company paths are tracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

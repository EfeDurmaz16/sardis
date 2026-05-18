#!/usr/bin/env python3
"""Fail if private/company material is tracked in the public OSS repo."""

from __future__ import annotations

import subprocess
import sys


BLOCKED_PREFIXES = (
    "docs/cdp/",
    "docs/hiring/",
    "docs/partnerships/",
    "docs/sales/",
    "docs/yc/",
    "scripts/gtm/",
    "scripts/outreach/",
)

BLOCKED_FILES = {
    "docs/business-plan.md",
    "docs/investor-list.xlsx",
    "docs/investor-proof-memo-march-2026.md",
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

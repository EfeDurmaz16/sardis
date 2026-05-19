#!/usr/bin/env python3
"""Validate GitHub issue and PR templates keep contributors on the OSS path."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_SNIPPETS: dict[str, tuple[str, ...]] = {
    ".github/pull_request_template.md": (
        "docs/oss/contribution-map.md",
        "docs/oss/public-private-boundary.md",
        "docs/oss/ci-cd.md",
        "pnpm run check:contributor",
        "Package maturity and contribution-map entries",
    ),
    ".github/ISSUE_TEMPLATE/bug_report.yml": (
        "pnpm run doctor",
        "pnpm run check:contributor",
        "docs/oss/contribution-map.md",
    ),
    ".github/ISSUE_TEMPLATE/contribution_task.yml": (
        "docs/oss/contribution-map.md",
        "pnpm run check:contributor",
    ),
    ".github/ISSUE_TEMPLATE/feature_request.yml": (
        "docs/oss/contribution-map.md",
        "private hosted product",
    ),
    ".github/ISSUE_TEMPLATE/security_or_payment_invariant.yml": (
        "GitHub Security Advisories",
        "Policy must run before provider execution",
    ),
}


def main() -> int:
    missing: list[str] = []

    for rel_path, snippets in REQUIRED_SNIPPETS.items():
        path = ROOT / rel_path
        if not path.exists():
            missing.append(f"{rel_path} is missing")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                missing.append(f"{rel_path} missing `{snippet}`")

    if missing:
        print("GitHub contributor template check failed:")
        for item in missing:
            print(f"  - {item}")
        return 1

    print("GitHub contributor template check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

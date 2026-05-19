#!/usr/bin/env python3
"""Validate OSS community health files and README links."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

REQUIRED_FILES = (
    "README.md",
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "LICENSE",
    ".github/CODEOWNERS",
    ".github/pull_request_template.md",
)

README_REQUIRED_LINKS = (
    "CONTRIBUTING.md",
    "CODE_OF_CONDUCT.md",
    "SECURITY.md",
    "SUPPORT.md",
    "LICENSE",
    "docs/oss/public-private-boundary.md",
    "docs/oss/contribution-map.md",
    "docs/oss/ci-cd.md",
)


def main() -> int:
    errors: list[str] = []

    for rel_path in REQUIRED_FILES:
        path = ROOT / rel_path
        if not path.exists():
            errors.append(f"Missing required OSS community health file: {rel_path}")

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for target in README_REQUIRED_LINKS:
        if target not in readme:
            errors.append(f"README.md does not reference {target}")

    if errors:
        print("Community health check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Community health check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

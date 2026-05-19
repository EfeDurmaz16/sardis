#!/usr/bin/env python3
"""Validate public package maturity documentation.

The OSS repo intentionally exposes many packages, but every tracked public
package must have a README and an entry in docs/packages.md so contributors can
understand its status before opening a PR.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DOC = ROOT / "docs" / "packages.md"
DEVELOPMENT_DOC = ROOT / "docs" / "development.md"


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tracked_package_dirs(files: list[str]) -> set[str]:
    packages: set[str] = set()
    for path in files:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "packages":
            packages.add(parts[1])
    return packages


def documented_package_dirs() -> set[str]:
    text = PACKAGES_DOC.read_text(encoding="utf-8")
    active_text = text.split("## Moved Private", 1)[0]
    return set(re.findall(r"`packages/([^`/]+)/`", active_text))


def main() -> int:
    files = tracked_files()
    tracked = tracked_package_dirs(files)
    documented = documented_package_dirs()
    development_text = DEVELOPMENT_DOC.read_text(encoding="utf-8")

    missing_docs = sorted(tracked - documented)
    stale_docs = sorted(documented - tracked)
    missing_readmes = sorted(
        pkg
        for pkg in tracked
        if f"packages/{pkg}/README.md" not in files
    )

    errors: list[str] = []
    if missing_docs:
        errors.append(
            "Tracked package directories missing from docs/packages.md:\n"
            + "\n".join(f"  - packages/{pkg}/" for pkg in missing_docs)
        )
    if stale_docs:
        errors.append(
            "docs/packages.md references package directories not tracked in git:\n"
            + "\n".join(f"  - packages/{pkg}/" for pkg in stale_docs)
        )
    if missing_readmes:
        errors.append(
            "Tracked package directories missing README.md:\n"
            + "\n".join(f"  - packages/{pkg}/README.md" for pkg in missing_readmes)
        )
    if "pnpm repo:package-validation" not in development_text:
        errors.append(
            "docs/development.md must document pnpm repo:package-validation so "
            "contributors can find package-specific validation commands."
        )

    if errors:
        print("\n\n".join(errors))
        return 1

    print(
        f"Package maturity check passed: {len(tracked)} tracked package directories "
        "are documented and have README.md."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

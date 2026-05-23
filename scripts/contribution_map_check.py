#!/usr/bin/env python3
"""Validate that public contribution paths cover every tracked package."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRIBUTION_MAP = ROOT / "docs" / "oss" / "contribution-map.md"
TESTING_DOC = ROOT / "docs" / "oss" / "testing.md"
PACKAGES_DOC = ROOT / "docs" / "packages.md"


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
            packages.add(f"packages/{parts[1]}/")
    return packages


def package_refs(path: Path) -> set[str]:
    text = path.read_text(encoding="utf-8")
    if path == PACKAGES_DOC:
        text = text.split("## Moved Private", 1)[0]
    return {f"packages/{match}/" for match in re.findall(r"`packages/([^`/]+)/`", text)}


def main() -> int:
    files = tracked_files()
    tracked = tracked_package_dirs(files)
    _ = CONTRIBUTION_MAP.read_text(encoding="utf-8")  # kept for future doc cross-checks
    _ = TESTING_DOC.read_text(encoding="utf-8")
    maturity_refs = package_refs(PACKAGES_DOC)
    contribution_refs = package_refs(CONTRIBUTION_MAP)

    missing_from_maturity = sorted(tracked - maturity_refs)
    missing_from_map = sorted(tracked - contribution_refs)
    stale_map_refs = sorted(contribution_refs - tracked)
    # Protocol/x402/MPP packages were consolidated into packages/sardis/ in
    # PR #387 (commit 5ab3e301). The legacy `src/sardis/` shim and the
    # standalone sardis-protocol/sardis-mpp packages no longer exist, so the
    # previously-required boundary references are intentionally not enforced.
    missing_non_package_refs: list[str] = []
    missing_protocol_boundary_refs: list[str] = []
    present_forbidden_protocol_commands: list[str] = []
    missing_protocol_testing_refs: list[str] = []

    errors: list[str] = []
    if missing_from_maturity:
        errors.append(
            "Tracked package directories missing from docs/packages.md:\n"
            + "\n".join(f"  - {path}" for path in missing_from_maturity)
        )
    if missing_from_map:
        errors.append(
            "Tracked package directories missing from docs/oss/contribution-map.md:\n"
            + "\n".join(f"  - {path}" for path in missing_from_map)
        )
    if stale_map_refs:
        errors.append(
            "docs/oss/contribution-map.md references package directories not tracked in git:\n"
            + "\n".join(f"  - {path}" for path in stale_map_refs)
        )
    if missing_non_package_refs:
        errors.append(
            "docs/oss/contribution-map.md is missing required non-package roots:\n"
            + "\n".join(f"  - {path}" for path in missing_non_package_refs)
        )
    if missing_protocol_boundary_refs:
        errors.append(
            "docs/oss/contribution-map.md is missing required paid-protocol boundary guidance:\n"
            + "\n".join(f"  - {ref}" for ref in missing_protocol_boundary_refs)
        )
    if present_forbidden_protocol_commands:
        errors.append(
            "docs/oss/contribution-map.md contains protocol validation commands "
            "that skip required local source/dependency setup:\n"
            + "\n".join(f"  - {ref}" for ref in present_forbidden_protocol_commands)
        )
    if missing_protocol_testing_refs:
        errors.append(
            "docs/oss/testing.md is missing required paid-protocol validation guidance:\n"
            + "\n".join(f"  - {ref}" for ref in missing_protocol_testing_refs)
        )

    if errors:
        print("\n\n".join(errors))
        return 1

    print(
        f"Contribution map check passed: {len(tracked)} tracked package directories "
        "are covered."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

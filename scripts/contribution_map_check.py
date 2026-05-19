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
    contribution_map_text = CONTRIBUTION_MAP.read_text(encoding="utf-8")
    testing_doc_text = TESTING_DOC.read_text(encoding="utf-8")
    maturity_refs = package_refs(PACKAGES_DOC)
    contribution_refs = package_refs(CONTRIBUTION_MAP)

    missing_from_maturity = sorted(tracked - maturity_refs)
    missing_from_map = sorted(tracked - contribution_refs)
    stale_map_refs = sorted(contribution_refs - tracked)
    required_non_package_refs = ["src/sardis/"]
    missing_non_package_refs = [
        ref
        for ref in required_non_package_refs
        if f"`{ref}`" not in contribution_map_text
    ]
    required_protocol_boundary_refs = [
        "x402 and MPP are separate protocol surfaces",
        "docs/architecture/x402-and-mpp.md",
        "tests/test_x402_middleware.py",
        "tests/test_mpp_router.py",
    ]
    missing_protocol_boundary_refs = [
        ref for ref in required_protocol_boundary_refs if ref not in contribution_map_text
    ]
    required_protocol_testing_refs = [
        "PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q",
        "PYTHONPATH=packages/sardis-mpp/src uv run --with pympp pytest packages/sardis-mpp/tests -q",
        "PYTHONPATH=packages/reference-api uv run pytest tests/test_x402_middleware.py tests/test_mpp_router.py -q",
        "Run those protocol targets separately.",
    ]
    missing_protocol_testing_refs = [
        ref for ref in required_protocol_testing_refs if ref not in testing_doc_text
    ]

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

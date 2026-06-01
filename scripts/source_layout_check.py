#!/usr/bin/env python3
"""Validate contributor-facing source layout invariants."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = (
    "packages/sardis-api",
    "packages/server-api",
    "packages/api",
    "packages/api/src",
    "packages/api/sardis_api",
    "packages/api/sardis",
    "packages/api/server",
    "apps/api/src",
    "apps/api/sardis_api",
    "apps/api/sardis",
    "apps/api/server/routers",
)

FORBIDDEN_TRACKED_PREFIXES = (
    "packages/reference-api/",
)

# The deployable reference API moved to the private service repository as part
# of the OSS/private split, so this gate no longer requires apps/api to exist.
# It now only guards against reintroducing forbidden API source layouts and
# keeps the published-library layout docs honest.
REQUIRED_PATHS = (
    "docs/oss/source-layout.md",
)

REQUIRED_DOC_SNIPPETS = {
    "docs/oss/contribution-map.md": (
        "docs/oss/source-layout.md",
    ),
    "docs/oss/testing.md": (
        "python3 scripts/source_layout_check.py",
        "source-layout guard",
    ),
}

FORBIDDEN_API_PACKAGE_PARTS = {
    "sardis_api",
}


def main() -> int:
    errors: list[str] = []

    tracked_paths = tracked_files()

    for prefix in FORBIDDEN_TRACKED_PREFIXES:
        matches = [path for path in tracked_paths if path.startswith(prefix)]
        if matches:
            errors.append(
                "Forbidden tracked API app path exists:\n"
                + "\n".join(f"  - {path}" for path in matches[:20])
            )

    for relative_path in FORBIDDEN_PATHS:
        path = ROOT / relative_path
        if path.exists():
            errors.append(f"Forbidden source layout path exists: {relative_path}")

    packages_root = ROOT / "packages"
    if packages_root.exists():
        for path in packages_root.rglob("*"):
            if not path.is_dir():
                continue
            relative = path.relative_to(ROOT).as_posix()
            if path.name in FORBIDDEN_API_PACKAGE_PARTS:
                errors.append(
                    "Forbidden repeated API import package exists: "
                    f"{relative}. Use apps/api/server for the "
                    "reference API and reserve src/<import_name> for published "
                    "library packages."
                )

    for relative_path in REQUIRED_PATHS:
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"Required source layout path is missing: {relative_path}")

    for relative_path, snippets in REQUIRED_DOC_SNIPPETS.items():
        path = ROOT / relative_path
        if not path.exists():
            errors.append(f"Required source layout doc is missing: {relative_path}")
            continue
        text = path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(
                    f"Required source layout doc snippet missing from {relative_path}: "
                    f"{snippet}"
                )

    if errors:
        print("Source layout check failed:")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nThe public repo must not reintroduce a backend API source tree. "
            "Do not add packages/sardis-api, packages/api, apps/api/src, or "
            "sardis_api import packages; the deployable API lives in the private "
            "service repository."
        )
        return 1

    print("Source layout check passed: API package paths are contributor-readable.")
    return 0


def tracked_files() -> list[str]:
    import subprocess

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


if __name__ == "__main__":
    sys.exit(main())

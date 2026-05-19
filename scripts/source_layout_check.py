#!/usr/bin/env python3
"""Validate contributor-facing source layout invariants."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

FORBIDDEN_PATHS = (
    "packages/sardis-api",
    "packages/server-api",
    "packages/api/src",
    "packages/api/sardis_api",
    "packages/api/sardis",
    "packages/api/sardis_server/routers",
)

REQUIRED_PATHS = (
    "packages/api/sardis_server",
    "packages/api/sardis_server/routes",
    "packages/api/sardis_server/routing",
    "docs/oss/source-layout.md",
)

REQUIRED_DOC_SNIPPETS = {
    "docs/oss/contribution-map.md": (
        "docs/oss/source-layout.md",
        "packages/api/sardis_server",
    ),
    "docs/oss/testing.md": (
        "python3 scripts/source_layout_check.py",
        "source-layout guard",
    ),
}


def main() -> int:
    errors: list[str] = []

    for relative_path in FORBIDDEN_PATHS:
        path = ROOT / relative_path
        if path.exists():
            errors.append(f"Forbidden source layout path exists: {relative_path}")

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
            "\nThe API source tree must stay at packages/api/sardis_server. "
            "Do not reintroduce packages/sardis-api, packages/api/src, "
            "sardis_api, or the legacy sardis_server/routers bucket."
        )
        return 1

    print("Source layout check passed: API package paths are contributor-readable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

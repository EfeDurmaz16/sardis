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
    "packages/reference-api/src",
    "packages/reference-api/sardis_api",
    "packages/reference-api/sardis",
    "packages/reference-api/server/routers",
)

REQUIRED_PATHS = (
    "packages/reference-api/server",
    "packages/reference-api/server/routes",
    "packages/reference-api/server/route_registry",
    "docs/oss/source-layout.md",
)

REQUIRED_DOC_SNIPPETS = {
    "docs/oss/contribution-map.md": (
        "docs/oss/source-layout.md",
        "packages/reference-api/server",
    ),
    "docs/oss/testing.md": (
        "python3 scripts/source_layout_check.py",
        "source-layout guard",
    ),
}

MAX_ROUTE_RELATIVE_PARTS = 2


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

    route_root = ROOT / "packages/reference-api/server/routes"
    if route_root.exists():
        for path in route_root.rglob("*.py"):
            relative_parts = path.relative_to(route_root).parts
            if len(relative_parts) > MAX_ROUTE_RELATIVE_PARTS:
                errors.append(
                    "Route implementation is nested too deeply: "
                    f"{path.relative_to(ROOT).as_posix()}"
                )

    if errors:
        print("Source layout check failed:")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nThe API source tree must stay at packages/reference-api/server. "
            "Do not reintroduce packages/sardis-api, packages/api, "
            "packages/reference-api/src, "
            "sardis_api, or the legacy server/routers bucket. Route "
            "implementations should stay at routes/<domain>/<module>.py."
        )
        return 1

    print("Source layout check passed: API package paths are contributor-readable.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

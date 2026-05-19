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

REQUIRED_PATHS = (
    "apps/api/server",
    "apps/api/server/routes",
    "apps/api/server/route_registry",
    "apps/api/server/route_registry/static_routes.py",
    "docs/oss/source-layout.md",
)

REQUIRED_DOC_SNIPPETS = {
    "docs/oss/source-layout.md": (
        "apps/api/server/route_registry/",
        "route_registry/static_routes.py",
        "card_runtime.py",
        "checkout_runtime.py",
        "funding_runtime.py",
        "1,000-line ceiling",
        "app.include_router",
        "packages/sardis-api/src/sardis_api/",
    ),
    "docs/oss/contribution-map.md": (
        "docs/oss/source-layout.md",
        "apps/api/server",
    ),
    "docs/oss/testing.md": (
        "python3 scripts/source_layout_check.py",
        "source-layout guard",
    ),
}

MAX_ROUTE_RELATIVE_PARTS = 2
MAX_MAIN_LINES = 1000

FORBIDDEN_MAIN_SNIPPETS = {
    ".include_router(": "route mounting must stay in route_registry helpers",
    "APIRouter": "main.py must not define route implementations",
    "from server.routes": "route implementation imports must stay out of main.py",
    "from .routes": "route implementation imports must stay out of main.py",
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

    route_root = ROOT / "apps/api/server/routes"
    if route_root.exists():
        for path in route_root.rglob("*.py"):
            relative_parts = path.relative_to(route_root).parts
            if len(relative_parts) > MAX_ROUTE_RELATIVE_PARTS:
                errors.append(
                    "Route implementation is nested too deeply: "
                    f"{path.relative_to(ROOT).as_posix()}"
                )
            if len(relative_parts) == MAX_ROUTE_RELATIVE_PARTS:
                domain, filename = relative_parts
                module_name = Path(filename).stem
                if module_name == domain:
                    errors.append(
                        "Route implementation repeats its domain folder: "
                        f"{path.relative_to(ROOT).as_posix()}. Rename the file "
                        "to the route role, such as lifecycle, accounts, screening, "
                        "records, webhooks, or capabilities."
                    )

    main_py = ROOT / "apps/api/server/main.py"
    if main_py.exists():
        main_lines = main_py.read_text(encoding="utf-8").splitlines()
        main_line_count = len(main_lines)
        if main_line_count > MAX_MAIN_LINES:
            errors.append(
                "API composition root is too large: "
                f"apps/api/server/main.py has {main_line_count} lines "
                f"(limit {MAX_MAIN_LINES}). Move route registration into "
                "route_registry/ or runtime construction into focused *_runtime.py helpers."
            )
        for line_no, line in enumerate(main_lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            for snippet, reason in FORBIDDEN_MAIN_SNIPPETS.items():
                if snippet in line:
                    errors.append(
                        "Forbidden API composition-root route wiring in "
                        f"apps/api/server/main.py:{line_no}: "
                        f"{reason}."
                    )

    if errors:
        print("Source layout check failed:")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nThe API source tree must stay at apps/api/server. "
            "Do not reintroduce packages/sardis-api, packages/api, "
            "apps/api/src, "
            "sardis_api, or the legacy server/routers bucket. Route "
            "implementations should stay at routes/<domain>/<module>.py."
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

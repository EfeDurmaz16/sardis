#!/usr/bin/env python3
"""Validate contributor-readable package layout rules.

This check is intentionally stricter for deployable applications than for
published libraries. Python libraries may use ``src/<import_package>`` for
packaging correctness; deployable apps should expose a short role-based import
root so contributors do not have to read the same product name at every level.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PACKAGE_LAYOUT_DOC = ROOT / "docs" / "oss" / "package-layout.md"
CONNECT_BOUNDARY_DOC = ROOT / "docs" / "architecture" / "connect-packages.md"
OPENAI_BOUNDARY_DOC = ROOT / "docs" / "architecture" / "openai-packages.md"
SDK_BOUNDARY_DOC = ROOT / "docs" / "architecture" / "sdk-packages.md"
SOURCE_LAYOUT_DOC = ROOT / "docs" / "oss" / "source-layout.md"
DEVELOPMENT_DOC = ROOT / "docs" / "development.md"
CONTRIBUTION_MAP = ROOT / "docs" / "oss" / "contribution-map.md"

FORBIDDEN_TRACKED_PREFIXES = (
    "packages/sardis-api/",
    "packages/server-api/",
    "packages/api/",
    "packages/reference-api/",
    "apps/api/src/",
    "apps/api/sardis_api/",
    "apps/api/sardis/",
    "apps/api/server/routers/",
)

FORBIDDEN_TRACKED_SEGMENTS = {
    "sardis_api": (
        "Do not reintroduce the repeated API import package. Use "
        "apps/api/server for the deployable reference API."
    ),
}

REFERENCE_API_REQUIRED_PATHS = (
    "apps/api/server/__init__.py",
    "apps/api/server/main.py",
    "apps/api/server/routes/",
    "apps/api/server/route_registry/",
)

REQUIRED_DOC_SNIPPETS = {
    PACKAGE_LAYOUT_DOC: (
        "Deployable applications use role-based source roots",
        "apps/api/server",
        "Python libraries may keep `src/<import_package>`",
        "Do not flatten published libraries only to shorten paths.",
        "Rename Candidates",
        "packages/sardis-connect/",
        "packages/sardis-connect-js/",
        "docs/architecture/connect-packages.md",
        "docs/architecture/openai-packages.md",
        "docs/architecture/sdk-packages.md",
    ),
    CONNECT_BOUNDARY_DOC: (
        "Python FastAPI",
        "TypeScript Node",
        "packages/sardis-connect/",
        "packages/sardis-connect-js/",
        "packages/sardis-sdk-js/",
        "PYTHONPATH=packages/sardis-connect/src uv run pytest packages/sardis-connect/tests -q",
        "pnpm --filter @sardis/connect build",
    ),
    OPENAI_BOUNDARY_DOC: (
        "OpenAI API Chat Completions",
        "OpenAI Agents SDK",
        "packages/sardis-openai/",
        "packages/sardis-openai-agents/",
        "uv run pytest packages/sardis-openai/tests -q",
        "uv run pytest packages/sardis-openai-agents/tests -q",
    ),
    SDK_BOUNDARY_DOC: (
        "Official Python API SDK",
        "Anthropic Claude Agent SDK",
        "packages/sardis-sdk-python/",
        "packages/sardis-agent-sdk/",
        "uv run pytest packages/sardis-sdk-python/tests -q",
        "PYTHONPATH=packages/sardis-agent-sdk/src uv run pytest packages/sardis-agent-sdk/tests -q",
    ),
    SOURCE_LAYOUT_DOC: (
        "docs/oss/package-layout.md",
        "apps/api/server",
        "packages/sardis-api/src/sardis_api/",
    ),
    DEVELOPMENT_DOC: (
        "pnpm repo:package-layout",
        "package layout",
    ),
    CONTRIBUTION_MAP: (
        "docs/oss/package-layout.md",
        "package layout",
    ),
}


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def has_tracked_path(files: list[str], prefix_or_file: str) -> bool:
    if prefix_or_file.endswith("/"):
        return any(path.startswith(prefix_or_file) for path in files)
    return prefix_or_file in files


def main() -> int:
    files = tracked_files()
    errors: list[str] = []

    for prefix in FORBIDDEN_TRACKED_PREFIXES:
        matches = [path for path in files if path.startswith(prefix)]
        if matches:
            errors.append(
                "Forbidden tracked package layout exists:\n"
                + "\n".join(f"  - {path}" for path in matches[:20])
            )

    for path in files:
        parts = path.split("/")
        for segment, reason in FORBIDDEN_TRACKED_SEGMENTS.items():
            if segment in parts:
                errors.append(f"Forbidden tracked path segment in {path}: {reason}")

    for required_path in REFERENCE_API_REQUIRED_PATHS:
        if not has_tracked_path(files, required_path):
            errors.append(f"Reference API layout path is missing: {required_path}")

    if has_tracked_path(files, "apps/api/src/"):
        errors.append(
            "The reference API must not use a nested src/ layer. It is a "
            "deployable application package; the source root is server/."
        )

    for doc_path, snippets in REQUIRED_DOC_SNIPPETS.items():
        if not doc_path.exists():
            errors.append(f"Required package layout doc is missing: {doc_path.relative_to(ROOT)}")
            continue
        text = doc_path.read_text(encoding="utf-8")
        for snippet in snippets:
            if snippet not in text:
                errors.append(
                    "Required package layout doc snippet missing from "
                    f"{doc_path.relative_to(ROOT)}: {snippet}"
                )

    if errors:
        print("Package layout check failed:")
        for error in errors:
            print(f"  - {error}")
        print(
            "\nDeployable apps must use short role-based source roots. Published "
            "libraries may keep src/<import_package>, but repeated API layouts "
            "such as packages/sardis-api/src/sardis_api are forbidden, and the "
            "reference API must stay at apps/api/server."
        )
        return 1

    print("Package layout check passed: contributor-facing package paths are documented.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

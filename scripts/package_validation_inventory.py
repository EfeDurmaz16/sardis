#!/usr/bin/env python3
"""Print validation guidance for tracked public packages.

This inventory complements docs/packages.md and docs/oss/contribution-map.md.
Those docs explain why a package exists and where it fits; this script gives
contributors a fast, current answer to "what can I run for this package?"
without depending on stale README copy.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGES_DOC = ROOT / "docs" / "packages.md"
BACKLOG_DOC = ROOT / "docs" / "oss" / "package-validation-backlog.md"
FALLBACK_VALIDATION = "pnpm run check:contributor"
EXTERNAL_TOOL_MANIFESTS = {"e2b.toml", "Nargo.toml"}
VALIDATION_OVERRIDES = {
    "packages/sardis-protocol": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-protocol/src uv run pytest packages/sardis-protocol/tests -q",
    ),
    "packages/sardis-mpp": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-mpp/src uv run --with pympp pytest packages/sardis-mpp/tests -q",
    ),
    "packages/sardis-ramp": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-ramp/src uv run pytest packages/sardis-ramp/tests -q",
    ),
    "packages/sardis-openclaw": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-openclaw/src uv run pytest packages/sardis-openclaw/tests -q",
    ),
    "packages/sardis-connect": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-connect/src uv run pytest packages/sardis-connect/tests -q",
    ),
    "packages/sardis-e2b": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-e2b uv run pytest packages/sardis-e2b/tests -q",
    ),
    "packages/sardis-coinbase": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-coinbase/src uv run pytest packages/sardis-coinbase/tests -q",
    ),
    "packages/sardis-agentkit": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-agentkit/src uv run pytest packages/sardis-agentkit/tests -q",
    ),
    "packages/sardis-agent-sdk": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-agent-sdk/src uv run pytest packages/sardis-agent-sdk/tests -q",
    ),
    "packages/sardis-openai": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-openai/src uv run pytest packages/sardis-openai/tests -q",
    ),
    "packages/sardis-openai-agents": (
        "pyproject.toml",
        "PYTHONPATH=packages/sardis-openai-agents uv run pytest packages/sardis-openai-agents/tests -q",
    ),
}


@dataclass(frozen=True)
class PackageValidation:
    path: str
    status: str
    manifest: str
    validation: str


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def tracked_package_dirs(files: list[str]) -> list[str]:
    packages: set[str] = set()
    for path in files:
        parts = path.split("/")
        if len(parts) >= 3 and parts[0] == "packages":
            packages.add(f"packages/{parts[1]}")
    return sorted(packages)


def documented_statuses() -> dict[str, str]:
    text = PACKAGES_DOC.read_text(encoding="utf-8").split("## Moved Private", 1)[0]
    statuses: dict[str, str] = {}
    current = "unknown"
    for line in text.splitlines():
        heading = re.match(r"^##\s+(.+)$", line)
        if heading:
            current = heading.group(1).strip().lower().replace(" ", "-")
            continue
        for match in re.findall(r"`(packages/[^`/]+/)`", line):
            statuses[match.rstrip("/")] = current
    return statuses


def package_json_validation(path: Path) -> tuple[str, str]:
    data = json.loads((path / "package.json").read_text(encoding="utf-8"))
    scripts = data.get("scripts") or {}
    package_name = data.get("name") or path.name
    if "test" in scripts:
        return "package.json", f"pnpm --filter {package_name} test"
    if "typecheck" in scripts:
        return "package.json", f"pnpm --filter {package_name} typecheck"
    if "build" in scripts:
        return "package.json", f"pnpm --filter {package_name} build"
    return "package.json", "pnpm run check:contributor"


def python_validation(path: Path) -> tuple[str, str]:
    tests_dir = path / "tests"
    if tests_dir.exists():
        return "pyproject.toml", f"uv run pytest {path.relative_to(ROOT).as_posix()}/tests -q"
    return "pyproject.toml", "pnpm run check:contributor"


def validation_for(path: Path) -> tuple[str, str]:
    rel = path.relative_to(ROOT).as_posix()
    if rel in VALIDATION_OVERRIDES:
        return VALIDATION_OVERRIDES[rel]
    if (path / "package.json").exists():
        return package_json_validation(path)
    if (path / "pyproject.toml").exists():
        return python_validation(path)
    if (path / "Cargo.toml").exists():
        return "Cargo.toml", f"cargo test --manifest-path {path.relative_to(ROOT).as_posix()}/Cargo.toml"
    if (path / "go.mod").exists():
        return "go.mod", f"(cd {path.relative_to(ROOT).as_posix()} && go test ./...)"
    if (path / "Nargo.toml").exists():
        return "Nargo.toml", f"(cd {path.relative_to(ROOT).as_posix()} && nargo check)"
    if (path / "e2b.toml").exists():
        return "e2b.toml", f"(cd {path.relative_to(ROOT).as_posix()} && e2b template build --name sardis-agent)"
    if (path / "openapi-actions.yaml").exists():
        return "openapi-actions.yaml", "pnpm check:openapi"
    return "README-only", "pnpm run check:contributor"


def inventory() -> list[PackageValidation]:
    statuses = documented_statuses()
    rows: list[PackageValidation] = []
    for package in tracked_package_dirs(tracked_files()):
        path = ROOT / package
        manifest, validation = validation_for(path)
        rows.append(
            PackageValidation(
                path=f"{package}/",
                status=statuses.get(package, "undocumented"),
                manifest=manifest,
                validation=validation,
            )
        )
    return rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Print or check public package validation coverage."
    )
    parser.add_argument(
        "--check-no-fallback",
        action="store_true",
        help=(
            "Fail if any tracked package still falls back to the repo-wide "
            "contributor gate instead of a package-owned validation command."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = inventory()
    backlog_text = BACKLOG_DOC.read_text(encoding="utf-8") if BACKLOG_DOC.exists() else ""
    errors: list[str] = []
    for row in rows:
        if row.status == "undocumented":
            errors.append(f"{row.path}: missing docs/packages.md status")
        if row.validation == FALLBACK_VALIDATION and f"`{row.path}`" not in backlog_text:
            errors.append(f"{row.path}: fallback validation is missing from {BACKLOG_DOC.relative_to(ROOT)}")
        if row.manifest in EXTERNAL_TOOL_MANIFESTS and f"`{row.path}`" not in backlog_text:
            errors.append(f"{row.path}: external-tool validation is missing from {BACKLOG_DOC.relative_to(ROOT)}")
        if args.check_no_fallback and row.validation == FALLBACK_VALIDATION:
            errors.append(f"{row.path}: package-owned validation is required")

    if errors:
        print("Package validation inventory is incomplete:")
        for error in errors:
            print(f"  - {error}")
        return 1

    if args.check_no_fallback:
        print("Package validation check passed: no package falls back to the repo-wide gate.")
        return 0

    print("Package validation inventory")
    print("| Package | Status | Manifest | Validation |")
    print("| --- | --- | --- | --- |")
    for row in rows:
        print(f"| `{row.path}` | `{row.status}` | `{row.manifest}` | `{row.validation}` |")
    return 0


if __name__ == "__main__":
    sys.exit(main())

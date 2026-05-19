#!/usr/bin/env python3
"""Fail when active public surfaces point contributors at stale API paths."""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

STALE_PATTERNS = (
    re.compile(r"\bsardis_api\b"),
    re.compile(r"\bsardis\.main\b"),
    re.compile(r"\bsardis\.routers\b"),
    re.compile(r"\bsardis/routes\b"),
    re.compile(r"\bsardis/routing\b"),
    re.compile(r"\bsardis/main\.py\b"),
    re.compile(r"packages/sardis-api"),
    re.compile(r"packages/server-api"),
    re.compile(r"packages/api/src/sardis_api"),
    re.compile(r"packages/api/src/sardis/routers"),
    re.compile(r"packages/api/src/sardis/main\.py"),
    re.compile(r"packages/api/src/server"),
    re.compile(r"packages/api/sardis_api"),
    re.compile(r"packages/api/sardis/routers"),
    re.compile(r"packages/api/sardis/main\.py"),
    re.compile(r"packages/reference-api/src/sardis_api"),
    re.compile(r"packages/reference-api/src/sardis/routers"),
    re.compile(r"packages/reference-api/src/sardis/main\.py"),
    re.compile(r"packages/reference-api/src/server"),
    re.compile(r"packages/reference-api/sardis_api"),
    re.compile(r"packages/reference-api/sardis/routers"),
    re.compile(r"packages/reference-api/sardis/main\.py"),
)

# Root tests are a documented legacy migration backlog. They are excluded from
# default contributor validation until each test is moved to its owning package.
IGNORED_PREFIXES = (
    "tests/",
    "docs/modernization/api-naming-migration.md",
    "docs/modernization/package-path-simplification.md",
    "docs/oss/source-layout.md",
    "docs/oss/root-test-migration.md",
    "scripts/root_test_inventory.py",
    "scripts/stale_api_path_check.py",
    "scripts/source_layout_check.py",
)

TEXT_SUFFIXES = {
    ".astro",
    ".css",
    ".html",
    ".js",
    ".json",
    ".md",
    ".mdx",
    ".mjs",
    ".py",
    ".rst",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yml",
    ".yaml",
}

SKIPPED_LOCAL_DIRS = {
    ".git",
    ".mypy_cache",
    ".next",
    ".omc",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    "__pycache__",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
}

MAX_LOCAL_FILE_BYTES = 1_000_000


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def local_files() -> list[str]:
    files: list[str] = []
    for current_root, dirnames, filenames in os.walk("."):
        dirnames[:] = [
            dirname for dirname in dirnames if dirname not in SKIPPED_LOCAL_DIRS
        ]
        root = Path(current_root)
        for filename in filenames:
            path = (root / filename).as_posix()
            if path.startswith("./"):
                path = path[2:]
            files.append(path)
    return sorted(files)


def should_check(path: str) -> bool:
    if path.startswith(IGNORED_PREFIXES):
        return False
    path_obj = Path(path)
    return path_obj.suffix in TEXT_SUFFIXES and path_obj.is_file()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail when public or local surfaces point to stale API paths."
    )
    parser.add_argument(
        "--include-local",
        action="store_true",
        help=(
            "Scan the full local working tree, including untracked and ignored "
            "text files. This is useful for cleanup audits and intentionally "
            "stricter than the default contributor guard."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    violations: list[tuple[str, int, str]] = []

    paths = local_files() if args.include_local else tracked_files()
    for path in paths:
        if not should_check(path):
            continue
        if not Path(path).exists():
            continue
        if args.include_local and Path(path).stat().st_size > MAX_LOCAL_FILE_BYTES:
            continue
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in STALE_PATTERNS):
                violations.append((path, line_no, line.strip()))

    if violations:
        surface = "local working tree" if args.include_local else "active public surfaces"
        print(f"Stale API import/path references found in {surface}:")
        for path, line_no, line in violations:
            print(f"  - {path}:{line_no}: {line}")
        print(
            "\nUse server imports and packages/reference-api/server paths, "
            "or move legacy material behind an explicit migration/archive boundary."
        )
        return 1

    surface = "local working tree" if args.include_local else "active public surfaces"
    print(f"Stale API path check passed: {surface} use server paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

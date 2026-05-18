#!/usr/bin/env python3
"""Fail when active public surfaces point contributors at stale API paths."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


STALE_PATTERNS = (
    re.compile(r"\bsardis_api\b"),
    re.compile(r"\bsardis\.main\b"),
    re.compile(r"\bsardis\.routers\b"),
    re.compile(r"packages/sardis-api"),
    re.compile(r"packages/api/src/sardis_api"),
    re.compile(r"packages/server-api/src/sardis_api"),
    re.compile(r"packages/server-api/src/sardis/routers"),
    re.compile(r"packages/server-api/src/sardis/main\.py"),
)

# Root tests are a documented legacy migration backlog. They are excluded from
# default contributor validation until each test is moved to its owning package.
IGNORED_PREFIXES = (
    "tests/",
    "docs/modernization/api-naming-migration.md",
    "docs/modernization/package-path-simplification.md",
    "scripts/stale_api_path_check.py",
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


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        check=True,
        capture_output=True,
        text=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def should_check(path: str) -> bool:
    if path.startswith(IGNORED_PREFIXES):
        return False
    return Path(path).suffix in TEXT_SUFFIXES


def main() -> int:
    violations: list[tuple[str, int, str]] = []

    for path in tracked_files():
        if not should_check(path):
            continue
        try:
            text = Path(path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue

        for line_no, line in enumerate(text.splitlines(), start=1):
            if any(pattern.search(line) for pattern in STALE_PATTERNS):
                violations.append((path, line_no, line.strip()))

    if violations:
        print("Stale API import/path references found in active public surfaces:")
        for path, line_no, line in violations:
            print(f"  - {path}:{line_no}: {line}")
        print(
            "\nUse sardis_server imports and packages/server-api/src/sardis_server paths, "
            "or move legacy material behind an explicit migration/archive boundary."
        )
        return 1

    print("Stale API path check passed: active public surfaces use sardis_server paths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

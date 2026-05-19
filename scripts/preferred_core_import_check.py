#!/usr/bin/env python3
"""Require public examples and README files to use the preferred core import."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY_IMPORT_PATTERN = re.compile(
    r"^\s*(from\s+sardis_v2_core\b|import\s+sardis_v2_core\b)"
)

PUBLIC_PREFIXES = (
    "README.md",
    "examples/",
    "packages/",
)

PUBLIC_SUFFIXES = (".md", ".py")
IGNORED_PARTS = {
    ".venv",
    ".pytest_cache",
    ".ruff_cache",
    "dist",
    "node_modules",
    "tests",
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


def should_check(path: str) -> bool:
    if not path.endswith(PUBLIC_SUFFIXES):
        return False
    if not any(path == prefix or path.startswith(prefix) for prefix in PUBLIC_PREFIXES):
        return False
    parts = set(Path(path).parts)
    if parts & IGNORED_PARTS:
        return False
    if path.startswith("packages/") and not (
        path.endswith("/README.md") or "/examples/" in path
    ):
        return False
    return True


def main() -> int:
    violations: list[tuple[str, int, str]] = []
    for path in tracked_files():
        if not should_check(path):
            continue
        text = (ROOT / path).read_text(encoding="utf-8")
        for line_no, line in enumerate(text.splitlines(), start=1):
            if LEGACY_IMPORT_PATTERN.search(line):
                violations.append((path, line_no, line.strip()))

    if violations:
        print("Public examples or READMEs use the legacy core import namespace:")
        for path, line_no, line in violations:
            print(f"  - {path}:{line_no}: {line}")
        print("\nUse `sardis_core` for new public examples. Keep `sardis_v2_core` only for compatibility notes.")
        return 1

    print("Preferred core import check passed: public examples use sardis_core.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

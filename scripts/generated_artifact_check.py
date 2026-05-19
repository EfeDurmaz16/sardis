#!/usr/bin/env python3
"""Fail if generated or local-only artifacts are tracked in git.

Use `python3 scripts/ignored_artifact_inventory.py` when the checkout is noisy
because ignored generated artifacts exist locally but are not tracked.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

BLOCKED_PATH_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(^|/)__pycache__/"),
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"(^|/)\.pytest_cache/"),
    re.compile(r"(^|/)\.ruff_cache/"),
    re.compile(r"(^|/)\.mypy_cache/"),
    re.compile(r"(^|/)\.next/"),
    re.compile(r"(^|/)\.vercel/"),
    re.compile(r"(^|/)coverage/"),
    re.compile(r"(^|/)htmlcov/"),
    re.compile(r"(^|/)dist/"),
    re.compile(r"(^|/)build/"),
    re.compile(r"^contracts/(out|cache|broadcast)/"),
)

BLOCKED_FILE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\.py[cod]$"),
    re.compile(r"\.tsbuildinfo$"),
    re.compile(r"\.DS_Store$"),
    re.compile(r"(^|/)\.coverage$"),
)

ALLOWED_PATHS = {
    "apps/api/dist/.gitignore",
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


def is_blocked(path: str) -> bool:
    if path in ALLOWED_PATHS:
        return False
    return any(pattern.search(path) for pattern in BLOCKED_PATH_PATTERNS) or any(
        pattern.search(path) for pattern in BLOCKED_FILE_PATTERNS
    )


def main() -> int:
    blocked = sorted(path for path in tracked_files() if is_blocked(path))
    if blocked:
        print("Generated or local-only artifacts are tracked:")
        for path in blocked:
            print(f"  - {path}")
        print("\nRemove these from git or add a narrow allowlist entry with justification.")
        return 1

    print("Generated artifact check passed: no blocked build/cache artifacts are tracked.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

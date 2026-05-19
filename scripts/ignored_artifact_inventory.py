#!/usr/bin/env python3
"""Inventory ignored generated artifacts that clutter local repo traversal.

The public repository intentionally ignores virtualenvs, package-manager
installs, build outputs, caches, and local test artifacts. They are harmless
when untracked, but they make raw `find` output and manual package roaming much
harder. This script gives contributors a focused view of cleanup-safe ignored
artifacts without reporting private ignored docs or local secret files.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

GENERATED_DIR_NAMES = {
    ".astro",
    ".hypothesis",
    ".mypy_cache",
    ".next",
    ".omc",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    ".vercel",
    "__pycache__",
    "build",
    "cache",
    "coverage",
    "dist",
    "htmlcov",
    "node_modules",
    "out",
    "target",
}

GENERATED_FILE_NAMES = {
    ".coverage",
    ".DS_Store",
    "coverage.json",
    "next-env.d.ts",
    "package-lock.json",
    "tsconfig.tsbuildinfo",
}

GENERATED_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
    ".tsbuildinfo",
}


def ignored_paths() -> list[Path]:
    result = subprocess.run(
        ["git", "status", "--ignored", "--short"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    paths: list[Path] = []
    for line in result.stdout.splitlines():
        if not line.startswith("!! "):
            continue
        raw = line[3:].strip()
        if not raw:
            continue
        paths.append(ROOT / raw.rstrip("/"))
    return sorted(paths)


def artifact_kind(path: Path) -> str | None:
    rel_parts = path.relative_to(ROOT).parts
    if any(part in GENERATED_DIR_NAMES for part in rel_parts):
        for part in rel_parts:
            if part in GENERATED_DIR_NAMES:
                return part
    if path.name in GENERATED_FILE_NAMES:
        return path.name
    if path.suffix in GENERATED_FILE_SUFFIXES:
        return path.suffix
    return None


def artifact_roots(paths: list[Path]) -> list[tuple[str, Path]]:
    roots: dict[Path, str] = {}
    for path in paths:
        kind = artifact_kind(path)
        if kind is None:
            continue
        rel = path.relative_to(ROOT)
        parts = rel.parts
        root_parts: list[str] = []
        for part in parts:
            root_parts.append(part)
            if part == kind:
                break
        root = ROOT.joinpath(*root_parts)
        roots[root] = kind
    return sorted((kind, path) for path, kind in roots.items())


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        return
    if path.exists():
        path.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "List ignored generated artifacts that are safe to delete from a "
            "local Sardis checkout."
        )
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Delete the listed generated artifacts. Omitted by default.",
    )
    args = parser.parse_args()

    artifacts = artifact_roots(ignored_paths())
    if not artifacts:
        print("Ignored artifact inventory passed: no generated artifacts found.")
        return 0

    counts = Counter(kind for kind, _path in artifacts)
    print("Ignored generated artifacts:")
    for kind, path in artifacts:
        print(f"  - {path.relative_to(ROOT)} ({kind})")

    print()
    print("Summary:")
    for kind, count in sorted(counts.items()):
        print(f"  - {kind}: {count}")

    if not args.delete:
        print()
        print("Dry run only. Re-run with --delete to remove these generated artifacts.")
        return 0

    for _kind, path in artifacts:
        remove_path(path)
    print()
    print(f"Deleted {len(artifacts)} ignored generated artifact path(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

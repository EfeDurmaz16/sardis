#!/usr/bin/env python3
"""Print a contributor-friendly repository tree.

The local checkout often contains ignored build outputs, virtualenvs, package
manager caches, and generated artifacts. Plain `find` output is therefore too
noisy for contributors trying to understand the source layout.
"""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path


DEFAULT_EXCLUDED_DIRS = {
    ".git",
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


def is_git_ignored(root: Path, path: Path) -> bool:
    rel = path.relative_to(root).as_posix()
    result = subprocess.run(
        ["git", "-C", str(root), "check-ignore", "-q", "--", rel],
        check=False,
    )
    return result.returncode == 0


def iter_paths(
    root: Path,
    max_depth: int,
    excluded_dirs: set[str],
    include_files: bool,
) -> list[Path]:
    results: list[Path] = []
    stack = [(root, 0)]

    while stack:
        current, depth = stack.pop()
        if depth > max_depth:
            continue

        if current != root:
            results.append(current)

        if depth == max_depth:
            continue

        children: list[Path] = []
        files: list[Path] = []
        for child in sorted(current.iterdir()):
            if child.is_file() and include_files and depth < max_depth:
                files.append(child)
                continue
            if not child.is_dir():
                continue
            if child.name in excluded_dirs or is_git_ignored(root, child):
                continue
            children.append(child)
        results.extend(files)
        stack.extend((child, depth + 1) for child in sorted(children, reverse=True))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Print a clean directory tree without ignored local artifacts."
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=3,
        help="Maximum directory depth to print from the repository root.",
    )
    parser.add_argument(
        "--root",
        default=".",
        help="Directory to inspect. Defaults to the current working directory.",
    )
    parser.add_argument(
        "--files",
        action="store_true",
        help="Also print non-ignored files within the selected depth.",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    for path in iter_paths(root, args.max_depth, DEFAULT_EXCLUDED_DIRS, args.files):
        print(path.relative_to(root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

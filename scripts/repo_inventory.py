#!/usr/bin/env python3
"""Print a generated-folder-aware Sardis repository inventory.

This is intentionally lightweight and credential-free. It is meant to be the
first command to run before modernization work, not a replacement for builds or
tests.
"""

from __future__ import annotations

import subprocess
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PRUNED_DIRS = {
    ".git",
    ".next",
    ".pytest_cache",
    ".ruff_cache",
    ".turbo",
    ".venv",
    ".vercel",
    "__pycache__",
    "build",
    "cache",
    "dist",
    "node_modules",
    "out",
}
GENERATED_MARKERS = {
    "contracts/out",
    "contracts/cache",
    "contracts/broadcast",
}
MANIFEST_NAMES = {
    "package.json",
    "pyproject.toml",
    "Cargo.toml",
    "go.mod",
    "Nargo.toml",
    "foundry.toml",
    "pnpm-workspace.yaml",
    "turbo.json",
    "vercel.json",
    "Dockerfile",
    "docker-compose.yml",
}


def is_pruned(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    if any(rel == marker or rel.startswith(f"{marker}/") for marker in GENERATED_MARKERS):
        return True
    return any(part in PRUNED_DIRS for part in path.relative_to(ROOT).parts)


def iter_files() -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    files: list[Path] = []
    for line in proc.stdout.splitlines():
        path = ROOT / line
        if is_pruned(path):
            continue
        if path.is_file():
            files.append(path)
    return sorted(files)


def main() -> int:
    files = iter_files()
    by_ext: Counter[str] = Counter()
    manifests: list[Path] = []
    top_level: defaultdict[str, int] = defaultdict(int)

    for path in files:
        rel = path.relative_to(ROOT)
        top_level[rel.parts[0]] += 1
        suffix = path.suffix.lower() or "[no extension]"
        by_ext[suffix] += 1
        if path.name in MANIFEST_NAMES:
            manifests.append(rel)

    print("Sardis repository inventory")
    print(f"root: {ROOT}")
    print(f"files scanned: {len(files)}")
    print()

    print("Top-level file counts")
    for name, count in sorted(top_level.items()):
        print(f"- {name}: {count}")
    print()

    print("Primary extensions")
    for suffix, count in by_ext.most_common(20):
        print(f"- {suffix}: {count}")
    print()

    print("Manifests")
    for manifest in sorted(manifests):
        print(f"- {manifest}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

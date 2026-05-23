#!/usr/bin/env python3
"""Validate local Markdown links in public contributor-facing docs."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
def _glob_md(*parts: str) -> list[Path]:
    directory = ROOT.joinpath(*parts)
    return sorted(directory.glob("*.md")) if directory.exists() else []


_CANDIDATE_DOCS = [
    ROOT / "README.md",
    ROOT / "CONTRIBUTING.md",
    ROOT / ".github" / "CONTRIBUTING.md",
    ROOT / "SECURITY.md",
    ROOT / ".github" / "SECURITY.md",
    ROOT / "SUPPORT.md",
    ROOT / ".github" / "SUPPORT.md",
    ROOT / "docs" / "development.md",
    ROOT / "docs" / "packages.md",
    ROOT / "docs" / "docs" / "index.md",
    ROOT / "docs" / "quickstart" / "README.md",
    *_glob_md("docs", "oss"),
    *_glob_md("docs", "architecture"),
]
PUBLIC_DOCS = [p for p in _CANDIDATE_DOCS if p.exists()]

MARKDOWN_LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def local_target(raw_target: str) -> str | None:
    target = raw_target.strip()
    if not target or target.startswith("#"):
        return None
    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return None
    return unquote(parsed.path)


def main() -> int:
    broken: list[str] = []

    for doc in PUBLIC_DOCS:
        text = doc.read_text(encoding="utf-8")
        for match in MARKDOWN_LINK_RE.finditer(text):
            target = local_target(match.group(1))
            if target is None:
                continue
            resolved = (doc.parent / target).resolve()
            try:
                resolved.relative_to(ROOT)
            except ValueError:
                broken.append(f"{doc.relative_to(ROOT)} -> {target} escapes repository root")
                continue
            if not resolved.exists():
                broken.append(f"{doc.relative_to(ROOT)} -> {target}")

    if broken:
        print("Broken local Markdown links in public docs:")
        for item in broken:
            print(f"  - {item}")
        return 1

    print(f"Public doc link check passed: {len(PUBLIC_DOCS)} files scanned.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate workflow Node, pnpm, and install commands match repo policy."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
EXPECTED_NODE = "22"
EXPECTED_PNPM = "9.15.4"


BAD_PNPM_INSTALL_RE = re.compile(r"run:\s*pnpm install\s*$")
NODE_VERSION_RE = re.compile(r"node-version:\s*['\"]?([^'\"\s]+)")
PNPM_VERSION_RE = re.compile(r"version:\s*([0-9][0-9.]+)")


def main() -> int:
    errors: list[str] = []

    for workflow in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        text = workflow.read_text(encoding="utf-8")
        rel = workflow.relative_to(ROOT)

        for line_no, line in enumerate(text.splitlines(), start=1):
            node_match = NODE_VERSION_RE.search(line)
            if node_match:
                node_version = node_match.group(1)
                if node_version != EXPECTED_NODE and node_version != "${{":
                    errors.append(f"{rel}:{line_no} uses node-version {node_version}; use {EXPECTED_NODE}")

            if "pnpm/action-setup" in line:
                nearby = "\n".join(text.splitlines()[line_no - 1 : line_no + 6])
                version_match = PNPM_VERSION_RE.search(nearby)
                if version_match and version_match.group(1) != EXPECTED_PNPM:
                    errors.append(
                        f"{rel}:{line_no} pins pnpm {version_match.group(1)}; use {EXPECTED_PNPM}"
                    )

            if BAD_PNPM_INSTALL_RE.search(line):
                errors.append(f"{rel}:{line_no} uses mutable `pnpm install`; use `pnpm install --frozen-lockfile`")

    if errors:
        print("Workflow toolchain check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Workflow toolchain check passed: Node, pnpm, and install commands match repo policy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

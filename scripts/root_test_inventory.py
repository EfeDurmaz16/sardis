#!/usr/bin/env python3
"""Inventory the legacy root test backlog.

The maintained contributor test suites live under package-owned `tests/`
directories. The repository-root `tests/` tree is a migration backlog; this
script keeps that backlog explicit so it cannot quietly grow.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

STALE_API_PATTERNS = (
    r"\bsardis_api\b",
    r"packages/sardis-api",
    r"packages/server-api",
    r"packages/api/sardis_api",
    r"packages/api/sardis/routers",
    r"packages/reference-api/sardis_api",
    r"packages/reference-api/sardis/routers",
    r"\bsardis\.routers\b",
    r"\bsardis\.main:create_app\b",
)

STALE_API_RE = re.compile("|".join(f"(?:{pattern})" for pattern in STALE_API_PATTERNS))

OWNER_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(api|auth|billing|checkout|compliance|cpn|fides|mpp|ramp|stripe|tap|wallet|x402|router|webhook|health|rate_limit|rbac|usage)"), "packages/reference-api/tests"),
    (re.compile(r"(ledger|receipt|reconciliation)"), "packages/sardis-ledger/tests"),
    (re.compile(r"(chain|solana|tempo|erc|token)"), "packages/sardis-chain/tests"),
    (re.compile(r"(policy|mandate|orchestrator|trust|evidence|reason|scheduler|cache)"), "packages/sardis-core/tests"),
    (re.compile(r"(sdk|facade|examples|readme|quickstart)"), "package docs/tests or package-owned examples"),
)


@dataclass(frozen=True)
class TestFile:
    path: str
    owner: str
    stale_api_refs: int


def git_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "tests"],
        check=True,
        capture_output=True,
        text=True,
    )
    return sorted(path for path in result.stdout.splitlines() if path.endswith(".py"))


def guess_owner(path: str) -> str:
    lowered = path.lower()
    for pattern, owner in OWNER_RULES:
        if pattern.search(lowered):
            return owner
    if "/integration/" in lowered or "/e2e/" in lowered:
        return "package-owned integration test or archive-candidate"
    return "needs owner review"


def analyze(path: str) -> TestFile:
    text = Path(path).read_text(encoding="utf-8")
    return TestFile(
        path=path,
        owner=guess_owner(path),
        stale_api_refs=len(STALE_API_RE.findall(text)),
    )


def build_report(files: list[TestFile]) -> str:
    total = len(files)
    stale = [item for item in files if item.stale_api_refs]
    owners = Counter(item.owner for item in files)

    lines = [
        "# Root Test Migration Inventory",
        "",
        "The repository-root `tests/` tree is a legacy migration backlog, not the default contributor test suite.",
        "Maintained tests live under package-owned `tests/` directories such as `packages/reference-api/tests/`, `packages/sardis-core/tests/`, `packages/sardis-ledger/tests/`, and `packages/sardis-chain/tests/`.",
        "",
        "## Current Snapshot",
        "",
        f"- Root Python test files: `{total}`",
        f"- Files with stale API import/path references: `{len(stale)}`",
        "- Default pytest path: `packages/reference-api/tests` from root `pyproject.toml`",
        "- Default npm test path: package-owned suites from `package.json`",
        "",
        "## Owner Buckets",
        "",
        "| Target owner | Root test files |",
        "| --- | ---: |",
    ]

    for owner, count in sorted(owners.items()):
        lines.append(f"| `{owner}` | {count} |")

    lines.extend(
        [
            "",
            "## Migration Rules",
            "",
            "1. Do not add new tests to root `tests/` unless the test genuinely spans multiple packages and has no clearer package owner.",
            "2. When touching a root test, either move it to the owning package suite or mark it as archive-candidate in the PR.",
            "3. API route tests should import `server.routes.<domain>` or test HTTP behavior through the maintained API app.",
            "4. Compatibility imports such as `sardis_api` and `sardis.routers` must not be reintroduced.",
            "5. Cross-package tests should document the packages they bind together and their required credentials or local services.",
            "",
            "## Stale API Reference Backlog",
            "",
            "| File | Suggested owner | Stale refs |",
            "| --- | --- | ---: |",
        ]
    )

    for item in stale:
        lines.append(f"| `{item.path}` | `{item.owner}` | {item.stale_api_refs} |")

    lines.extend(
        [
            "",
            "Regenerate this inventory with:",
            "",
            "```bash",
            "python3 scripts/root_test_inventory.py --write",
            "```",
        ]
    )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write docs/oss/root-test-migration.md instead of printing to stdout.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if docs/oss/root-test-migration.md is not current.",
    )
    args = parser.parse_args()

    files = [analyze(path) for path in git_files()]
    report = build_report(files)

    out = Path("docs/oss/root-test-migration.md")
    if args.write:
        out.write_text(report, encoding="utf-8")
        print(f"wrote {out}")
    elif args.check:
        if not out.exists():
            print(f"{out} is missing; run python3 scripts/root_test_inventory.py --write")
            return 1
        current = out.read_text(encoding="utf-8")
        if current != report:
            print(f"{out} is stale; run python3 scripts/root_test_inventory.py --write")
            return 1
        print("Root test inventory is current.")
    else:
        print(report, end="")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

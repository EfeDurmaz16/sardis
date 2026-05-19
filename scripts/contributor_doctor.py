#!/usr/bin/env python3
"""Check the local contributor toolchain before running heavier gates."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class CheckResult:
    name: str
    ok: bool
    detail: str
    fix: str
    warning: bool = False


def run(command: list[str]) -> subprocess.CompletedProcess[str] | None:
    if shutil.which(command[0]) is None:
        return None
    return subprocess.run(command, check=False, capture_output=True, text=True)


def parse_version(text: str) -> tuple[int, ...] | None:
    match = re.search(r"v?(\d+)(?:\.(\d+))?(?:\.(\d+))?", text)
    if not match:
        return None
    return tuple(int(part) for part in match.groups(default="0"))


def check_python() -> CheckResult:
    result = run(["python3", "--version"])
    if result is None:
        return CheckResult("python3", False, "missing", "Install Python 3.12 or newer.")
    version = parse_version(result.stdout or result.stderr)
    if version is None:
        return CheckResult("python3", False, (result.stdout or result.stderr).strip(), "Use Python 3.12 or newer.")
    ok = version >= (3, 12, 0)
    return CheckResult(
        "python3",
        ok,
        ".".join(str(part) for part in version),
        "Install Python 3.12+ and ensure `python3` resolves to it.",
    )


def check_node() -> CheckResult:
    result = run(["node", "--version"])
    if result is None:
        return CheckResult("node", False, "missing", "Install Node.js 22 LTS.")
    version = parse_version(result.stdout or result.stderr)
    if version is None:
        return CheckResult("node", False, (result.stdout or result.stderr).strip(), "Use Node.js 22 LTS.")
    ok = version[0] == 22
    return CheckResult(
        "node",
        ok,
        ".".join(str(part) for part in version),
        "Switch to Node.js 22 LTS, for example with `nvm use 22` or Volta.",
    )


def check_pnpm() -> CheckResult:
    result = run(["pnpm", "--version"])
    if result is None:
        return CheckResult("pnpm", False, "missing", "Install pnpm 9.15.4 or newer.")
    version = parse_version(result.stdout or result.stderr)
    if version is None:
        return CheckResult("pnpm", False, (result.stdout or result.stderr).strip(), "Use pnpm 9.15.4+.")
    ok = version >= (9, 15, 4)
    return CheckResult(
        "pnpm",
        ok,
        ".".join(str(part) for part in version),
        "Run `corepack enable` and `corepack prepare pnpm@9.15.4 --activate`.",
    )


def check_uv() -> CheckResult:
    result = run(["uv", "--version"])
    if result is None:
        return CheckResult("uv", False, "missing", "Install uv: https://docs.astral.sh/uv/")
    version = parse_version(result.stdout or result.stderr)
    if version is None:
        return CheckResult("uv", True, (result.stdout or result.stderr).strip(), "Keep uv current.", warning=True)
    ok = version >= (0, 5, 0)
    return CheckResult(
        "uv",
        ok,
        ".".join(str(part) for part in version),
        "Upgrade uv to a current release.",
    )


def main() -> int:
    checks = [check_python(), check_node(), check_pnpm(), check_uv()]
    failures = [check for check in checks if not check.ok and not check.warning]

    for check in checks:
        if check.ok:
            status = "ok"
        elif check.warning:
            status = "warn"
        else:
            status = "fail"
        print(f"{status:>4} {check.name:<8} {check.detail}")
        if not check.ok:
            print(f"     fix: {check.fix}")

    if failures:
        print("\nContributor doctor failed. Fix the toolchain before running bootstrap or CI gates.")
        return 1

    print("\nContributor doctor passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

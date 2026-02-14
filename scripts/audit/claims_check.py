#!/usr/bin/env python3
"""Release claim checker for Sardis launch/docs assertions.

Computes canonical counts used across README/landing/marketing:
- MCP tool count
- tests collected via pytest
- package counts (Python/NPM/meta)
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _run(cmd: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        cmd,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def get_mcp_tools_count() -> int:
    pkg = ROOT / "packages" / "sardis-mcp-server" / "package.json"
    data = json.loads(pkg.read_text(encoding="utf-8"))
    return len(data.get("mcp", {}).get("tools", []))


def get_package_counts() -> dict[str, int]:
    py = len(list((ROOT / "packages").glob("*/pyproject.toml")))
    npm = len(list((ROOT / "packages").glob("*/package.json")))
    root_py = int((ROOT / "pyproject.toml").exists())
    return {
        "python_packages_under_packages": py,
        "npm_packages_under_packages": npm,
        "root_meta_package": root_py,
        "total_packages_claimable": py + npm + root_py,
    }


def get_tests_collected() -> dict[str, int | None]:
    code, out, err = _run(["pytest", "--collect-only", "-q"])
    text = f"{out}\n{err}"

    # Example: "757/819 tests collected (62 deselected)"
    m = re.search(r"(\d+)/(\d+)\s+tests collected(?:\s*\((\d+) deselected\))?", text)
    if not m:
        return {
            "selected": None,
            "total": None,
            "deselected": None,
            "ok": 0,
        }

    selected = int(m.group(1))
    total = int(m.group(2))
    deselected = int(m.group(3)) if m.group(3) else 0
    return {
        "selected": selected,
        "total": total,
        "deselected": deselected,
        "ok": 1 if code == 0 else 0,
    }


def collect_claims() -> dict[str, object]:
    return {
        "mcp_tools": get_mcp_tools_count(),
        "packages": get_package_counts(),
        "tests_collected": get_tests_collected(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Check launch/documentation claim counts")
    parser.add_argument("--json", action="store_true", help="Emit compact JSON only")
    args = parser.parse_args()

    claims = collect_claims()

    if args.json:
        print(json.dumps(claims, separators=(",", ":")))
        return 0

    print(json.dumps(claims, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

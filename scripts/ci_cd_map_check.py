#!/usr/bin/env python3
"""Validate the public CI/CD map against workflow files and package scripts."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI_DOC = ROOT / "docs" / "oss" / "ci-cd.md"
PACKAGE_JSON = ROOT / "package.json"


def documented_workflows(text: str) -> set[str]:
    return set(re.findall(r"`(\.github/workflows/[^`]+\.ya?ml)`", text))


def documented_scripts(text: str) -> set[str]:
    scripts: set[str] = set()
    for match in re.findall(r"`pnpm run ([^`]+)`", text):
        script = match.strip()
        if " " not in script:
            scripts.add(script)
    return scripts


def documented_jobs(text: str) -> set[str]:
    jobs: set[str] = set()
    for row in text.splitlines():
        if not row.startswith("|"):
            continue
        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) < 3 or cells[0] in {"Gate", "---"}:
            continue
        for job in cells[2].split(","):
            job = job.strip().strip("`")
            if job and not job.endswith("jobs"):
                jobs.add(job)
    return jobs


def workflow_job_names() -> set[str]:
    names: set[str] = set()
    for workflow in (ROOT / ".github" / "workflows").glob("*.yml"):
        text = workflow.read_text(encoding="utf-8")
        names.update(re.findall(r"^\s{4}name:\s*(.+?)\s*$", text, flags=re.MULTILINE))
    for workflow in (ROOT / ".github" / "workflows").glob("*.yaml"):
        text = workflow.read_text(encoding="utf-8")
        names.update(re.findall(r"^\s{4}name:\s*(.+?)\s*$", text, flags=re.MULTILINE))
    return names


def package_scripts() -> set[str]:
    data = json.loads(PACKAGE_JSON.read_text(encoding="utf-8"))
    return set(data["scripts"])


def main() -> int:
    text = CI_DOC.read_text(encoding="utf-8")

    missing_workflows = sorted(
        workflow for workflow in documented_workflows(text) if not (ROOT / workflow).exists()
    )
    missing_scripts = sorted(documented_scripts(text) - package_scripts())
    missing_jobs = sorted(documented_jobs(text) - workflow_job_names())

    errors: list[str] = []
    if missing_workflows:
        errors.append(
            "docs/oss/ci-cd.md references missing workflow files:\n"
            + "\n".join(f"  - {path}" for path in missing_workflows)
        )
    if missing_scripts:
        errors.append(
            "docs/oss/ci-cd.md references missing package scripts:\n"
            + "\n".join(f"  - pnpm run {script}" for script in missing_scripts)
        )
    if missing_jobs:
        errors.append(
            "docs/oss/ci-cd.md references missing workflow job names:\n"
            + "\n".join(f"  - {job}" for job in missing_jobs)
        )

    if errors:
        print("\n\n".join(errors))
        return 1

    print("CI/CD map check passed: documented workflows, jobs, and scripts exist.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Validate that PR-triggered workflows do not expose private deploy secrets."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
PUBLIC_PR_EVENTS = {"pull_request", "pull_request_target"}
EXEMPT_SECRETS = {"GITHUB_TOKEN"}


def on_block(text: str) -> str:
    match = re.search(r"^on:\s*\n", text, flags=re.MULTILINE)
    if not match:
        return ""
    start = match.start()
    next_top_level = re.search(r"^(?!\s)(?!on:)[A-Za-z0-9_-]+:", text[match.end() :], flags=re.MULTILINE)
    if not next_top_level:
        return text[start:]
    return text[start : match.end() + next_top_level.start()]


def workflow_pr_events(text: str) -> set[str]:
    block = on_block(text)
    return {event for event in PUBLIC_PR_EVENTS if re.search(rf"^\s{{2}}{event}:", block, flags=re.MULTILINE)}


def job_blocks(text: str) -> list[tuple[str, str]]:
    jobs_match = re.search(r"^jobs:\s*$", text, flags=re.MULTILINE)
    if not jobs_match:
        return []
    jobs_text = text[jobs_match.end() :]
    matches = list(re.finditer(r"^\s{2}([A-Za-z0-9_-]+):\s*$", jobs_text, flags=re.MULTILINE))
    blocks: list[tuple[str, str]] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(jobs_text)
        blocks.append((match.group(1), jobs_text[start:end]))
    return blocks


def non_github_secrets(text: str) -> set[str]:
    return {
        secret
        for secret in re.findall(r"secrets\.([A-Z0-9_]+)", text)
        if secret not in EXEMPT_SECRETS
    }


def top_level_permissions(text: str) -> str:
    match = re.search(r"^permissions:\s*(.*?)$", text, flags=re.MULTILINE)
    if not match:
        return ""
    if match.group(1).strip():
        return match.group(1).strip()
    lines = text[match.end() :].splitlines()
    block: list[str] = []
    for line in lines:
        if line and not line.startswith((" ", "\t")):
            break
        if line.strip():
            block.append(line.strip())
    return "\n".join(block)


def job_condition(job_text: str) -> str:
    header = job_text.split("\n    steps:", maxsplit=1)[0]
    match = re.search(r"^\s{4}if:\s*(.+?)\s*$", header, flags=re.MULTILINE)
    if not match:
        return ""
    return match.group(1).strip()


def excludes_public_pr(condition: str) -> bool:
    normalized = condition.replace('"', "'")
    return (
        "github.event_name == 'push'" in normalized
        or "github.event_name != 'pull_request'" in normalized
        or "github.event_name != 'pull_request_target'" in normalized
    )


def main() -> int:
    errors: list[str] = []

    for workflow in sorted(WORKFLOWS.glob("*.yml")) + sorted(WORKFLOWS.glob("*.yaml")):
        text = workflow.read_text(encoding="utf-8")
        workflow_secrets = non_github_secrets(text)
        if workflow_secrets and top_level_permissions(text) == "read-all":
            errors.append(
                f"{workflow.relative_to(ROOT)} uses private secrets with top-level permissions: read-all; "
                "use explicit least-privilege permissions instead"
            )

        events = workflow_pr_events(text)
        if events and top_level_permissions(text) == "read-all":
            errors.append(
                f"{workflow.relative_to(ROOT)} is triggered by {', '.join(sorted(events))} "
                "with top-level permissions: read-all; use explicit least-privilege permissions"
            )
        if not events:
            continue

        for job_name, job_text in job_blocks(text):
            secrets = non_github_secrets(job_text)
            if not secrets:
                continue
            condition = job_condition(job_text)
            if excludes_public_pr(condition):
                continue
            errors.append(
                f"{workflow.relative_to(ROOT)} job {job_name} uses private secrets "
                f"on {', '.join(sorted(events))} without a PR-excluding job if: "
                f"{', '.join(sorted(secrets))}"
            )

    if errors:
        print("Workflow secret scope check failed:")
        for error in errors:
            print(f"  - {error}")
        return 1

    print("Workflow secret scope check passed: PR-triggered jobs do not expose private secrets.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

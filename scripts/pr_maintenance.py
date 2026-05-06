#!/usr/bin/env python3
"""Summarize and optionally nudge open Sardis pull requests.

The script is intentionally a thin GitHub CLI wrapper. It avoids adding another
API dependency, keeps mutation behind explicit flags, and makes the current PR
queue auditable from a terminal or scheduled workflow.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

DEPENDABOT_LOGINS = {"app/dependabot", "dependabot[bot]"}
REBASE_COMMENT = "@dependabot rebase"


@dataclass(frozen=True)
class PullRequestSummary:
    number: int
    title: str
    author: str
    head_ref: str
    merge_state: str
    updated_at: str
    is_draft: bool
    non_success_checks: int
    category: str


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=False, capture_output=True, text=True)


def _run_json(args: list[str]) -> Any:
    result = _run(args)
    if result.returncode != 0:
        raise SystemExit(result.stderr.strip() or result.stdout.strip())
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"failed to parse JSON from {' '.join(args)}: {exc}") from exc


def non_success_check_count(status_check_rollup: list[dict[str, Any]]) -> int:
    count = 0
    for check in status_check_rollup:
        conclusion = check.get("conclusion")
        status = check.get("status")
        if conclusion in {"SUCCESS", "SKIPPED"}:
            continue
        if status in {"COMPLETED"} and conclusion in {"SUCCESS", "SKIPPED"}:
            continue
        count += 1
    return count


def classify_pr(merge_state: str, is_draft: bool, non_success_checks: int) -> str:
    normalized_state = (merge_state or "UNKNOWN").upper()
    if is_draft:
        return "draft"
    if normalized_state == "DIRTY":
        return "conflict"
    if normalized_state == "BEHIND":
        return "needs-rebase"
    if non_success_checks > 0:
        return "waiting-on-checks"
    if normalized_state in {"CLEAN", "HAS_HOOKS", "UNKNOWN"}:
        return "ready-for-review"
    if normalized_state == "BLOCKED":
        return "blocked-by-policy"
    return "unknown"


def summarize_pr(raw: dict[str, Any]) -> PullRequestSummary:
    author = raw.get("author") or {}
    non_success_checks = non_success_check_count(raw.get("statusCheckRollup") or [])
    merge_state = str(raw.get("mergeStateStatus") or "UNKNOWN")
    is_draft = bool(raw.get("isDraft"))
    return PullRequestSummary(
        number=int(raw["number"]),
        title=str(raw.get("title") or ""),
        author=str(author.get("login") or ""),
        head_ref=str(raw.get("headRefName") or ""),
        merge_state=merge_state,
        updated_at=str(raw.get("updatedAt") or ""),
        is_draft=is_draft,
        non_success_checks=non_success_checks,
        category=classify_pr(merge_state, is_draft, non_success_checks),
    )


def fetch_open_prs(repo: str, limit: int) -> list[PullRequestSummary]:
    payload = _run_json(
        [
            "gh",
            "pr",
            "list",
            "--repo",
            repo,
            "--state",
            "open",
            "--limit",
            str(limit),
            "--json",
            "number,title,author,headRefName,updatedAt,isDraft,mergeStateStatus,statusCheckRollup",
        ]
    )
    return [summarize_pr(item) for item in payload]


def fetch_repo_settings(repo: str) -> dict[str, Any]:
    return _run_json(
        [
            "gh",
            "api",
            f"repos/{repo}",
            "--jq",
            "{allow_auto_merge,delete_branch_on_merge,default_branch}",
        ]
    )


def should_rebase(pr: PullRequestSummary, include_non_dependabot: bool) -> bool:
    if pr.category not in {"needs-rebase", "waiting-on-checks", "blocked-by-policy"}:
        return False
    if include_non_dependabot:
        return True
    return pr.author in DEPENDABOT_LOGINS


def comment_rebase(repo: str, pr: PullRequestSummary) -> None:
    result = _run(
        [
            "gh",
            "pr",
            "comment",
            str(pr.number),
            "--repo",
            repo,
            "--body",
            REBASE_COMMENT,
        ]
    )
    if result.returncode != 0:
        raise SystemExit(
            f"failed to comment on PR #{pr.number}: {result.stderr.strip() or result.stdout.strip()}"
        )


def report_payload(prs: list[PullRequestSummary], repo_settings: dict[str, Any]) -> dict[str, Any]:
    categories: dict[str, int] = {}
    for pr in prs:
        categories[pr.category] = categories.get(pr.category, 0) + 1
    return {
        "repo_settings": repo_settings,
        "total_open_prs": len(prs),
        "categories": categories,
        "pull_requests": [pr.__dict__ for pr in prs],
    }


def render_markdown(payload: dict[str, Any]) -> str:
    settings = payload["repo_settings"]
    lines = [
        "# PR Maintenance Report",
        "",
        f"- Open PRs: {payload['total_open_prs']}",
        f"- Auto-merge enabled: {settings.get('allow_auto_merge')}",
        f"- Delete branch on merge: {settings.get('delete_branch_on_merge')}",
        f"- Default branch: {settings.get('default_branch')}",
        "",
        "## Categories",
    ]
    for name, count in sorted(payload["categories"].items()):
        lines.append(f"- {name}: {count}")
    lines.extend(["", "## Pull Requests", ""])
    lines.append("| PR | Category | State | Checks | Author | Title |")
    lines.append("| --- | --- | --- | ---: | --- | --- |")
    for pr in payload["pull_requests"]:
        title = str(pr["title"]).replace("|", "\\|")
        lines.append(
            f"| #{pr['number']} | {pr['category']} | {pr['merge_state']} | "
            f"{pr['non_success_checks']} | {pr['author']} | {title} |"
        )
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize and optionally nudge open PRs")
    parser.add_argument("--repo", default="EfeDurmaz16/sardis")
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON")
    parser.add_argument(
        "--comment-rebase",
        action="store_true",
        help="Comment '@dependabot rebase' on selected stale PRs",
    )
    parser.add_argument(
        "--include-non-dependabot",
        action="store_true",
        help="Allow --comment-rebase to target non-Dependabot PRs too",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    prs = fetch_open_prs(args.repo, args.limit)
    settings = fetch_repo_settings(args.repo)

    if args.comment_rebase:
        for pr in prs:
            if should_rebase(pr, args.include_non_dependabot):
                comment_rebase(args.repo, pr)

    payload = report_payload(prs, settings)
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(render_markdown(payload))
    return 0


if __name__ == "__main__":
    sys.exit(main())

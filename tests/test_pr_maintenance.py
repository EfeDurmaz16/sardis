from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "pr_maintenance.py"
SPEC = importlib.util.spec_from_file_location("pr_maintenance", SCRIPT_PATH)
assert SPEC is not None
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules["pr_maintenance"] = MODULE
SPEC.loader.exec_module(MODULE)


def test_classify_conflict_before_checks() -> None:
    assert MODULE.classify_pr("DIRTY", False, 12) == "conflict"


def test_classify_stale_dependabot_pr() -> None:
    raw = {
        "number": 286,
        "title": "build(deps): bump axios",
        "author": {"login": "app/dependabot"},
        "headRefName": "dependabot/npm_and_yarn/axios-1.15.2",
        "updatedAt": "2026-05-06T00:00:00Z",
        "isDraft": False,
        "mergeStateStatus": "BEHIND",
        "statusCheckRollup": [
            {"name": "Python Lint & Test", "status": "COMPLETED", "conclusion": "SUCCESS"},
            {"name": "TypeScript SDK Build & Type Check", "status": "IN_PROGRESS"},
        ],
    }

    pr = MODULE.summarize_pr(raw)

    assert pr.category == "needs-rebase"
    assert pr.non_success_checks == 1
    assert MODULE.should_rebase(pr, include_non_dependabot=False) is True


def test_rebase_selection_skips_non_dependabot_by_default() -> None:
    pr = MODULE.PullRequestSummary(
        number=1,
        title="manual branch",
        author="efe",
        head_ref="feature/manual",
        merge_state="BEHIND",
        updated_at="2026-05-06T00:00:00Z",
        is_draft=False,
        non_success_checks=0,
        category="needs-rebase",
    )

    assert MODULE.should_rebase(pr, include_non_dependabot=False) is False
    assert MODULE.should_rebase(pr, include_non_dependabot=True) is True


def test_markdown_report_surfaces_repo_settings() -> None:
    payload = MODULE.report_payload(
        [
            MODULE.PullRequestSummary(
                number=178,
                title="chore(deps): bump mcp sdk",
                author="app/dependabot",
                head_ref="dependabot/npm_and_yarn/modelcontextprotocol/sdk-1.26.0",
                merge_state="DIRTY",
                updated_at="2026-05-06T00:00:00Z",
                is_draft=False,
                non_success_checks=4,
                category="conflict",
            )
        ],
        {"allow_auto_merge": False, "delete_branch_on_merge": False, "default_branch": "main"},
    )

    report = MODULE.render_markdown(payload)

    assert "Auto-merge enabled: False" in report
    assert "| #178 | conflict | DIRTY | 4 | app/dependabot | chore(deps): bump mcp sdk |" in report

# PR Maintenance

Sardis keeps a wide CI surface because payment, policy, signing, SDK, and demo
changes need different proof. That creates a noisy PR queue, especially when
Dependabot opens many package-specific updates. Use the PR maintenance command
as the first pass before manually inspecting individual PRs.

## Local Report

```bash
python3 scripts/pr_maintenance.py --repo EfeDurmaz16/sardis
```

For machine-readable output:

```bash
python3 scripts/pr_maintenance.py --repo EfeDurmaz16/sardis --json
```

The report groups open PRs into:

- `waiting-on-checks`: CI is still running or has failures.
- `needs-rebase`: the branch is behind the base branch.
- `conflict`: GitHub reports merge conflicts.
- `blocked-by-policy`: checks are green but branch protection or repo policy blocks merge.
- `ready-for-review`: no obvious merge blocker was found by the GitHub API.

## Rebase Dependabot PRs

The command is report-only by default. To comment `@dependabot rebase` on stale
Dependabot PRs:

```bash
python3 scripts/pr_maintenance.py --repo EfeDurmaz16/sardis --comment-rebase
```

The command only targets Dependabot PRs unless `--include-non-dependabot` is
passed. Do not use that flag for normal branch maintenance unless the branch
owner expects automated comments.

## GitHub Actions Report

`.github/workflows/pr-maintenance.yml` runs on weekdays and can also be run with
`workflow_dispatch`. It uploads both Markdown and JSON artifacts.

## Repo Settings Required For Auto-Merge

The Dependabot auto-merge workflow can only enable auto-merge if the repository
allows it. Confirm these settings before expecting unattended merges:

```bash
gh api repos/EfeDurmaz16/sardis --jq '{allow_auto_merge,delete_branch_on_merge,default_branch}'
```

Expected operating posture:

- `allow_auto_merge`: `true`
- `delete_branch_on_merge`: `true`
- default branch: `main`

If `allow_auto_merge` is `false`, Dependabot PRs may be rebased and checked, but
GitHub will reject `gh pr merge --auto`.

# Branch Protection Runbook

Date: 2026-02-25
Owner: Sardis Platform

## Goal

Protect `main` with:
- Required CI checks
- Code-owner review requirement
- Minimum approval count
- Linear history + conversation resolution

## Prerequisites

- GitHub CLI authenticated: `gh auth status`
- Repo admin permissions
- `.github/required-checks.json` updated with current CI job names

## Dry Run

```bash
./scripts/bootstrap_branch_protection.sh --repo EfeDurmaz16/sardis --branch main --dry-run
```

## Apply Protection

```bash
./scripts/bootstrap_branch_protection.sh --repo EfeDurmaz16/sardis --branch main
```

## Increase Required Approvals

```bash
APPROVING_REVIEW_COUNT=2 ./scripts/bootstrap_branch_protection.sh --repo EfeDurmaz16/sardis --branch main
```

## Verify Configuration

```bash
gh api /repos/EfeDurmaz16/sardis/branches/main/protection | jq .
```

Key fields to verify:
- `required_status_checks.contexts`
- `required_pull_request_reviews.require_code_owner_reviews`
- `required_pull_request_reviews.required_approving_review_count`
- `required_conversation_resolution.enabled`
- `required_linear_history.enabled`

## Notes

- Keep CI job names in `.github/required-checks.json` synchronized with workflow job names.
- If a required check is renamed in CI, protection must be reapplied.

#!/usr/bin/env bash
set -euo pipefail

# Bootstraps GitHub branch protection using .github/required-checks.json.
#
# Usage:
#   ./scripts/bootstrap_branch_protection.sh
#   ./scripts/bootstrap_branch_protection.sh --repo EfeDurmaz16/sardis --branch main
#   ./scripts/bootstrap_branch_protection.sh --repo EfeDurmaz16/sardis --dry-run

REPO=""
BRANCH="main"
DRY_RUN="false"
APPROVING_REVIEW_COUNT="${APPROVING_REVIEW_COUNT:-1}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --repo)
      REPO="${2:-}"
      shift 2
      ;;
    --branch)
      BRANCH="${2:-main}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN="true"
      shift 1
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

if [[ -z "$REPO" ]]; then
  origin_url="$(git remote get-url origin 2>/dev/null || true)"
  if [[ -z "$origin_url" ]]; then
    echo "Could not infer repository from origin; pass --repo owner/name" >&2
    exit 1
  fi
  REPO="$(python3 - <<'PY'
import re
import subprocess

url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
url = url.removesuffix(".git")
m = re.search(r"github\.com[:/](?P<owner>[^/]+)/(?P<repo>[^/]+)$", url)
if not m:
    raise SystemExit("Could not parse GitHub owner/repo from origin URL")
print(f"{m.group('owner')}/{m.group('repo')}")
PY
)"
fi

if [[ ! -f ".github/required-checks.json" ]]; then
  echo ".github/required-checks.json is required" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "gh CLI is required. Install from https://cli.github.com/" >&2
  exit 1
fi

required_contexts_json="$(python3 - <<'PY'
import json
from pathlib import Path

cfg = json.loads(Path(".github/required-checks.json").read_text())
contexts = cfg.get("contexts", [])
strict = bool(cfg.get("strict", True))
payload = {"strict": strict, "contexts": contexts}
print(json.dumps(payload))
PY
)"

protection_payload="$(STATUS_CHECKS="$required_contexts_json" REVIEW_COUNT="$APPROVING_REVIEW_COUNT" python3 - <<'PY'
import json
import os

status_checks = json.loads(os.environ["STATUS_CHECKS"])
review_count = int(os.environ.get("REVIEW_COUNT", "1"))
payload = {
    "required_status_checks": status_checks,
    "enforce_admins": True,
    "required_pull_request_reviews": {
        "dismiss_stale_reviews": True,
        "require_code_owner_reviews": True,
        "required_approving_review_count": review_count,
    },
    "restrictions": None,
    "required_linear_history": True,
    "allow_force_pushes": False,
    "allow_deletions": False,
    "block_creations": False,
    "required_conversation_resolution": True,
    "lock_branch": False,
    "allow_fork_syncing": True,
}
print(json.dumps(payload))
PY
)"

echo "Repo: $REPO"
echo "Branch: $BRANCH"
echo "Required checks: $required_contexts_json"
echo "Approvals required: $APPROVING_REVIEW_COUNT"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "Dry-run payload:"
  echo "$protection_payload"
  exit 0
fi

gh api \
  --method PUT \
  -H "Accept: application/vnd.github+json" \
  "/repos/$REPO/branches/$BRANCH/protection" \
  --input <(echo "$protection_payload")

echo "Branch protection updated for $REPO:$BRANCH"

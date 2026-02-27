#!/usr/bin/env bash
# Pre-commit hook: detect accidental secret commits.
# Scans staged files for common secret patterns.
set -euo pipefail

STAGED=$(git diff --cached --name-only --diff-filter=ACM)
if [ -z "$STAGED" ]; then
  exit 0
fi

ERRORS=0

# Patterns that indicate secrets
PATTERNS=(
  'sk_live_[A-Za-z0-9]+'         # Stripe live key
  'sk_test_[A-Za-z0-9]+'         # Stripe test key
  'whsec_[A-Za-z0-9]+'           # Stripe webhook secret
  'AKIA[0-9A-Z]{16}'             # AWS access key
  'sk-[A-Za-z0-9]{20,}'          # OpenAI key
  'ghp_[A-Za-z0-9]{36}'          # GitHub PAT
  'gho_[A-Za-z0-9]{36}'          # GitHub OAuth
  'xoxb-[0-9]+-[A-Za-z0-9]+'    # Slack bot token
  'xoxp-[0-9]+-[A-Za-z0-9]+'    # Slack user token
  'eyJ[A-Za-z0-9_-]{20,}\.'      # JWT token
  'PRIVATE KEY-----'              # PEM private key
  'password\s*=\s*"[^"]{8,}"'    # Hardcoded password
)

# Files to skip
SKIP_PATTERN='(\.lock$|\.min\.|node_modules|__pycache__|\.example$|detect-secrets\.sh$|\.pre-commit-config\.yaml$)'

for file in $STAGED; do
  # Skip binary, lock, and minified files
  if echo "$file" | grep -qE "$SKIP_PATTERN"; then
    continue
  fi

  # Skip files that don't exist (deleted)
  if [ ! -f "$file" ]; then
    continue
  fi

  for pattern in "${PATTERNS[@]}"; do
    MATCHES=$(grep -nE "$pattern" "$file" 2>/dev/null || true)
    if [ -n "$MATCHES" ]; then
      echo "ERROR: Possible secret detected in $file"
      echo "$MATCHES" | head -3
      echo ""
      ERRORS=$((ERRORS + 1))
    fi
  done
done

if [ $ERRORS -gt 0 ]; then
  echo "========================================="
  echo "BLOCKED: $ERRORS potential secret(s) found"
  echo "If these are false positives, commit with:"
  echo "  git commit --no-verify"
  echo "========================================="
  exit 1
fi

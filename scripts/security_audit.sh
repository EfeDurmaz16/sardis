#!/usr/bin/env bash
# Sardis Security Audit Script
#
# Runs automated security scanning tools and generates a report.
# Prerequisites: pip install trufflehog safety; npm install; pip install slither-analyzer
#
# Usage: ./scripts/security_audit.sh

set -euo pipefail

REPORT_DIR="security-audit-report"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_FILE="${REPORT_DIR}/audit_${TIMESTAMP}.md"

mkdir -p "$REPORT_DIR"

echo "# Sardis Security Audit Report" > "$REPORT_FILE"
echo "Date: $(date -u +%Y-%m-%dT%H:%M:%SZ)" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

PASS=0
FAIL=0

run_check() {
    local name="$1"
    local cmd="$2"

    echo "## $name" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
    echo "Running: $name..."

    if eval "$cmd" >> "$REPORT_FILE" 2>&1; then
        echo "**Status: PASS**" >> "$REPORT_FILE"
        PASS=$((PASS + 1))
    else
        echo "**Status: ISSUES FOUND**" >> "$REPORT_FILE"
        FAIL=$((FAIL + 1))
    fi
    echo "" >> "$REPORT_FILE"
}

# 1. Secret scanning with TruffleHog
if command -v trufflehog &>/dev/null; then
    run_check "Secret Scanning (TruffleHog)" \
        "trufflehog filesystem . --no-update --only-verified 2>&1 | head -200"
else
    echo "## Secret Scanning (TruffleHog)" >> "$REPORT_FILE"
    echo "SKIPPED: trufflehog not installed (pip install trufflehog)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

# 2. Python dependency vulnerabilities
if command -v safety &>/dev/null; then
    run_check "Python Vulnerabilities (Safety)" \
        "safety check 2>&1 | head -100"
else
    echo "## Python Vulnerabilities (Safety)" >> "$REPORT_FILE"
    echo "SKIPPED: safety not installed (pip install safety)" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

# 3. npm audit
if [ -f "package-lock.json" ] || [ -f "pnpm-lock.yaml" ]; then
    if command -v pnpm &>/dev/null; then
        run_check "JavaScript Vulnerabilities (pnpm audit)" \
            "pnpm audit --no-fix 2>&1 | head -100"
    elif command -v npm &>/dev/null; then
        run_check "JavaScript Vulnerabilities (npm audit)" \
            "npm audit 2>&1 | head -100"
    fi
fi

# 4. Solidity analysis with Slither
if command -v slither &>/dev/null && [ -d "contracts" ]; then
    run_check "Solidity Analysis (Slither)" \
        "cd contracts && slither src/ --exclude-dependencies 2>&1 | head -200"
else
    echo "## Solidity Analysis (Slither)" >> "$REPORT_FILE"
    echo "SKIPPED: slither not installed or contracts/ not found" >> "$REPORT_FILE"
    echo "" >> "$REPORT_FILE"
fi

# 5. Check for common misconfigurations
echo "## Configuration Checks" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Check for hardcoded secrets in source
echo "### Hardcoded Secrets Grep" >> "$REPORT_FILE"
if grep -rn --include="*.py" --include="*.ts" --include="*.js" \
    -E '(sk_live_|sk_test_|AKIA|password\s*=\s*["\047][^"\047]{8,})' \
    packages/ sardis/ dashboard/src/ 2>/dev/null | head -20; then
    echo "**WARNING: Potential hardcoded secrets found above**" >> "$REPORT_FILE"
    FAIL=$((FAIL + 1))
else
    echo "No hardcoded secrets detected." >> "$REPORT_FILE"
    PASS=$((PASS + 1))
fi
echo "" >> "$REPORT_FILE"

# Check .env files are gitignored
echo "### .env Files in Git" >> "$REPORT_FILE"
if git ls-files '*.env' '.env*' 2>/dev/null | grep -v '.env.example' | head -5; then
    echo "**WARNING: .env files tracked in git**" >> "$REPORT_FILE"
    FAIL=$((FAIL + 1))
else
    echo "No .env files tracked in git." >> "$REPORT_FILE"
    PASS=$((PASS + 1))
fi
echo "" >> "$REPORT_FILE"

# Summary
echo "---" >> "$REPORT_FILE"
echo "## Summary" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"
echo "- Checks passed: $PASS" >> "$REPORT_FILE"
echo "- Checks with issues: $FAIL" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

echo ""
echo "Audit complete. Report saved to: $REPORT_FILE"
echo "Passed: $PASS | Issues: $FAIL"

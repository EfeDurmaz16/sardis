#!/usr/bin/env bash
set -euo pipefail

# =============================================================================
# Sardis Integration Smoke Test
#
# Tests each framework integration package against the staging API:
#   - Package import check (Python / JS)
#   - API health endpoint
#   - Basic wallet listing
#
# Usage:
#   ./scripts/integration_smoke_test.sh --api-url https://api.sardis.sh --api-key sk_test_...
# =============================================================================

# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------
if [[ -t 1 ]]; then
    GREEN='\033[0;32m'
    RED='\033[0;31m'
    YELLOW='\033[0;33m'
    BOLD='\033[1m'
    RESET='\033[0m'
else
    GREEN=''
    RED=''
    YELLOW=''
    BOLD=''
    RESET=''
fi

# ---------------------------------------------------------------------------
# Defaults & argument parsing
# ---------------------------------------------------------------------------
API_URL="https://api.sardis.sh"
API_KEY=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --api-url)
            API_URL="$2"
            shift 2
            ;;
        --api-key)
            API_KEY="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [--api-url URL] [--api-key KEY]"
            echo ""
            echo "Options:"
            echo "  --api-url   API base URL (default: https://api.sardis.sh)"
            echo "  --api-key   Sardis API key (required for authenticated endpoints)"
            echo "  -h, --help  Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# ---------------------------------------------------------------------------
# Counters
# ---------------------------------------------------------------------------
PASS_COUNT=0
FAIL_COUNT=0
SKIP_COUNT=0

pass() {
    local msg="$1"
    echo -e "  ${GREEN}[PASS]${RESET} ${msg}"
    ((PASS_COUNT++))
}

fail() {
    local msg="$1"
    local detail="${2:-}"
    if [[ -n "$detail" ]]; then
        echo -e "  ${RED}[FAIL]${RESET} ${msg} - ${detail}"
    else
        echo -e "  ${RED}[FAIL]${RESET} ${msg}"
    fi
    ((FAIL_COUNT++))
}

skip() {
    local msg="$1"
    local reason="${2:-}"
    echo -e "  ${YELLOW}[SKIP]${RESET} ${msg} - ${reason}"
    ((SKIP_COUNT++))
}

# ---------------------------------------------------------------------------
# Python import test
# ---------------------------------------------------------------------------
test_python_import() {
    local label="$1"       # display name, e.g. "sardis-crewai"
    local module="$2"      # Python module, e.g. "sardis_crewai"

    if ! command -v python3 &>/dev/null; then
        skip "${label} (Python) - import" "python3 not found"
        return
    fi

    local output
    if output=$(python3 -c "import ${module}" 2>&1); then
        pass "${label} (Python) - import OK"
    else
        # Extract the last line which usually has the meaningful error
        local err
        err=$(echo "$output" | tail -1)
        fail "${label} (Python) - import failed" "${err}"
    fi
}

# ---------------------------------------------------------------------------
# JS/TS require test
# ---------------------------------------------------------------------------
test_js_import() {
    local label="$1"       # display name, e.g. "@sardis/sdk"
    local pkg="$2"         # npm package, e.g. "@sardis/sdk"
    local pkg_dir="$3"     # local package dir for fallback resolution

    if ! command -v node &>/dev/null; then
        skip "${label} (JS) - import" "node not found"
        return
    fi

    local output
    # Try global require first, then resolve from the local package directory
    if output=$(node -e "try { require('${pkg}') } catch(e) { require('${pkg_dir}/dist/index.js') }" 2>&1); then
        pass "${label} (JS) - import OK"
    else
        local err
        err=$(echo "$output" | tail -1)
        fail "${label} (JS) - import failed" "${err}"
    fi
}

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------
test_health() {
    local url="${API_URL}/health"
    local http_code
    local body

    if ! command -v curl &>/dev/null; then
        skip "Health check" "curl not found"
        return
    fi

    body=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "${url}" 2>&1) || true

    if [[ "$body" == "200" ]]; then
        pass "Health check: OK (${url})"
    else
        fail "Health check: HTTP ${body}" "${url}"
    fi
}

test_wallets() {
    if [[ -z "$API_KEY" ]]; then
        skip "Wallet listing (GET /api/v2/wallets)" "no --api-key provided"
        return
    fi

    if ! command -v curl &>/dev/null; then
        skip "Wallet listing" "curl not found"
        return
    fi

    local url="${API_URL}/api/v2/wallets"
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 \
        -H "Authorization: Bearer ${API_KEY}" \
        -H "Content-Type: application/json" \
        "${url}" 2>&1) || true

    if [[ "$http_code" == "200" ]]; then
        pass "Wallet listing: OK (${url})"
    elif [[ "$http_code" == "401" ]]; then
        fail "Wallet listing: HTTP 401 Unauthorized" "check API key"
    else
        fail "Wallet listing: HTTP ${http_code}" "${url}"
    fi
}

# ---------------------------------------------------------------------------
# Resolve repo root (script may be called from anywhere)
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PACKAGES_DIR="${REPO_ROOT}/packages"

# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------
echo ""
echo -e "${BOLD}=== Sardis Integration Smoke Test ===${RESET}"
echo "API: ${API_URL}"
echo "Date: $(date +%Y-%m-%d)"
echo ""

# ---------------------------------------------------------------------------
# API connectivity tests
# ---------------------------------------------------------------------------
echo -e "${BOLD}--- API Connectivity ---${RESET}"
test_health
test_wallets
echo ""

# ---------------------------------------------------------------------------
# Python integration packages
# ---------------------------------------------------------------------------
echo -e "${BOLD}--- Python Packages ---${RESET}"

# Each entry: "display-name|python_module"
PYTHON_PACKAGES=(
    "sardis (root SDK)|sardis"
    "sardis-sdk-python|sardis_sdk"
    "sardis-crewai|sardis_crewai"
    "sardis-autogpt|sardis_autogpt"
    "sardis-browser-use|sardis_browser_use"
    "sardis-composio|sardis_composio"
    "sardis-openai-agents|sardis_openai_agents"
    "sardis-langchain|sardis_langchain"
    "sardis-adk|sardis_adk"
    "sardis-guardrails|sardis_guardrails"
    "sardis-coinbase|sardis_coinbase"
)

for entry in "${PYTHON_PACKAGES[@]}"; do
    IFS='|' read -r label module <<< "$entry"
    test_python_import "$label" "$module"
done
echo ""

# ---------------------------------------------------------------------------
# JS/TS integration packages
# ---------------------------------------------------------------------------
echo -e "${BOLD}--- JS/TS Packages ---${RESET}"

# Each entry: "display-name|npm-package|local-dir-name"
JS_PACKAGES=(
    "@sardis/sdk|@sardis/sdk|sardis-sdk-js"
    "@sardis/ai-sdk|@sardis/ai-sdk|sardis-ai-sdk"
    "@sardis/stagehand|@sardis/stagehand|sardis-stagehand"
    "@sardis/ramp|@sardis/ramp|sardis-ramp-js"
    "n8n-nodes-sardis|n8n-nodes-sardis|n8n-nodes-sardis"
)

for entry in "${JS_PACKAGES[@]}"; do
    IFS='|' read -r label pkg dir_name <<< "$entry"
    test_js_import "$label" "$pkg" "${PACKAGES_DIR}/${dir_name}"
done
echo ""

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
TOTAL=$((PASS_COUNT + FAIL_COUNT + SKIP_COUNT))

echo -e "${BOLD}--- Summary ---${RESET}"
echo -e "  Total:   ${TOTAL}"
echo -e "  ${GREEN}Passed:  ${PASS_COUNT}${RESET}"
if [[ $FAIL_COUNT -gt 0 ]]; then
    echo -e "  ${RED}Failed:  ${FAIL_COUNT}${RESET}"
else
    echo -e "  Failed:  0"
fi
if [[ $SKIP_COUNT -gt 0 ]]; then
    echo -e "  ${YELLOW}Skipped: ${SKIP_COUNT}${RESET}"
fi
echo ""

echo -e "Results: ${GREEN}${PASS_COUNT}/${TOTAL} passed${RESET}, ${RED}${FAIL_COUNT} failed${RESET}, ${YELLOW}${SKIP_COUNT} skipped${RESET}"
echo ""

# Exit with failure code if any tests failed
if [[ $FAIL_COUNT -gt 0 ]]; then
    exit 1
fi
exit 0

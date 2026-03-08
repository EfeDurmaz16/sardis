#!/usr/bin/env bash
set -euo pipefail

# ───────────────────────────────────────────────────────────────
# onboard_partner.sh — Automated partner onboarding for Sardis
#
# Creates an API key, wallet, pilot branch, and quickstart doc
# for a new integration partner.
# ───────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# ── Defaults ──────────────────────────────────────────────────

PARTNER_NAME=""
CONTACT_EMAIL=""
API_URL="https://api.sardis.sh"
ADMIN_KEY=""
LIMIT_PER_TX="5"
DAILY_LIMIT="50"
FRAMEWORK=""

# ── Usage ─────────────────────────────────────────────────────

usage() {
  cat <<EOF
Usage: $0 [OPTIONS]

Onboard a new Sardis integration partner.

Required:
  --partner-name NAME      Partner identifier (e.g. "crewai", "autogpt")
  --contact-email EMAIL    Partner contact email
  --admin-key KEY          Admin API key for provisioning

Optional:
  --api-url URL            Sardis API base URL (default: https://api.sardis.sh)
  --limit-per-tx USD       Per-transaction limit in USD (default: 5)
  --daily-limit USD        Daily spending limit in USD (default: 50)
  --framework NAME         Sardis integration framework they'll use
                           (e.g. crewai, autogpt, browser-use, openai-agents,
                            langchain, composio, n8n, vercel-ai)

Examples:
  $0 --partner-name crewai --contact-email dev@crewai.com --admin-key sk_live_...
  $0 --partner-name autogpt --contact-email eng@autogpt.com --admin-key sk_live_... \\
     --framework autogpt --limit-per-tx 10 --daily-limit 100
EOF
  exit 1
}

# ── Parse arguments ───────────────────────────────────────────

while [[ $# -gt 0 ]]; do
  case "$1" in
    --partner-name)
      PARTNER_NAME="$2"; shift 2 ;;
    --contact-email)
      CONTACT_EMAIL="$2"; shift 2 ;;
    --api-url)
      API_URL="$2"; shift 2 ;;
    --admin-key)
      ADMIN_KEY="$2"; shift 2 ;;
    --limit-per-tx)
      LIMIT_PER_TX="$2"; shift 2 ;;
    --daily-limit)
      DAILY_LIMIT="$2"; shift 2 ;;
    --framework)
      FRAMEWORK="$2"; shift 2 ;;
    --help|-h)
      usage ;;
    *)
      echo "Error: Unknown option '$1'"
      echo ""
      usage ;;
  esac
done

# ── Validate required inputs ─────────────────────────────────

errors=()

if [[ -z "$PARTNER_NAME" ]]; then
  errors+=("--partner-name is required")
fi

if [[ -z "$CONTACT_EMAIL" ]]; then
  errors+=("--contact-email is required")
fi

if [[ -z "$ADMIN_KEY" ]]; then
  errors+=("--admin-key is required")
fi

# Validate partner name format (lowercase alphanumeric + hyphens only)
if [[ -n "$PARTNER_NAME" && ! "$PARTNER_NAME" =~ ^[a-z0-9]([a-z0-9-]*[a-z0-9])?$ ]]; then
  errors+=("--partner-name must be lowercase alphanumeric with optional hyphens (e.g. 'crewai', 'auto-gpt')")
fi

# Validate email format (basic check)
if [[ -n "$CONTACT_EMAIL" && ! "$CONTACT_EMAIL" =~ ^[^@]+@[^@]+\.[^@]+$ ]]; then
  errors+=("--contact-email must be a valid email address")
fi

# Validate numeric limits
if ! [[ "$LIMIT_PER_TX" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  errors+=("--limit-per-tx must be a positive number")
fi

if ! [[ "$DAILY_LIMIT" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
  errors+=("--daily-limit must be a positive number")
fi

if [[ ${#errors[@]} -gt 0 ]]; then
  echo "Error: Invalid arguments"
  for err in "${errors[@]}"; do
    echo "  - $err"
  done
  echo ""
  usage
fi

# ── Dependency checks ────────────────────────────────────────

for cmd in curl git python3; do
  if ! command -v "$cmd" &>/dev/null; then
    echo "Error: '$cmd' is required but not found in PATH"
    exit 1
  fi
done

# ── Helper: extract JSON field via python3 ────────────────────

json_field() {
  local field="$1"
  python3 -c "
import json, sys
raw = sys.stdin.read().strip()
try:
    data = json.loads(raw) if raw else {}
except Exception:
    data = {}
print(data.get('$field', ''))
"
}

# ── Helper: mask API key (show only last 4 chars) ────────────

mask_key() {
  local key="$1"
  local len=${#key}
  if [[ $len -le 4 ]]; then
    echo "$key"
  else
    local masked_len=$((len - 4))
    local last4="${key: -4}"
    printf 'sk_...%s' "$last4"
  fi
}

# ── Helper: map framework to pip package name ────────────────

framework_pip_package() {
  case "$1" in
    crewai)          echo "sardis-crewai" ;;
    autogpt)         echo "sardis-autogpt" ;;
    browser-use)     echo "sardis-browser-use" ;;
    openai-agents)   echo "sardis-openai-agents" ;;
    langchain)       echo "sardis-langchain" ;;
    composio)        echo "sardis-composio" ;;
    vercel-ai)       echo "sardis-ai-sdk" ;;
    n8n)             echo "n8n-nodes-sardis" ;;
    *)               echo "sardis" ;;
  esac
}

# ── Helper: generate framework-specific example code ─────────

framework_example() {
  local fw="$1"
  local wallet_id="$2"

  case "$fw" in
    crewai)
      cat <<'PYEOF'
from crewai import Agent, Task, Crew
from sardis_crewai import SardisPaymentTool

payment_tool = SardisPaymentTool(
    api_key="YOUR_API_KEY",
    wallet_id="WALLET_ID",
)

agent = Agent(
    role="Procurement Agent",
    goal="Purchase supplies within budget",
    tools=[payment_tool],
)

task = Task(
    description="Buy 10 units of office supplies under $50",
    agent=agent,
)

crew = Crew(agents=[agent], tasks=[task])
crew.kickoff()
PYEOF
      ;;
    autogpt)
      cat <<'PYEOF'
# AutoGPT Block Configuration
# Add the Sardis payment block to your agent

from sardis_autogpt import SardisPaymentBlock

block = SardisPaymentBlock(
    api_key="YOUR_API_KEY",
    wallet_id="WALLET_ID",
)

# The block exposes:
#   - send_payment(destination, amount, token, chain)
#   - check_balance()
#   - get_transaction_history()
PYEOF
      ;;
    browser-use)
      cat <<'PYEOF'
from browser_use import Agent
from sardis_browser_use import SardisPaymentAction

agent = Agent(
    task="Navigate to store and purchase item",
    actions=[
        SardisPaymentAction(
            api_key="YOUR_API_KEY",
            wallet_id="WALLET_ID",
        )
    ],
)

await agent.run()
PYEOF
      ;;
    openai-agents)
      cat <<'PYEOF'
from agents import Agent, Runner
from sardis_openai_agents import sardis_payment_tool

agent = Agent(
    name="Payment Agent",
    instructions="You help users make payments safely.",
    tools=[
        sardis_payment_tool(
            api_key="YOUR_API_KEY",
            wallet_id="WALLET_ID",
        )
    ],
)

result = Runner.run_sync(agent, "Send $5 USDC to 0xABC...")
print(result.final_output)
PYEOF
      ;;
    langchain)
      cat <<'PYEOF'
from langchain.agents import initialize_agent, AgentType
from langchain_openai import ChatOpenAI
from sardis_langchain import SardisToolkit

toolkit = SardisToolkit(
    api_key="YOUR_API_KEY",
    wallet_id="WALLET_ID",
)

agent = initialize_agent(
    tools=toolkit.get_tools(),
    llm=ChatOpenAI(model="gpt-4"),
    agent=AgentType.OPENAI_FUNCTIONS,
)

agent.run("Check my wallet balance")
PYEOF
      ;;
    *)
      cat <<'PYEOF'
import sardis

client = sardis.Client(api_key="YOUR_API_KEY")

# Check wallet balance
wallet = client.wallets.get("WALLET_ID")
print(f"Balance: {wallet.balance} {wallet.currency}")

# Send a payment
tx = client.payments.send(
    wallet_id="WALLET_ID",
    destination="0xRecipientAddress",
    amount=5.00,
    token="USDC",
    chain="base",
)
print(f"Transaction: {tx.tx_hash} ({tx.status})")
PYEOF
      ;;
  esac
}

# ── Display name (capitalize first letter of each segment) ───

display_name() {
  echo "$1" | sed 's/-/ /g' | python3 -c "import sys; print(sys.stdin.read().strip().title())"
}

# ── Trim trailing slash from API URL ─────────────────────────

API_URL="${API_URL%/}"

# ── Begin onboarding ─────────────────────────────────────────

DISPLAY_NAME="$(display_name "$PARTNER_NAME")"

echo ""
echo "=== Sardis Partner Onboarding ==="
echo "Partner: $DISPLAY_NAME"
echo "Contact: $CONTACT_EMAIL"
echo ""

# ── Step 1: Create API key ───────────────────────────────────

printf "[1/4] Creating API key...     "

api_key_payload="$(cat <<JSON
{
  "name": "partner-${PARTNER_NAME}",
  "scopes": ["read", "write"],
  "rate_limit": 100,
  "expires_in_days": 90
}
JSON
)"

api_key_response="$(curl -sS -w "\n%{http_code}" -X POST "${API_URL}/api/v2/api-keys" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d "$api_key_payload" 2>&1)" || true

api_key_http_code="$(echo "$api_key_response" | tail -1)"
api_key_body="$(echo "$api_key_response" | sed '$d')"

if [[ "$api_key_http_code" != "201" ]]; then
  echo "FAILED"
  echo ""
  echo "Error: Failed to create API key (HTTP $api_key_http_code)"
  echo "Response: $api_key_body"
  exit 1
fi

PARTNER_API_KEY="$(echo "$api_key_body" | json_field "key")"
PARTNER_KEY_ID="$(echo "$api_key_body" | json_field "key_id")"

if [[ -z "$PARTNER_API_KEY" ]]; then
  echo "FAILED"
  echo ""
  echo "Error: API key not found in response"
  echo "Response: $api_key_body"
  exit 1
fi

MASKED_KEY="$(mask_key "$PARTNER_API_KEY")"
echo "OK  $MASKED_KEY"

# ── Step 2: Create wallet ────────────────────────────────────

printf "[2/4] Creating wallet...      "

wallet_payload="$(cat <<JSON
{
  "agent_id": "partner-${PARTNER_NAME}",
  "mpc_provider": "circle",
  "account_type": "mpc_v1",
  "currency": "USDC",
  "limit_per_tx": ${LIMIT_PER_TX},
  "limit_total": ${DAILY_LIMIT},
  "wallet_name": "partner-${PARTNER_NAME}-pilot",
  "chains": ["base"]
}
JSON
)"

wallet_response="$(curl -sS -w "\n%{http_code}" -X POST "${API_URL}/api/v2/wallets" \
  -H "Authorization: Bearer ${ADMIN_KEY}" \
  -H "Content-Type: application/json" \
  -d "$wallet_payload" 2>&1)" || true

wallet_http_code="$(echo "$wallet_response" | tail -1)"
wallet_body="$(echo "$wallet_response" | sed '$d')"

if [[ "$wallet_http_code" != "201" ]]; then
  echo "FAILED"
  echo ""
  echo "Error: Failed to create wallet (HTTP $wallet_http_code)"
  echo "Response: $wallet_body"
  exit 1
fi

WALLET_ID="$(echo "$wallet_body" | json_field "wallet_id")"

if [[ -z "$WALLET_ID" ]]; then
  echo "FAILED"
  echo ""
  echo "Error: wallet_id not found in response"
  echo "Response: $wallet_body"
  exit 1
fi

echo "OK  $WALLET_ID"

# ── Step 3: Create pilot branch ──────────────────────────────

printf "[3/4] Creating pilot branch... "

BRANCH_NAME="partner/${PARTNER_NAME}-pilot"

cd "$REPO_ROOT"

# Check if branch already exists (local or remote)
if git show-ref --verify --quiet "refs/heads/$BRANCH_NAME" 2>/dev/null; then
  echo "SKIP (branch already exists)"
elif git show-ref --verify --quiet "refs/remotes/origin/$BRANCH_NAME" 2>/dev/null; then
  echo "SKIP (remote branch already exists)"
else
  git branch "$BRANCH_NAME" 2>/dev/null || {
    echo "FAILED"
    echo ""
    echo "Error: Could not create branch '$BRANCH_NAME'"
    exit 1
  }
  echo "OK  $BRANCH_NAME"
fi

# ── Step 4: Generate quickstart document ─────────────────────

printf "[4/4] Generating quickstart... "

DOCS_DIR="${REPO_ROOT}/docs/partners"
QUICKSTART_PATH="${DOCS_DIR}/${PARTNER_NAME}-quickstart.md"

mkdir -p "$DOCS_DIR"

# Determine pip package
PIP_PACKAGE="$(framework_pip_package "${FRAMEWORK:-}")"

# Determine install instructions
if [[ "$PIP_PACKAGE" == "n8n-nodes-sardis" ]]; then
  INSTALL_CMD="npm install $PIP_PACKAGE"
elif [[ "$PIP_PACKAGE" == "sardis-ai-sdk" ]]; then
  INSTALL_CMD="npm install @sardis/ai-sdk"
else
  INSTALL_CMD="pip install $PIP_PACKAGE"
fi

# Generate example code
EXAMPLE_CODE="$(framework_example "${FRAMEWORK:-}" "$WALLET_ID")"
# Replace placeholders in example code
EXAMPLE_CODE="$(echo "$EXAMPLE_CODE" | sed "s|WALLET_ID|${WALLET_ID}|g")"

# Build framework section
FRAMEWORK_SECTION=""
if [[ -n "$FRAMEWORK" ]]; then
  FRAMEWORK_SECTION="- **Framework:** ${FRAMEWORK}"
fi

cat > "$QUICKSTART_PATH" <<MDEOF
# Sardis Quickstart: ${DISPLAY_NAME}

Welcome to Sardis! This guide will get you up and running with agent payments in minutes.

## Your Credentials

| Field | Value |
|-------|-------|
| **API Key** | \`${MASKED_KEY}\` |
| **Wallet ID** | \`${WALLET_ID}\` |
| **Per-Transaction Limit** | \$${LIMIT_PER_TX} USD |
| **Daily Limit** | \$${DAILY_LIMIT} USD |
| **API Base URL** | ${API_URL} |
${FRAMEWORK_SECTION:+| **Integration** | ${FRAMEWORK} |}

> **Important:** Your full API key was provided during onboarding. Store it securely — it cannot be retrieved again.

## Installation

\`\`\`bash
${INSTALL_CMD}
\`\`\`

## Quick Start

\`\`\`python
${EXAMPLE_CODE}
\`\`\`

## API Reference

### Check Wallet Balance

\`\`\`bash
curl -s ${API_URL}/api/v2/wallets/${WALLET_ID} \\
  -H "Authorization: Bearer \$SARDIS_API_KEY" | python3 -m json.tool
\`\`\`

### Send a Payment

\`\`\`bash
curl -s -X POST ${API_URL}/api/v2/wallets/${WALLET_ID}/transfer \\
  -H "Authorization: Bearer \$SARDIS_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "destination": "0xRecipientAddress",
    "amount": 5.00,
    "token": "USDC",
    "chain": "base"
  }' | python3 -m json.tool
\`\`\`

### List Transactions

\`\`\`bash
curl -s "${API_URL}/api/v2/wallets/${WALLET_ID}/transactions" \\
  -H "Authorization: Bearer \$SARDIS_API_KEY" | python3 -m json.tool
\`\`\`

## Spending Policies

Your wallet is configured with the following limits:

- **Per-transaction:** \$${LIMIT_PER_TX} USD maximum per payment
- **Daily total:** \$${DAILY_LIMIT} USD maximum across all payments per day

Need higher limits? Contact us and we will adjust them for your pilot.

## Architecture Overview

Sardis uses **non-custodial MPC wallets** — your agent's private keys are never stored on a single server. Every transaction is verified against your spending policy before execution, and all activity is recorded in an append-only audit ledger.

\`\`\`
Your Agent --> Sardis SDK --> Policy Engine --> MPC Signing --> Blockchain
                                  |
                            Spending limits
                            Rate limits
                            Allowlists
\`\`\`

## Support

- **Email:** support@sardis.sh
- **Partner contact:** ${CONTACT_EMAIL}
- **Documentation:** https://sardis.sh/docs
- **API Docs:** ${API_URL}/api/v2/docs
- **Status Page:** https://status.sardis.sh

---

*Generated on $(date -u +"%Y-%m-%d %H:%M:%S UTC") by Sardis partner onboarding.*
MDEOF

echo "OK  $QUICKSTART_PATH"

# ── Summary ──────────────────────────────────────────────────

echo ""
echo "Partner onboarding complete!"
echo "Next steps:"
echo "  1. Send quickstart doc to ${CONTACT_EMAIL}"
echo "  2. Schedule kickoff meeting"
echo "  3. Monitor API usage at ${API_URL}/api/v2/analytics"
echo ""

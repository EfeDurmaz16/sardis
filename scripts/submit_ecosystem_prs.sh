#!/usr/bin/env bash
# Sardis Ecosystem PR Submission Script
# Usage: ./scripts/submit_ecosystem_prs.sh [TARGET]
#
# Targets: langchain, vercel-ai, google-adk, crewai, autogpt, awesome-n8n, all
#
# Prerequisites:
#   - gh CLI authenticated (gh auth login)
#   - Packages published to PyPI/npm
#
# This script forks repos, creates branches, copies files, and opens PRs.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
PRS_DIR="$ROOT_DIR/prs"
GITHUB_USER=$(gh api user --jq '.login' 2>/dev/null || echo "EfeDurmaz16")

TARGET="${1:-all}"

echo "========================================="
echo "  Sardis Ecosystem PR Submission"
echo "  GitHub User: $GITHUB_USER"
echo "  Target: $TARGET"
echo "========================================="
echo ""

submit_langchain() {
    echo "--- LangChain Provider Docs ---"
    local REPO="langchain-ai/langchain"
    local BRANCH="docs/add-sardis-provider"

    # Fork if not already forked
    gh repo fork "$REPO" --clone=false 2>/dev/null || true

    # Clone fork
    local TMPDIR=$(mktemp -d)
    gh repo clone "$GITHUB_USER/langchain" "$TMPDIR/langchain" -- --depth=1
    cd "$TMPDIR/langchain"

    # Create branch and add file
    git checkout -b "$BRANCH"
    mkdir -p docs/docs/integrations/providers/
    cp "$PRS_DIR/langchain-docs/sardis.mdx" docs/docs/integrations/providers/sardis.mdx
    git add docs/docs/integrations/providers/sardis.mdx
    git commit -m "docs: add Sardis provider integration page"
    git push origin "$BRANCH"

    # Create PR
    gh pr create \
        --repo "$REPO" \
        --head "$GITHUB_USER:$BRANCH" \
        --title "docs: add Sardis provider integration page" \
        --body "$(cat <<'EOF'
## Summary
- Adds Sardis as a community integration provider
- Sardis enables AI agents to make policy-controlled payments through non-custodial MPC wallets
- Package: [`sardis-langchain`](https://pypi.org/project/sardis-langchain/) on PyPI

## What is Sardis?
Sardis is the Payment OS for the Agent Economy — infrastructure enabling AI agents to make real financial transactions safely with spending policy guardrails.

## Tools provided
- `SardisPaymentTool` — Execute policy-controlled payments
- `SardisBalanceTool` — Check balance and spending limits
- `SardisPolicyCheckTool` — Pre-check payment policy compliance

Links: [Website](https://sardis.sh) | [Docs](https://sardis.sh/docs) | [GitHub](https://github.com/EfeDurmaz16/sardis)
EOF
)"

    echo "LangChain PR submitted!"
    rm -rf "$TMPDIR"
    cd "$ROOT_DIR"
}

submit_vercel_ai() {
    echo "--- Vercel AI SDK Community Provider ---"
    local REPO="vercel/ai"
    local BRANCH="docs/add-sardis-community-provider"

    gh repo fork "$REPO" --clone=false 2>/dev/null || true

    local TMPDIR=$(mktemp -d)
    gh repo clone "$GITHUB_USER/ai" "$TMPDIR/ai" -- --depth=1
    cd "$TMPDIR/ai"

    git checkout -b "$BRANCH"
    mkdir -p content/providers/05-community-providers/
    cp "$PRS_DIR/vercel-ai-sdk/sardis.mdx" content/providers/05-community-providers/sardis.mdx
    git add content/providers/05-community-providers/sardis.mdx
    git commit -m "docs: add Sardis as community provider"
    git push origin "$BRANCH"

    gh pr create \
        --repo "$REPO" \
        --head "$GITHUB_USER:$BRANCH" \
        --title "docs: add Sardis as community provider" \
        --body "$(cat <<'EOF'
## Summary
- Adds Sardis to the Community Providers docs page
- Package: [`@sardis/ai-sdk`](https://www.npmjs.com/package/@sardis/ai-sdk) on npm

## What is Sardis?
Sardis provides AI SDK tools for policy-controlled stablecoin payments through non-custodial MPC wallets with spending guardrails.

## Tools: sardis_pay, sardis_create_hold, sardis_capture_hold, sardis_void_hold, sardis_check_policy, sardis_get_balance, sardis_get_spending

Links: [Website](https://sardis.sh) | [npm](https://www.npmjs.com/package/@sardis/ai-sdk) | [GitHub](https://github.com/EfeDurmaz16/sardis)
EOF
)"

    echo "Vercel AI SDK PR submitted!"
    rm -rf "$TMPDIR"
    cd "$ROOT_DIR"
}

submit_google_adk() {
    echo "--- Google ADK Community Tools ---"
    local REPO="google/adk-python-community"
    local BRANCH="feat/add-sardis-payment-tools"

    gh repo fork "$REPO" --clone=false 2>/dev/null || true

    local TMPDIR=$(mktemp -d)
    gh repo clone "$GITHUB_USER/adk-python-community" "$TMPDIR/adk-python-community" -- --depth=1
    cd "$TMPDIR/adk-python-community"

    git checkout -b "$BRANCH"
    mkdir -p tools/sardis/
    cp "$PRS_DIR/google-adk-community/tools/sardis/__init__.py" tools/sardis/__init__.py
    cp "$PRS_DIR/google-adk-community/tools/sardis/sardis_tool.py" tools/sardis/sardis_tool.py
    cp "$PRS_DIR/google-adk-community/tools/sardis/README.md" tools/sardis/README.md
    git add tools/sardis/
    git commit -m "feat: add Sardis payment tools for ADK agents"
    git push origin "$BRANCH"

    gh pr create \
        --repo "$REPO" \
        --head "$GITHUB_USER:$BRANCH" \
        --title "feat: add Sardis payment tools for ADK agents" \
        --body "$(cat <<'EOF'
## Summary
- Adds Sardis payment tools for Google ADK agents
- Package: [`sardis-adk`](https://pypi.org/project/sardis-adk/) on PyPI
- Tools: `sardis_pay`, `sardis_check_balance`, `sardis_check_policy`

## What is Sardis?
Sardis is the Payment OS for the Agent Economy — non-custodial MPC wallets with spending policy guardrails for AI agents.

Links: [Website](https://sardis.sh) | [PyPI](https://pypi.org/project/sardis-adk/) | [GitHub](https://github.com/EfeDurmaz16/sardis)
EOF
)"

    echo "Google ADK PR submitted!"
    rm -rf "$TMPDIR"
    cd "$ROOT_DIR"
}

submit_crewai() {
    echo "--- CrewAI Tools ---"
    local REPO="crewAIInc/crewAI-tools"
    local BRANCH="feat/add-sardis-payment-tool"

    gh repo fork "$REPO" --clone=false 2>/dev/null || true

    local TMPDIR=$(mktemp -d)
    gh repo clone "$GITHUB_USER/crewAI-tools" "$TMPDIR/crewAI-tools" -- --depth=1
    cd "$TMPDIR/crewAI-tools"

    git checkout -b "$BRANCH"
    mkdir -p crewai_tools/tools/sardis_payment_tool/
    cp "$PRS_DIR/crewai-tools/crewai_tools/tools/sardis_payment_tool/__init__.py" crewai_tools/tools/sardis_payment_tool/__init__.py
    cp "$PRS_DIR/crewai-tools/crewai_tools/tools/sardis_payment_tool/sardis_payment_tool.py" crewai_tools/tools/sardis_payment_tool/sardis_payment_tool.py
    git add crewai_tools/tools/sardis_payment_tool/
    git commit -m "feat: add SardisPaymentTool for policy-controlled payments"
    git push origin "$BRANCH"

    gh pr create \
        --repo "$REPO" \
        --head "$GITHUB_USER:$BRANCH" \
        --title "feat: add SardisPaymentTool for policy-controlled payments" \
        --body "$(cat <<'EOF'
## Summary
- Adds `SardisPaymentTool` for policy-controlled payments from CrewAI agents
- Package: [`sardis`](https://pypi.org/project/sardis/) on PyPI
- Full toolkit also available: [`sardis-crewai`](https://pypi.org/project/sardis-crewai/)

## Usage
```python
from crewai_tools import SardisPaymentTool
tool = SardisPaymentTool()
```

## What is Sardis?
Sardis is the Payment OS for the Agent Economy — non-custodial MPC wallets with spending policy guardrails for AI agents.

Links: [Website](https://sardis.sh) | [PyPI](https://pypi.org/project/sardis-crewai/) | [GitHub](https://github.com/EfeDurmaz16/sardis)
EOF
)"

    echo "CrewAI PR submitted!"
    rm -rf "$TMPDIR"
    cd "$ROOT_DIR"
}

submit_autogpt() {
    echo "--- AutoGPT Blocks ---"
    echo "NOTE: AutoGPT requires Discord discussion before PR submission."
    echo "1. Post in #plugins or #development on AutoGPT Discord"
    echo "2. Reference the sardis-autogpt package: https://pypi.org/project/sardis-autogpt/"
    echo "3. After discussion, submit PR to Significant-Gravitas/AutoGPT"
    echo ""
    echo "PR content is prepared at: $PRS_DIR/autogpt-blocks/"
    echo "Target file: autogpt_platform/backend/backend/blocks/sardis.py"
    echo ""
    echo "When ready, run:"
    echo "  gh repo fork Significant-Gravitas/AutoGPT --clone=false"
    echo "  # Clone, create branch, copy sardis.py, push, create PR"
}

submit_awesome_n8n() {
    echo "--- Awesome n8n ---"
    local REPO="restyler/awesome-n8n"
    local BRANCH="feat/add-sardis-community-node"

    gh repo fork "$REPO" --clone=false 2>/dev/null || true

    local TMPDIR=$(mktemp -d)
    gh repo clone "$GITHUB_USER/awesome-n8n" "$TMPDIR/awesome-n8n" -- --depth=1
    cd "$TMPDIR/awesome-n8n"

    git checkout -b "$BRANCH"

    # Find the community nodes section and add our entry
    # This is a best-effort insertion - may need manual adjustment
    if grep -q "Community nodes" README.md 2>/dev/null; then
        # Try to add after the last entry in community nodes section
        echo "" >> README.md
        echo "- [n8n-nodes-sardis](https://www.npmjs.com/package/n8n-nodes-sardis) - Policy-controlled payments for AI agents via Sardis MPC wallets" >> README.md
    fi

    git add README.md
    git commit -m "feat: add n8n-nodes-sardis community node"
    git push origin "$BRANCH"

    gh pr create \
        --repo "$REPO" \
        --head "$GITHUB_USER:$BRANCH" \
        --title "Add n8n-nodes-sardis - AI agent payment tools" \
        --body "$(cat <<'EOF'
## Summary
Adds [n8n-nodes-sardis](https://www.npmjs.com/package/n8n-nodes-sardis) to the community nodes list.

Sardis enables n8n workflows and AI agents to make policy-controlled stablecoin payments through non-custodial MPC wallets.

- Execute payments with spending policy checks
- Check wallet balance and limits
- Multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)

Links: [Website](https://sardis.sh) | [npm](https://www.npmjs.com/package/n8n-nodes-sardis) | [GitHub](https://github.com/EfeDurmaz16/sardis)
EOF
)"

    echo "Awesome n8n PR submitted!"
    rm -rf "$TMPDIR"
    cd "$ROOT_DIR"
}

# Execute based on target
case "$TARGET" in
    langchain) submit_langchain ;;
    vercel-ai) submit_vercel_ai ;;
    google-adk) submit_google_adk ;;
    crewai) submit_crewai ;;
    autogpt) submit_autogpt ;;
    awesome-n8n) submit_awesome_n8n ;;
    all)
        submit_langchain
        echo ""
        submit_vercel_ai
        echo ""
        submit_google_adk
        echo ""
        submit_crewai
        echo ""
        submit_awesome_n8n
        echo ""
        submit_autogpt
        ;;
    *) echo "Unknown target: $TARGET"; echo "Available: langchain, vercel-ai, google-adk, crewai, autogpt, awesome-n8n, all"; exit 1 ;;
esac

echo ""
echo "========================================="
echo "  Done!"
echo "========================================="

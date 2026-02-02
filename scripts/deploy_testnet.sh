#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# Sardis Testnet Deployment Wrapper (Base Sepolia)
# ============================================================================
# Wraps Foundry deployment of Sardis smart contracts on Base Sepolia.
# Default mode is dry-run. Pass --broadcast to actually deploy.
#
# Usage:
#   ./scripts/deploy_testnet.sh                  # dry run
#   ./scripts/deploy_testnet.sh --broadcast      # live deploy
#   ./scripts/deploy_testnet.sh --broadcast --verify  # deploy + verify on Basescan
# ============================================================================

CONTRACTS_DIR="$(cd "$(dirname "$0")/../contracts" && pwd)"
BASE_SEPOLIA_CHAIN_ID=84532
MIN_ETH_WEI=10000000000000000  # 0.01 ETH

BROADCAST=false
VERIFY=false

# --------------- Parse flags ---------------
for arg in "$@"; do
  case "$arg" in
    --broadcast) BROADCAST=true ;;
    --verify)    VERIFY=true ;;
    *)           echo "Unknown flag: $arg"; exit 1 ;;
  esac
done

# --------------- Helpers ---------------
info()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
ok()    { echo -e "\033[1;32m[OK]\033[0m    $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
fail()  { echo -e "\033[1;31m[FAIL]\033[0m  $*"; exit 1; }

# ============================================================================
# 1. PRE-FLIGHT CHECKS
# ============================================================================
info "Running pre-flight checks..."

# -- forge installed --
command -v forge >/dev/null 2>&1 || fail "forge is not installed. Install Foundry: https://getfoundry.sh"
ok "forge found: $(forge --version | head -1)"

# -- cast installed --
command -v cast >/dev/null 2>&1 || fail "cast is not installed. Install Foundry: https://getfoundry.sh"

# -- required env vars --
[[ -z "${BASE_SEPOLIA_RPC_URL:-}" ]] && fail "BASE_SEPOLIA_RPC_URL is not set"
[[ -z "${PRIVATE_KEY:-}" ]]          && fail "PRIVATE_KEY is not set"

ok "Required environment variables are set"

# -- verify chain ID --
CHAIN_ID=$(cast chain-id --rpc-url "$BASE_SEPOLIA_RPC_URL" 2>/dev/null) \
  || fail "Could not fetch chain ID from RPC. Check BASE_SEPOLIA_RPC_URL."

if [[ "$CHAIN_ID" != "$BASE_SEPOLIA_CHAIN_ID" ]]; then
  fail "Chain ID is $CHAIN_ID, expected $BASE_SEPOLIA_CHAIN_ID (Base Sepolia). Aborting to prevent mainnet deployment."
fi
ok "Chain ID confirmed: $CHAIN_ID (Base Sepolia)"

# -- deployer address and balance --
DEPLOYER=$(cast wallet address --private-key "$PRIVATE_KEY" 2>/dev/null) \
  || fail "Could not derive deployer address from PRIVATE_KEY"

BALANCE_WEI=$(cast balance "$DEPLOYER" --rpc-url "$BASE_SEPOLIA_RPC_URL" 2>/dev/null) \
  || fail "Could not fetch deployer balance"

BALANCE_ETH=$(cast from-wei "$BALANCE_WEI" 2>/dev/null || echo "unknown")

info "Deployer address: $DEPLOYER"
info "Deployer balance: $BALANCE_ETH ETH ($BALANCE_WEI wei)"

if [[ "$BALANCE_WEI" -lt "$MIN_ETH_WEI" ]]; then
  fail "Insufficient balance. Need at least 0.01 ETH for deployment gas. Fund the deployer on Base Sepolia."
fi
ok "Balance sufficient"

# -- compile --
info "Compiling contracts..."
(cd "$CONTRACTS_DIR" && forge build) || fail "Compilation failed"
ok "Contracts compiled"

# -- test suite --
info "Running test suite..."
(cd "$CONTRACTS_DIR" && forge test) || fail "Tests failed. Fix before deploying."
ok "All tests passed"

# ============================================================================
# 2. DEPLOYMENT
# ============================================================================
echo ""
echo "============================================"
if $BROADCAST; then
  echo "  MODE: LIVE BROADCAST"
else
  echo "  MODE: DRY RUN (simulation only)"
fi
echo "  Network:  Base Sepolia ($BASE_SEPOLIA_CHAIN_ID)"
echo "  Deployer: $DEPLOYER"
echo "  Balance:  $BALANCE_ETH ETH"
echo "============================================"
echo ""

# -- confirmation prompt for broadcast --
if $BROADCAST; then
  read -r -p "You are about to broadcast transactions to Base Sepolia. Continue? [y/N] " confirm
  case "$confirm" in
    [yY][eE][sS]|[yY]) ;;
    *) echo "Aborted."; exit 0 ;;
  esac
fi

# Build forge script command
FORGE_CMD=(
  forge script
  script/DeployMainnet.s.sol:DeployMainnet
  --rpc-url "$BASE_SEPOLIA_RPC_URL"
  --private-key "$PRIVATE_KEY"
  --chain-id "$BASE_SEPOLIA_CHAIN_ID"
  -vvvv
)

if $BROADCAST; then
  FORGE_CMD+=(--broadcast)
fi

if $VERIFY; then
  if [[ -z "${BASESCAN_API_KEY:-}" ]]; then
    warn "BASESCAN_API_KEY is not set. Skipping verification."
  else
    FORGE_CMD+=(--verify --etherscan-api-key "$BASESCAN_API_KEY")
  fi
fi

info "Running deployment script..."
(cd "$CONTRACTS_DIR" && CONFIRM_MAINNET=true "${FORGE_CMD[@]}") || fail "Deployment script failed"

ok "Forge script completed"

# ============================================================================
# 3. POST-DEPLOYMENT
# ============================================================================
if $BROADCAST; then
  echo ""
  info "Extracting deployed addresses from broadcast..."

  BROADCAST_JSON="$CONTRACTS_DIR/broadcast/DeployMainnet.s.sol/$BASE_SEPOLIA_CHAIN_ID/run-latest.json"

  if [[ -f "$BROADCAST_JSON" ]]; then
    echo ""
    echo "============================================"
    echo "  DEPLOYED CONTRACTS"
    echo "============================================"

    # Extract contract creations from the broadcast JSON
    if command -v jq >/dev/null 2>&1; then
      jq -r '.transactions[] | select(.transactionType == "CREATE") | "  \(.contractName): \(.contractAddress)"' "$BROADCAST_JSON" 2>/dev/null || true
    else
      warn "jq not installed; cannot parse broadcast JSON automatically."
      info "Check broadcast output at: $BROADCAST_JSON"
    fi

    echo "============================================"
    echo ""

    # -- run verification script if it exists --
    VERIFY_SCRIPT="$CONTRACTS_DIR/script/VerifyDeployment.s.sol"
    if [[ -f "$VERIFY_SCRIPT" ]]; then
      info "Running VerifyDeployment script..."
      (cd "$CONTRACTS_DIR" && forge script script/VerifyDeployment.s.sol --rpc-url "$BASE_SEPOLIA_RPC_URL" -vvvv) \
        || warn "VerifyDeployment script returned errors"
    fi

    # -- next steps --
    echo ""
    echo "============================================"
    echo "  NEXT STEPS"
    echo "============================================"
    echo "  1. Update .env / config with deployed addresses"
    echo "  2. Run e2e tests:  uv run pytest tests/e2e/test_base_sepolia_e2e.py"
    echo "  3. Verify on Basescan if not already done (--verify flag)"
    echo "  4. Update packages/sardis-core config with new addresses"
    echo "  5. Test wallet creation and transaction flow on Base Sepolia"
    echo "============================================"
  else
    warn "Broadcast JSON not found at $BROADCAST_JSON"
    info "Check the broadcast/ directory for deployment artifacts."
  fi
else
  echo ""
  ok "Dry run complete. No transactions were broadcast."
  info "To deploy for real, run:"
  info "  ./scripts/deploy_testnet.sh --broadcast"
fi

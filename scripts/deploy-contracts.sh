#!/usr/bin/env bash
# Sardis Smart Contract Deployment Script
# Deploys SardisPolicyModule, SardisLedgerAnchor, RefundProtocol
#
# Usage:
#   ./scripts/deploy-contracts.sh testnet    # Base Sepolia (dry run + broadcast)
#   ./scripts/deploy-contracts.sh mainnet    # Base mainnet (dry run only, add --confirm for broadcast)
#   ./scripts/deploy-contracts.sh dryrun     # Simulate only (no broadcast)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTRACTS_DIR="$PROJECT_DIR/contracts"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1" >&2; }

# ===== Configuration =====

TARGET="${1:-dryrun}"
CONFIRM="${2:-}"

# USDC addresses per chain
declare -A USDC_ADDRESSES=(
    ["base"]="0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    ["base_sepolia"]="0x036CbD53842c5426634e7929541eC2318f3dCF7e"
    ["ethereum"]="0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48"
    ["polygon"]="0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359"
    ["arbitrum"]="0xaf88d065e77c8cC2239327C5EDb3A432268e5831"
)

# ===== Pre-flight checks =====

check_env() {
    local missing=0
    for var in "$@"; do
        if [[ -z "${!var:-}" ]]; then
            err "Missing required env var: $var"
            missing=1
        fi
    done
    return $missing
}

check_forge() {
    if ! command -v forge &>/dev/null; then
        err "forge not found. Install Foundry: https://book.getfoundry.sh/getting-started/installation"
        exit 1
    fi
    log "Foundry version: $(forge --version | head -1)"
}

# ===== Deploy functions =====

deploy_testnet() {
    log "Deploying to Base Sepolia (testnet)..."

    check_env PRIVATE_KEY SARDIS_ADDRESS || {
        echo ""
        echo "Required environment variables:"
        echo "  PRIVATE_KEY         - Deployer wallet private key (without 0x)"
        echo "  SARDIS_ADDRESS      - Sardis platform address"
        echo "  BASE_SEPOLIA_RPC_URL - (optional) Alchemy RPC URL, defaults to public"
        echo ""
        echo "Optional:"
        echo "  BASESCAN_API_KEY    - For contract verification on Basescan"
        exit 1
    }

    export USDC_ADDRESS="${USDC_ADDRESSES[base_sepolia]}"
    local RPC_URL="${BASE_SEPOLIA_RPC_URL:-https://sepolia.base.org}"
    local VERIFY_FLAGS=""
    if [[ -n "${BASESCAN_API_KEY:-}" ]]; then
        VERIFY_FLAGS="--verify --etherscan-api-key $BASESCAN_API_KEY"
    fi

    cd "$CONTRACTS_DIR"

    # Step 1: Build
    log "Building contracts..."
    forge build --force

    # Step 2: Dry run
    log "Running dry run (no broadcast)..."
    forge script script/DeploySafeModules.s.sol:DeploySafeModules \
        --rpc-url "$RPC_URL" \
        -vvvv

    echo ""
    log "Dry run successful! Broadcasting..."
    echo ""

    # Step 3: Broadcast
    forge script script/DeploySafeModules.s.sol:DeploySafeModules \
        --rpc-url "$RPC_URL" \
        --broadcast \
        $VERIFY_FLAGS \
        --gas-estimate-multiplier 120 \
        -vvvv

    echo ""
    log "Testnet deployment complete!"
    log ""
    log "Next steps:"
    log "  1. Copy deployed addresses from output above"
    log "  2. Set env vars:"
    log "     SARDIS_BASE_SEPOLIA_POLICY_MODULE_ADDRESS=0x..."
    log "     SARDIS_BASE_SEPOLIA_LEDGER_ANCHOR_ADDRESS=0x..."
    log "  3. Run smoke test: ./scripts/deploy-contracts.sh verify base_sepolia"
}

deploy_mainnet() {
    log "Deploying to Base mainnet..."

    check_env PRIVATE_KEY SARDIS_ADDRESS BASESCAN_API_KEY || {
        echo ""
        echo "Required environment variables:"
        echo "  PRIVATE_KEY         - Deployer wallet private key (without 0x)"
        echo "  SARDIS_ADDRESS      - Sardis platform address"
        echo "  BASESCAN_API_KEY    - For contract verification"
        echo "  BASE_RPC_URL        - Alchemy RPC URL (required for mainnet)"
        exit 1
    }

    check_env BASE_RPC_URL || {
        err "BASE_RPC_URL is required for mainnet deployment (use Alchemy)"
        exit 1
    }

    export USDC_ADDRESS="${USDC_ADDRESSES[base]}"

    cd "$CONTRACTS_DIR"

    # Step 1: Build
    log "Building contracts..."
    forge build --force

    # Step 2: Run tests
    log "Running tests..."
    forge test
    log "All tests passed!"

    # Step 3: Dry run
    log "Running dry run (no broadcast)..."
    forge script script/DeploySafeModules.s.sol:DeploySafeModules \
        --rpc-url "$BASE_RPC_URL" \
        -vvvv

    if [[ "$CONFIRM" != "--confirm" ]]; then
        echo ""
        warn "Dry run complete. To broadcast, run:"
        warn "  ./scripts/deploy-contracts.sh mainnet --confirm"
        warn ""
        warn "Make sure you have ~0.01 ETH on Base mainnet for gas."
        exit 0
    fi

    echo ""
    log "Broadcasting to Base mainnet..."
    echo ""

    # Step 4: Broadcast + verify
    forge script script/DeploySafeModules.s.sol:DeploySafeModules \
        --rpc-url "$BASE_RPC_URL" \
        --broadcast \
        --verify \
        --etherscan-api-key "$BASESCAN_API_KEY" \
        --gas-estimate-multiplier 120 \
        -vvvv

    echo ""
    log "MAINNET DEPLOYMENT COMPLETE!"
    log ""
    log "Deployed contracts:"
    log "  SardisPolicyModule  - check Basescan for address"
    log "  SardisLedgerAnchor  - check Basescan for address"
    log "  RefundProtocol      - check Basescan for address"
    log ""
    log "Pre-deployed infrastructure (already live):"
    log "  Safe ProxyFactory:  0xa6B71E26C5e0845f74c812102Ca7114b6a896AB2"
    log "  Safe Singleton:     0x41675C099F32341bf84BFc5382aF534df5C7461a"
    log "  Safe 4337 Module:   0x75cf11467937ce3F2f357CE24ffc3DBF8fD5c226"
    log "  Permit2:            0x000000000022D473030F116dDEE9F6B43aC78BA3"
    log "  EAS:                0x4200000000000000000000000000000000000021"
    log ""
    log "Next steps:"
    log "  1. Copy deployed addresses from broadcast output"
    log "  2. Set env vars in Vercel:"
    log "     SARDIS_BASE_POLICY_MODULE_ADDRESS=0x..."
    log "     SARDIS_BASE_LEDGER_ANCHOR_ADDRESS=0x..."
    log "  3. Verify on Basescan: https://basescan.org/address/0x..."
}

deploy_dryrun() {
    log "Running dry run (simulation only, no broadcast)..."

    check_env PRIVATE_KEY SARDIS_ADDRESS || {
        echo ""
        echo "Required: PRIVATE_KEY, SARDIS_ADDRESS"
        echo ""
        echo "Quick test with Anvil (local):"
        echo "  anvil &"
        echo "  PRIVATE_KEY=ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80 \\"
        echo "  SARDIS_ADDRESS=0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266 \\"
        echo "  ./scripts/deploy-contracts.sh dryrun"
        exit 1
    }

    export USDC_ADDRESS="${USDC_ADDRESSES[base_sepolia]}"

    cd "$CONTRACTS_DIR"

    log "Building contracts..."
    forge build --force

    log "Simulating deployment..."
    forge script script/DeploySafeModules.s.sol:DeploySafeModules \
        --rpc-url "${BASE_SEPOLIA_RPC_URL:-https://sepolia.base.org}" \
        -vvvv

    echo ""
    log "Dry run successful! All contracts compile and deploy correctly."
    log ""
    log "To deploy for real:"
    log "  Testnet: ./scripts/deploy-contracts.sh testnet"
    log "  Mainnet: ./scripts/deploy-contracts.sh mainnet"
}

# ===== Main =====

check_forge

case "$TARGET" in
    testnet|test|sepolia|base_sepolia)
        deploy_testnet
        ;;
    mainnet|main|base|production|prod)
        deploy_mainnet
        ;;
    dryrun|dry|simulate|sim)
        deploy_dryrun
        ;;
    *)
        echo "Usage: $0 {testnet|mainnet|dryrun}"
        echo ""
        echo "Commands:"
        echo "  testnet  - Deploy to Base Sepolia (auto-broadcast)"
        echo "  mainnet  - Deploy to Base mainnet (dry run, add --confirm to broadcast)"
        echo "  dryrun   - Simulate deployment only (no broadcast)"
        echo ""
        echo "Examples:"
        echo "  PRIVATE_KEY=xxx SARDIS_ADDRESS=0x... $0 testnet"
        echo "  PRIVATE_KEY=xxx SARDIS_ADDRESS=0x... BASE_RPC_URL=https://... $0 mainnet --confirm"
        exit 1
        ;;
esac

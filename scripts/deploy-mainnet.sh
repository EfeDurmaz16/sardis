#!/bin/bash
# =============================================================================
# Sardis Mainnet Deployment Script
# =============================================================================
#
# This script deploys Sardis smart contracts to mainnet.
#
# Prerequisites:
#   - Foundry installed (forge, cast)
#   - Environment variables set in .env
#   - Deployer wallet funded with ETH for gas
#
# Usage:
#   ./scripts/deploy-mainnet.sh [base|polygon|ethereum|arbitrum|optimism]
#
# Example:
#   ./scripts/deploy-mainnet.sh base
#
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Load environment variables
if [ -f .env ]; then
    source .env
else
    echo -e "${RED}Error: .env file not found${NC}"
    echo "Please copy .env.example to .env and fill in your values"
    exit 1
fi

# Get network from argument
NETWORK=${1:-base}

# Network configuration
case $NETWORK in
    base)
        RPC_URL=${BASE_RPC_URL:-"https://mainnet.base.org"}
        EXPLORER_API_KEY=${BASESCAN_API_KEY}
        CHAIN_ID=8453
        VERIFY_URL="https://api.basescan.org/api"
        ;;
    polygon)
        RPC_URL=${POLYGON_RPC_URL:-"https://polygon-rpc.com"}
        EXPLORER_API_KEY=${POLYGONSCAN_API_KEY}
        CHAIN_ID=137
        VERIFY_URL="https://api.polygonscan.com/api"
        ;;
    ethereum)
        RPC_URL=${ETHEREUM_RPC_URL:-"https://eth.llamarpc.com"}
        EXPLORER_API_KEY=${ETHERSCAN_API_KEY}
        CHAIN_ID=1
        VERIFY_URL="https://api.etherscan.io/api"
        ;;
    arbitrum)
        RPC_URL=${ARBITRUM_RPC_URL:-"https://arb1.arbitrum.io/rpc"}
        EXPLORER_API_KEY=${ARBISCAN_API_KEY}
        CHAIN_ID=42161
        VERIFY_URL="https://api.arbiscan.io/api"
        ;;
    optimism)
        RPC_URL=${OPTIMISM_RPC_URL:-"https://mainnet.optimism.io"}
        EXPLORER_API_KEY=${OPTIMISM_API_KEY}
        CHAIN_ID=10
        VERIFY_URL="https://api-optimistic.etherscan.io/api"
        ;;
    *)
        echo -e "${RED}Unknown network: $NETWORK${NC}"
        echo "Supported networks: base, polygon, ethereum, arbitrum, optimism"
        exit 1
        ;;
esac

echo "=============================================="
echo -e "${YELLOW}Sardis Mainnet Deployment${NC}"
echo "=============================================="
echo "Network: $NETWORK"
echo "Chain ID: $CHAIN_ID"
echo "RPC URL: $RPC_URL"
echo ""

# Safety checks
if [ -z "$PRIVATE_KEY" ]; then
    echo -e "${RED}Error: PRIVATE_KEY not set${NC}"
    exit 1
fi

if [ -z "$EXPLORER_API_KEY" ]; then
    echo -e "${YELLOW}Warning: Explorer API key not set, verification may fail${NC}"
fi

# Get deployer address
DEPLOYER=$(cast wallet address --private-key $PRIVATE_KEY)
echo "Deployer: $DEPLOYER"

# Check balance
BALANCE=$(cast balance $DEPLOYER --rpc-url $RPC_URL)
echo "Balance: $BALANCE wei"

if [ "$BALANCE" = "0" ]; then
    echo -e "${RED}Error: Deployer has no balance${NC}"
    exit 1
fi

echo ""
echo -e "${YELLOW}=== PRE-DEPLOYMENT CHECKLIST ===${NC}"
echo "1. [ ] Contracts have been audited"
echo "2. [ ] Tested on all testnets"
echo "3. [ ] Recovery address is secure"
echo "4. [ ] Monitoring is set up"
echo "5. [ ] Incident response plan ready"
echo ""

# Confirm deployment
read -p "Are you sure you want to deploy to $NETWORK mainnet? (yes/no): " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
    echo "Deployment cancelled"
    exit 0
fi

# Set confirmation flag
export CONFIRM_MAINNET=true

echo ""
echo -e "${GREEN}Starting deployment...${NC}"
echo ""

# Navigate to contracts directory
cd contracts

# Run deployment
forge script script/DeployMainnet.s.sol:DeployMainnet \
    --rpc-url $RPC_URL \
    --broadcast \
    --verify \
    --etherscan-api-key $EXPLORER_API_KEY \
    -vvvv

echo ""
echo -e "${GREEN}=============================================="
echo "Deployment complete!"
echo "==============================================${NC}"
echo ""
echo "Next steps:"
echo "1. Save the contract addresses from above"
echo "2. Update packages/sardis-chain/src/sardis_chain/config.py"
echo "3. Update .env with new addresses"
echo "4. Test with a small transaction"
echo ""

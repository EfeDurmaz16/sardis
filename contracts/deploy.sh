#!/bin/bash
#
# Sardis Smart Contract Deployment Script
#
# Usage:
#   ./deploy.sh [chain]
#
# Supported chains:
#   base_sepolia (default)
#   polygon_amoy
#   sepolia
#   arbitrum_sepolia
#   optimism_sepolia
#
# Prerequisites:
#   - Foundry installed (curl -L https://foundry.paradigm.xyz | bash && foundryup)
#   - PRIVATE_KEY environment variable set
#   - RPC URLs configured in foundry.toml or as env vars
#   - Testnet ETH in deployer wallet
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default to Base Sepolia
CHAIN=${1:-base_sepolia}

echo -e "${GREEN}=== Sardis Smart Contract Deployment ===${NC}"
echo -e "Chain: ${YELLOW}$CHAIN${NC}"
echo ""

# Check prerequisites
if ! command -v forge &> /dev/null; then
    echo -e "${RED}Error: Foundry (forge) not found${NC}"
    echo "Install with: curl -L https://foundry.paradigm.xyz | bash && foundryup"
    exit 1
fi

if [ -z "$PRIVATE_KEY" ]; then
    echo -e "${RED}Error: PRIVATE_KEY environment variable not set${NC}"
    echo "Export your deployer private key: export PRIVATE_KEY=0x..."
    exit 1
fi

# Map chain name to RPC URL env var
case $CHAIN in
    base_sepolia)
        RPC_VAR="BASE_SEPOLIA_RPC_URL"
        DEFAULT_RPC="https://sepolia.base.org"
        ;;
    polygon_amoy)
        RPC_VAR="POLYGON_AMOY_RPC_URL"
        DEFAULT_RPC="https://rpc-amoy.polygon.technology"
        ;;
    sepolia)
        RPC_VAR="SEPOLIA_RPC_URL"
        DEFAULT_RPC="https://rpc.sepolia.org"
        ;;
    arbitrum_sepolia)
        RPC_VAR="ARBITRUM_SEPOLIA_RPC_URL"
        DEFAULT_RPC="https://sepolia-rollup.arbitrum.io/rpc"
        ;;
    optimism_sepolia)
        RPC_VAR="OPTIMISM_SEPOLIA_RPC_URL"
        DEFAULT_RPC="https://sepolia.optimism.io"
        ;;
    *)
        echo -e "${RED}Error: Unknown chain '$CHAIN'${NC}"
        echo "Supported chains: base_sepolia, polygon_amoy, sepolia, arbitrum_sepolia, optimism_sepolia"
        exit 1
        ;;
esac

# Get RPC URL from env var or use default
RPC_URL="${!RPC_VAR:-$DEFAULT_RPC}"
echo "RPC URL: $RPC_URL"
echo ""

# Install dependencies if needed
if [ ! -d "lib/openzeppelin-contracts" ]; then
    echo -e "${YELLOW}Installing dependencies...${NC}"
    forge install OpenZeppelin/openzeppelin-contracts@v5.0.0 --no-commit
fi

# Build contracts
echo -e "${YELLOW}Building contracts...${NC}"
forge build

# Run tests
echo -e "${YELLOW}Running tests...${NC}"
forge test --no-match-test testFuzz -vvv || {
    echo -e "${RED}Tests failed! Fix tests before deploying.${NC}"
    exit 1
}

# Deploy
echo -e "${GREEN}Deploying to $CHAIN...${NC}"
echo ""

forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url $RPC_URL \
    --broadcast \
    -vvvv

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Next steps:"
echo "1. Copy the environment variables above to your .env file"
echo "2. Or update SARDIS_CONTRACTS in packages/sardis-chain/src/sardis_chain/executor.py"
echo "3. Verify contracts on block explorer (add --verify flag if API key set)"
echo ""

#!/bin/bash
# Sardis Smart Contract Deployment Script
# This script deploys the Sardis contracts to Base Sepolia testnet

set -e

echo "================================================"
echo "  Sardis Smart Contract Deployment"
echo "================================================"

# Check for Foundry
if ! command -v forge &> /dev/null; then
    echo "❌ Foundry not installed. Installing..."
    curl -L https://foundry.paradigm.xyz | bash
    source ~/.bashrc || source ~/.zshrc
    foundryup
fi

# Navigate to contracts directory
cd "$(dirname "$0")/../contracts"

# Check required environment variables
if [ -z "$PRIVATE_KEY" ]; then
    echo "❌ PRIVATE_KEY environment variable not set"
    echo ""
    echo "Please set your deployer wallet private key:"
    echo "  export PRIVATE_KEY='your_private_key_without_0x'"
    echo ""
    exit 1
fi

if [ -z "$BASE_SEPOLIA_RPC_URL" ]; then
    export BASE_SEPOLIA_RPC_URL="https://sepolia.base.org"
    echo "ℹ️  Using default RPC: $BASE_SEPOLIA_RPC_URL"
fi

# Install OpenZeppelin if not present
if [ ! -d "lib/openzeppelin-contracts" ]; then
    echo "📦 Installing OpenZeppelin..."
    forge install OpenZeppelin/openzeppelin-contracts --no-commit
fi

echo ""
echo "🔨 Building contracts..."
forge build

echo ""
echo "🚀 Deploying to Base Sepolia..."
echo ""

# Deploy using the testnet script
forge script script/Deploy.s.sol:DeployTestnet \
    --rpc-url base_sepolia \
    --broadcast \
    -vvv

echo ""
echo "✅ Deployment complete!"
echo ""
echo "Next steps:"
echo "1. Copy the contract addresses from the output above"
echo "2. Update packages/sardis-chain/src/sardis_chain/executor.py with the addresses"
echo "3. Set SARDIS_CHAIN_MODE=live to enable real transactions"
echo ""

# Optional: Verify on Basescan
if [ -n "$BASESCAN_API_KEY" ]; then
    echo "📝 Verifying contracts on Basescan..."
    # Verification would be done here
fi







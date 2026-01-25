# Sardis Smart Contract Deployment Guide

## Prerequisites

1. **Install Foundry**
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. **Get testnet ETH**
   - Base Sepolia: https://www.alchemy.com/faucets/base-sepolia
   - Polygon Amoy: https://faucet.polygon.technology/
   - Ethereum Sepolia: https://sepoliafaucet.com/

3. **Set environment variables**
   ```bash
   # Deployer private key (NEVER commit this!)
   export PRIVATE_KEY=0x...

   # RPC URLs (get from Alchemy, Infura, or similar)
   export BASE_SEPOLIA_RPC_URL=https://base-sepolia.g.alchemy.com/v2/YOUR_KEY
   export POLYGON_AMOY_RPC_URL=https://polygon-amoy.g.alchemy.com/v2/YOUR_KEY
   export SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY

   # Block explorer API keys (for contract verification)
   export BASESCAN_API_KEY=...
   export POLYGONSCAN_API_KEY=...
   export ETHERSCAN_API_KEY=...
   ```

## Deployment Steps

### 1. Install dependencies

```bash
cd contracts
forge install
```

### 2. Compile contracts

```bash
forge build
```

### 3. Run tests

```bash
forge test -vvv
```

### 4. Deploy to Base Sepolia (Primary Testnet)

```bash
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url base_sepolia \
    --broadcast \
    --verify
```

This will output:
- Contract addresses
- Environment variables to set
- Deployment JSON

### 5. Update executor.py

After deployment, update `/packages/sardis-chain/src/sardis_chain/executor.py` with the deployed addresses, or set environment variables:

```bash
# Option 1: Environment variables (recommended)
export SARDIS_BASE_SEPOLIA_WALLET_FACTORY_ADDRESS=0x...
export SARDIS_BASE_SEPOLIA_ESCROW_ADDRESS=0x...

# Option 2: Update executor.py directly
# Edit the SARDIS_CONTRACTS dictionary
```

### 6. Deploy to other testnets

```bash
# Polygon Amoy
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url polygon_amoy \
    --broadcast \
    --verify

# Ethereum Sepolia
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url sepolia \
    --broadcast \
    --verify

# Arbitrum Sepolia
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url arbitrum_sepolia \
    --broadcast \
    --verify

# Optimism Sepolia
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url optimism_sepolia \
    --broadcast \
    --verify
```

## Deployment Verification Checklist

After deployment, verify:

- [ ] Contract code is verified on block explorer
- [ ] Owner is set correctly
- [ ] Default limits are correct
- [ ] Recovery address is set
- [ ] Factory can create wallets
- [ ] Escrow can handle funds

## Gas Estimates

Approximate gas costs for deployment (at 1 gwei):

| Contract | Gas | Cost (ETH) |
|----------|-----|------------|
| SardisWalletFactory | ~2,500,000 | 0.0025 |
| SardisEscrow | ~1,500,000 | 0.0015 |
| **Total** | ~4,000,000 | **0.004** |

## Mainnet Deployment

⚠️ **IMPORTANT**: Before mainnet deployment:

1. Complete security audit
2. Review all parameters
3. Test thoroughly on testnet
4. Use multi-sig for ownership
5. Enable monitoring

Mainnet deployment uses the same script but with mainnet RPC URLs and higher limits.

## Troubleshooting

### "Insufficient funds"
- Ensure deployer wallet has enough ETH for gas

### "Contract verification failed"
- Check API key is correct
- Wait a few blocks before verifying
- Try manual verification on explorer

### "RPC error"
- Check RPC URL is correct
- Try a different RPC provider
- Check rate limits

## Quick Deploy Script

For convenience, use this bash script:

```bash
#!/bin/bash
set -e

CHAIN=${1:-base_sepolia}

echo "Deploying to $CHAIN..."

forge script script/DeployMultiChain.s.sol:DeployMultiChain \
    --rpc-url $CHAIN \
    --broadcast \
    --verify \
    -vvv

echo "Deployment complete!"
echo "Copy the environment variables above to your .env file"
```

Save as `deploy.sh` and run with: `./deploy.sh base_sepolia`

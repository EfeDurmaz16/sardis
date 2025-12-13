# Smart Contracts Deployment Guide

## Overview

Sardis smart contracts provide on-chain settlement and escrow functionality for agent payments.

### Contracts

| Contract | Description | Purpose |
|----------|-------------|---------|
| `SardisWalletFactory` | Creates and manages agent wallets | Per-agent spending limits and recovery |
| `SardisEscrow` | Trustless A2A payment escrow | Marketplace service payments |
| `SardisAgentWallet` | Individual agent wallet | ERC20 transfers with policy enforcement |

## Prerequisites

1. **Install Foundry**
   ```bash
   curl -L https://foundry.paradigm.xyz | bash
   foundryup
   ```

2. **Install OpenZeppelin Contracts**
   ```bash
   cd contracts
   forge install OpenZeppelin/openzeppelin-contracts --no-commit
   ```

3. **Set up environment variables**
   ```bash
   # Copy the example
   cp .env.example .env
   
   # Edit with your values
   nano .env
   ```

## Environment Variables

```bash
# Required for deployment
PRIVATE_KEY=your_deployer_private_key        # Without 0x prefix
RECOVERY_ADDRESS=0x...                        # Recovery wallet for emergencies

# RPC URLs
BASE_SEPOLIA_RPC_URL=https://sepolia.base.org
POLYGON_AMOY_RPC_URL=https://rpc-amoy.polygon.technology
SEPOLIA_RPC_URL=https://rpc.sepolia.org

# Block explorer API keys (for verification)
BASESCAN_API_KEY=your_basescan_api_key
POLYGONSCAN_API_KEY=your_polygonscan_api_key
ETHERSCAN_API_KEY=your_etherscan_api_key
```

## Deployment Steps

### 1. Compile Contracts

```bash
cd contracts
forge build
```

### 2. Run Tests

```bash
forge test -vv
```

### 3. Deploy to Base Sepolia (Testnet)

```bash
# Deploy with testnet configuration
forge script script/Deploy.s.sol:DeployTestnet \
    --rpc-url base_sepolia \
    --broadcast \
    --verify

# Or deploy with production configuration
forge script script/Deploy.s.sol:Deploy \
    --rpc-url base_sepolia \
    --broadcast \
    --verify
```

### 4. Verify Contracts (if not auto-verified)

```bash
forge verify-contract \
    <WALLET_FACTORY_ADDRESS> \
    SardisWalletFactory \
    --chain base-sepolia \
    --constructor-args $(cast abi-encode "constructor(uint256,uint256,address)" 100000000 1000000000 <RECOVERY_ADDRESS>)

forge verify-contract \
    <ESCROW_ADDRESS> \
    SardisEscrow \
    --chain base-sepolia \
    --constructor-args $(cast abi-encode "constructor(address,uint256,uint256,uint256)" <DEPLOYER_ADDRESS> 100 10000 7)
```

## Deployed Addresses

### Base Sepolia (Testnet)

| Contract | Address | Verified |
|----------|---------|----------|
| SardisWalletFactory | `TBD` | ⏳ |
| SardisEscrow | `TBD` | ⏳ |

### Polygon Amoy (Testnet)

| Contract | Address | Verified |
|----------|---------|----------|
| SardisWalletFactory | `TBD` | ⏳ |
| SardisEscrow | `TBD` | ⏳ |

### Mainnet (Production)

> ⚠️ Not yet deployed. Requires security audit first.

## Post-Deployment Configuration

### 1. Update API Configuration

Add deployed addresses to your `.env`:

```bash
SARDIS_WALLET_FACTORY=0x...
SARDIS_ESCROW=0x...
```

### 2. Update Chain Executor

The `ChainExecutor` will automatically use deployed addresses when configured:

```python
# In sardis-chain/src/sardis_chain/executor.py
CONTRACT_ADDRESSES = {
    "base_sepolia": {
        "wallet_factory": "0x...",
        "escrow": "0x...",
    },
}
```

### 3. Initialize Factory (First Time Only)

```bash
# Using cast (Foundry CLI)
cast send $SARDIS_WALLET_FACTORY \
    "initialize(address)" \
    $USDC_ADDRESS \
    --rpc-url base_sepolia \
    --private-key $PRIVATE_KEY
```

## Contract Interactions

### Create Agent Wallet

```bash
cast send $SARDIS_WALLET_FACTORY \
    "createWallet(string)" \
    "agent_001" \
    --rpc-url base_sepolia \
    --private-key $PRIVATE_KEY
```

### Create Escrow

```bash
cast send $SARDIS_ESCROW \
    "createEscrow(address,address,uint256,uint256,bytes32,string)" \
    $SELLER_ADDRESS \
    $USDC_ADDRESS \
    1000000 \
    $(date -d "+7 days" +%s) \
    0x0000000000000000000000000000000000000000000000000000000000000000 \
    "Test service" \
    --rpc-url base_sepolia \
    --private-key $PRIVATE_KEY
```

## Security Considerations

1. **Private Key Security**
   - Use hardware wallets for production
   - Never commit private keys
   - Use environment variables

2. **Recovery Address**
   - Should be a cold wallet or multisig
   - Required for emergency fund recovery

3. **Fee Settings**
   - Max 5% (500 basis points)
   - Review before mainnet deployment

4. **Upgrade Path**
   - Contracts are NOT upgradeable by design
   - New versions require redeployment
   - Consider proxy patterns for future upgrades

## Troubleshooting

### "insufficient funds for gas"
- Ensure deployer wallet has ETH for gas
- Base Sepolia faucet: https://faucet.quicknode.com/base/sepolia

### "verification failed"
- Check block explorer API key
- Wait for contract indexing (1-2 minutes)
- Try manual verification

### "nonce too low"
- Another transaction is pending
- Wait or increase nonce manually

## Gas Estimates

| Operation | Estimated Gas | Cost (at 0.1 gwei) |
|-----------|---------------|---------------------|
| Deploy WalletFactory | ~2,500,000 | ~0.00025 ETH |
| Deploy Escrow | ~3,000,000 | ~0.0003 ETH |
| Create Wallet | ~300,000 | ~0.00003 ETH |
| Create Escrow | ~200,000 | ~0.00002 ETH |
| Release Escrow | ~100,000 | ~0.00001 ETH |

## Links

- [Foundry Book](https://book.getfoundry.sh/)
- [Base Sepolia Explorer](https://sepolia.basescan.org/)
- [USDC on Base Sepolia](https://sepolia.basescan.org/address/0x036CbD53842c5426634e7929541eC2318f3dCF7e)






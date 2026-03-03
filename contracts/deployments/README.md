# Sardis Contract Deployments

This directory contains deployment records for Sardis smart contracts across all supported chains.

## Deployment Status

### Testnets

| Chain | Status | PolicyModule | LedgerAnchor |
|-------|--------|--------------|--------------|
| Base Sepolia | ⏳ Pending | - | - |
| Polygon Amoy | ⏳ Pending | - | - |
| Ethereum Sepolia | ⏳ Pending | - | - |
| Arbitrum Sepolia | ⏳ Pending | - | - |
| Optimism Sepolia | ⏳ Pending | - | - |

### Mainnets (Requires Audit)

| Chain | Status | PolicyModule | LedgerAnchor |
|-------|--------|--------------|--------------|
| Base | 🔒 Pending Audit | - | - |
| Polygon | 🔒 Pending Audit | - | - |
| Ethereum | 🔒 Pending Audit | - | - |
| Arbitrum | 🔒 Pending Audit | - | - |
| Optimism | 🔒 Pending Audit | - | - |

## Deployment Process

### External Policy Module Default

Sardis defaults to an external Safe policy module (Zodiac Roles) instead of deploying a custom `SardisPolicyModule`:

- `0x9646fDAD06d3e24444381f44362a3B0eB343D337`

Override per environment with:

```bash
export SARDIS_BASE_POLICY_MODULE_ADDRESS="0x..."
```

### Prerequisites

1. Install Foundry: `curl -L https://foundry.paradigm.xyz | bash && foundryup`
2. Set environment variables:
   ```bash
   export PRIVATE_KEY="your_deployer_private_key"
   export RECOVERY_ADDRESS="your_recovery_address"  # Optional, defaults to deployer
   ```

### Deploy to Testnet

```bash
cd contracts

# Base Sepolia (primary testnet)
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
  --rpc-url base_sepolia \
  --broadcast \
  --verify

# Polygon Amoy
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
  --rpc-url polygon_amoy \
  --broadcast \
  --verify

# Continue for other testnets...
```

### Deploy to Mainnet (After Audit)

```bash
# WARNING: Only deploy to mainnet after security audit

# Base Mainnet
forge script script/DeployMultiChain.s.sol:DeployMultiChain \
  --rpc-url base \
  --broadcast \
  --verify
```

## File Structure

```
deployments/
├── README.md           # This file
├── base_sepolia.json   # Base Sepolia deployment
├── polygon_amoy.json   # Polygon Amoy deployment
├── ethereum_sepolia.json
├── arbitrum_sepolia.json
├── optimism_sepolia.json
├── base.json           # Mainnet deployments (after audit)
├── polygon.json
├── ethereum.json
├── arbitrum.json
└── optimism.json
```

## Deployment JSON Format

Each deployment file contains:

```json
{
  "chain": "base_sepolia",
  "chainId": 84532,
  "deployer": "0x...",
  "contracts": {
    "policyModule": "0x...",
    "ledgerAnchor": "0x...",
    "refundProtocol": "0x..."
  },
  "blockNumber": 12345678,
  "timestamp": 1706140800
}
```

## After Deployment

1. Update contract addresses in `packages/sardis-chain/src/sardis_chain/executor.py`
2. Or set environment variables:
   ```bash
   export SARDIS_BASE_POLICY_MODULE_ADDRESS="0x..."
   export SARDIS_BASE_LEDGER_ANCHOR_ADDRESS="0x..."
   ```

3. Verify contracts on block explorers if not done during deployment:
   ```bash
   forge verify-contract <address> SardisWalletFactory --chain base-sepolia
   ```

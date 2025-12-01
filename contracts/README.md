# Sardis Smart Contracts

Solidity smart contracts for the Sardis AI Agent Payment Network.

## Contracts

### SardisAgentWallet.sol
Programmable wallet for AI agents with on-chain spending controls:
- Per-transaction and daily spending limits
- Merchant allowlist/denylist
- Pre-authorization holds (like credit cards)
- Multi-sig with Sardis as co-signer
- Emergency recovery mechanism

### SardisWalletFactory.sol
Factory contract for deploying agent wallets:
- Deploy new wallets with CREATE2 (deterministic addresses)
- Track all deployed wallets
- Configure default limits
- Wallet verification

### SardisEscrow.sol
Escrow for trustless agent-to-agent payments:
- Milestone-based payments
- Dispute resolution with arbiter
- Time-locked releases
- Automatic refunds on expiry

## Development Setup

### Prerequisites
- [Foundry](https://book.getfoundry.sh/getting-started/installation)
- Node.js 18+ (for additional tooling)

### Install Dependencies

```bash
cd contracts

# Install Foundry dependencies
forge install OpenZeppelin/openzeppelin-contracts

# Build contracts
forge build
```

### Run Tests

```bash
forge test
```

### Deploy to Testnet

1. Set environment variables:

```bash
export PRIVATE_KEY="your_deployer_private_key"
export BASE_SEPOLIA_RPC_URL="https://sepolia.base.org"
export BASESCAN_API_KEY="your_basescan_api_key"
```

2. Deploy to Base Sepolia:

```bash
forge script script/Deploy.s.sol:DeployTestnet \
    --rpc-url base_sepolia \
    --broadcast \
    --verify
```

3. Save the deployed addresses:

```bash
# Add to your .env file
SARDIS_WALLET_FACTORY=0x...
SARDIS_ESCROW=0x...
```

## Network Addresses

### Base Sepolia (Testnet)
| Contract | Address |
|----------|---------|
| WalletFactory | TBD |
| Escrow | TBD |
| USDC | 0x036CbD53842c5426634e7929541eC2318f3dCF7e |

### Polygon Amoy (Testnet)
| Contract | Address |
|----------|---------|
| WalletFactory | TBD |
| Escrow | TBD |
| USDC | 0x41E94Eb019C0762f9Bfcf9Fb1E58725BfB0e7582 |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Sardis Backend                          │
│  ┌─────────────────┐  ┌─────────────────┐                   │
│  │  Payment Service │  │ Contract Service │                 │
│  └────────┬────────┘  └────────┬────────┘                   │
│           │                    │                             │
│           ▼                    ▼                             │
└───────────┼────────────────────┼─────────────────────────────┘
            │                    │
            │    ┌───────────────┴───────────────┐
            │    │                               │
            ▼    ▼                               ▼
    ┌───────────────────┐             ┌───────────────────┐
    │  WalletFactory    │             │    Escrow         │
    │  (Deploy wallets) │             │ (A2A payments)    │
    └─────────┬─────────┘             └───────────────────┘
              │
              │ CREATE
              ▼
    ┌───────────────────┐
    │  AgentWallet      │
    │  ┌─────────────┐  │
    │  │ Limits      │  │
    │  │ Merchants   │  │
    │  │ Holds       │  │
    │  └─────────────┘  │
    └───────────────────┘
```

## Security

- All contracts use OpenZeppelin's battle-tested libraries
- ReentrancyGuard on all state-changing functions
- Pausable for emergency stops
- Multi-sig for high-value operations
- Audited limits and validation

## Gas Optimization

- CREATE2 for predictable wallet addresses
- Minimal storage operations
- Batch operations where possible
- Estimated costs:
  - Create wallet: ~200k gas
  - Payment: ~100k gas
  - Create hold: ~80k gas
  - Capture hold: ~70k gas

## License

MIT


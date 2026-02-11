# sardis-chain

[![PyPI version](https://badge.fury.io/py/sardis-chain.svg)](https://badge.fury.io/py/sardis-chain)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-grade multi-chain stablecoin executor for Sardis.

## Overview

`sardis-chain` provides the blockchain execution layer for stablecoin operations:

- **Multi-Chain Support**: Ethereum, Base, Polygon, Arbitrum, and more
- **MPC Custody**: Integration with Turnkey and Fireblocks
- **Transaction Execution**: Gas estimation, nonce management, confirmation tracking
- **Cross-Chain Routing**: CCIP and Wormhole integration
- **MEV Protection**: Flashbots and private mempool support
- **Deposit Monitoring**: Real-time deposit detection and processing

## Installation

```bash
pip install sardis-chain
```

### Development Installation

```bash
pip install sardis-chain[dev]
```

## Quick Start

```python
from sardis_chain import (
    ChainExecutor,
    WalletManager,
    NonceManager,
    ConfirmationTracker,
)

# Initialize the executor
executor = ChainExecutor(
    chain="base",
    rpc_url="https://mainnet.base.org",
    mpc_provider="turnkey",
)

# Execute a stablecoin transfer
result = await executor.transfer(
    from_wallet="0x...",
    to_address="0x...",
    token="USDC",
    amount=100_000000,  # $100 in 6 decimals
)

print(f"Transaction hash: {result.tx_hash}")
print(f"Confirmations: {result.confirmations}")
```

## Features

### Chain Execution

```python
from sardis_chain import ChainExecutor

executor = ChainExecutor(chain="ethereum")

# Transfer with automatic gas estimation
tx = await executor.transfer(
    from_wallet=wallet_id,
    to_address=recipient,
    token="USDC",
    amount=amount,
    priority="high",  # Adjusts gas price
)

# Wait for confirmation
confirmed = await executor.wait_for_confirmation(
    tx_hash=tx.tx_hash,
    confirmations=12,
)
```

### Nonce Management

```python
from sardis_chain import NonceManager

nonce_mgr = NonceManager(chain="base")

# Get next nonce with automatic tracking
async with nonce_mgr.acquire(wallet_address) as nonce:
    # Use nonce for transaction
    tx = build_transaction(nonce=nonce)
    await submit_transaction(tx)
# Nonce automatically released/committed on success
```

### Deposit Monitoring

```python
from sardis_chain import DepositMonitor

monitor = DepositMonitor(
    chain="base",
    tokens=["USDC", "USDT"],
    callback=handle_deposit,
)

# Start monitoring
await monitor.start()

async def handle_deposit(deposit):
    print(f"Received {deposit.amount} {deposit.token}")
    print(f"From: {deposit.from_address}")
    print(f"Block: {deposit.block_number}")
```

### MEV Protection

```python
from sardis_chain import ChainExecutor

executor = ChainExecutor(
    chain="ethereum",
    mev_protection=True,
    flashbots_relay="https://relay.flashbots.net",
)

# Transaction submitted via private mempool
tx = await executor.transfer(...)
```

## Supported Chains

| Chain    | Chain ID | Token Support |
|----------|----------|---------------|
| Ethereum | 1        | USDC, USDT, DAI |
| Base     | 8453     | USDC, USDbC |
| Polygon  | 137      | USDC, USDT |
| Arbitrum | 42161    | USDC, USDT |
| Optimism | 10       | USDC |

## Configuration

```python
from sardis_chain import ChainConfig

config = ChainConfig(
    chain="base",
    rpc_url="https://mainnet.base.org",
    fallback_rpcs=[
        "https://base.llamarpc.com",
        "https://base.blockpi.network/v1/rpc/public",
    ],
    confirmation_blocks=12,
    gas_price_multiplier=1.1,
    max_gas_price_gwei=100,
)
```

Or via environment variables:

```bash
SARDIS_CHAIN_RPC_URL=https://mainnet.base.org
SARDIS_CHAIN_CONFIRMATIONS=12
SARDIS_TURNKEY_API_KEY=your-api-key
SARDIS_TURNKEY_ORGANIZATION_ID=your-org-id
```

## Architecture

```
sardis-chain/
├── executor.py       # Transaction execution
├── wallet_manager.py # MPC wallet operations
├── nonce_manager.py  # Nonce tracking and recovery
├── deposit_monitor.py # Deposit detection
├── confirmation.py   # Confirmation tracking
├── mev_protection.py # MEV protection utilities
├── simulation.py     # Transaction simulation
└── rpc_client.py     # RPC connection management
```

## Requirements

- Python 3.11+
- web3 >= 6.0
- pydantic >= 2.6
- sardis-core >= 0.1.0
- httpx >= 0.25.0
- rlp >= 3.0.0
- cryptography >= 41.0.0

## Documentation

Full documentation is available at [docs.sardis.sh/chain](https://docs.sardis.sh/chain).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

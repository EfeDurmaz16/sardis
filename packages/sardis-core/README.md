# sardis-core

[![PyPI version](https://badge.fury.io/py/sardis-core.svg)](https://badge.fury.io/py/sardis-core)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Core AP2/TAP-aligned domain primitives for the Sardis stablecoin execution layer.

## Overview

`sardis-core` provides foundational components shared across all Sardis services:

- **Domain Models**: Wallets, transactions, holds, agents, mandates, and virtual cards
- **Configuration Management**: Deterministic config loading with validation
- **Security Utilities**: Ed25519/ECDSA key management, MPC connectors
- **Resilience Patterns**: Retry mechanisms, circuit breakers, rate limiting
- **Structured Logging**: Sensitive data masking, request tracing
- **Validation**: Comprehensive input validation for payments and blockchain data

## Installation

```bash
pip install sardis-core
```

### Optional Dependencies

```bash
# For natural language policy parsing (OpenAI-powered)
pip install sardis-core[nl-parser]

# For Redis-based spending tracking
pip install sardis-core[spending-tracker]

# Install all optional dependencies
pip install sardis-core[all]
```

## Quick Start

```python
from sardis_v2_core import (
    # Configuration
    load_config_from_env,
    validate_startup,

    # Domain models
    Wallet,
    Transaction,
    Hold,
    Agent,

    # Utilities
    retry,
    get_circuit_breaker,
    get_logger,
    validate_wallet_id,
)

# Load and validate configuration
config = load_config_from_env()
validate_startup(config)

# Get a structured logger
logger = get_logger("my_service")

# Use retry with exponential backoff
@retry(max_attempts=3, base_delay=1.0)
async def fetch_wallet(wallet_id: str) -> Wallet:
    validate_wallet_id(wallet_id)
    # ... fetch wallet logic
```

## Features

### Domain Models

```python
from sardis_v2_core import Wallet, Transaction, TransactionStatus

# Create a wallet
wallet = Wallet(
    wallet_id="wal_abc123",
    owner_id="user_xyz",
    chain="base",
    address="0x...",
)

# Track transactions
tx = Transaction(
    tx_id="tx_123",
    wallet_id=wallet.wallet_id,
    amount=100_00,  # $100.00 in cents
    status=TransactionStatus.PENDING,
)
```

### Resilience Patterns

```python
from sardis_v2_core import (
    retry_async,
    get_circuit_breaker,
    CircuitBreakerConfig,
)

# Circuit breaker for external services
cb = get_circuit_breaker(
    "mpc_service",
    config=CircuitBreakerConfig(
        failure_threshold=5,
        recovery_timeout=30.0,
    )
)

async with cb:
    result = await call_mpc_service()
```

### Structured Logging

```python
from sardis_v2_core import get_logger, mask_sensitive_data

logger = get_logger("payments")

# Automatically masks sensitive fields
logger.info("Processing payment", extra={
    "wallet_id": "wal_123",
    "amount": 1000,
    "card_number": "4111111111111111",  # Will be masked
})
```

## Architecture

`sardis-core` is designed as a pure domain library with no persistence or transport dependencies:

```
sardis-core/
├── exceptions.py      # Comprehensive error hierarchy
├── config.py          # Configuration models and loading
├── validators.py      # Input validation utilities
├── retry.py           # Retry mechanisms with backoff
├── circuit_breaker.py # Circuit breaker pattern
├── logging.py         # Structured logging with masking
├── wallets.py         # Wallet domain models
├── transactions.py    # Transaction models
├── holds.py           # Payment hold models
├── agents.py          # AI agent models
├── mandates.py        # AP2 mandate models
└── ...
```

## Requirements

- Python 3.11+
- pydantic >= 2.6
- pydantic-settings >= 2.0
- PyNaCl >= 1.5
- cryptography >= 41.0

## Documentation

Full documentation is available at [docs.sardis.io](https://docs.sardis.io).

## License

MIT License - see [LICENSE](LICENSE) for details.

## Contributing

Contributions are welcome! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

# Sardis CLI

Command-line interface for interacting with the Sardis payment platform.

## Installation

```bash
pip install sardis-cli
```

## Quick Start

```bash
# Configure API credentials
sardis login

# Check status
sardis status

# List agents
sardis agents list

# Execute a payment
sardis payments execute --from wallet_001 --to 0x1234... --amount 100 --token USDC
```

## Commands

### Authentication

```bash
# Login with API key
sardis login

# Check authentication status
sardis auth status

# Logout
sardis logout
```

### Agents

```bash
# List all agents
sardis agents list

# Get agent details
sardis agents get <agent_id>

# Create new agent
sardis agents create --name "My Agent"
```

### Wallets

```bash
# List wallets
sardis wallets list

# Get wallet balance
sardis wallets balance <wallet_id>

# Create wallet
sardis wallets create --agent <agent_id>
```

### Payments

```bash
# Execute payment
sardis payments execute \
    --from <wallet_id> \
    --to <destination> \
    --amount 100.00 \
    --token USDC \
    --chain base_sepolia

# Get payment status
sardis payments status <tx_id>
```

### Holds

```bash
# Create hold
sardis holds create \
    --wallet <wallet_id> \
    --amount 50.00 \
    --token USDC

# Capture hold
sardis holds capture <hold_id> --amount 45.00

# Void hold
sardis holds void <hold_id>

# List holds
sardis holds list --wallet <wallet_id>
```

### Chains

```bash
# List supported chains
sardis chains list

# Get gas estimate
sardis chains gas --chain base_sepolia --amount 100 --token USDC

# Route analysis
sardis chains route --from ethereum --to polygon --amount 1000
```

## Configuration

The CLI stores configuration in `~/.sardis/config.json`:

```json
{
  "api_base_url": "https://api.sardis.network",
  "api_key": "sk_...",
  "default_chain": "base_sepolia"
}
```

## Environment Variables

```bash
SARDIS_API_KEY=sk_...
SARDIS_API_BASE_URL=https://api.sardis.network
SARDIS_DEFAULT_CHAIN=base_sepolia
```

## Development

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run CLI
python -m sardis_cli --help
```


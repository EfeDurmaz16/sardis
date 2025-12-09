# Sardis Sandbox Environment

A fully isolated development environment for testing Sardis integrations without affecting production systems.

## Features

- **Mock Chain Executor**: Deterministic transaction simulation
- **Pre-seeded Data**: Test agents, wallets, and transactions
- **Isolated Database**: SQLite for local development
- **Demo API Key**: Pre-configured authentication

## Quick Start

```bash
# Navigate to project root
cd /path/to/sardis

# Start sandbox environment
./sandbox/start.sh

# OR manually:
export SARDIS_ENVIRONMENT=sandbox
export SARDIS_CHAIN_MODE=simulated
python -m scripts.seed_demo --sandbox
uvicorn sardis_api.main:create_app --factory --port 8001
```

## Configuration

The sandbox uses `.env.sandbox` with the following defaults:

```bash
SARDIS_ENVIRONMENT=sandbox
SARDIS_CHAIN_MODE=simulated
SARDIS_SECRET_KEY=sandbox-secret-key-not-for-production
DATABASE_URL=sqlite:///./sandbox/data/sardis.db
```

## Pre-seeded Data

### Demo Organization
- **ID**: `org_sandbox_demo`
- **Name**: Sandbox Demo Organization

### Demo Agents
| Agent ID | Name | Description |
|----------|------|-------------|
| `agent_alice` | Alice Agent | Shopping agent |
| `agent_bob` | Bob Agent | Merchant agent |
| `agent_charlie` | Charlie Agent | Service provider |

### Demo Wallets
| Wallet ID | Agent | Balance | Currency |
|-----------|-------|---------|----------|
| `wallet_alice` | agent_alice | 1,000.00 | USDC |
| `wallet_bob` | agent_bob | 500.00 | USDC |
| `wallet_charlie` | agent_charlie | 2,000.00 | USDC |

### Demo API Key
```
sk_sandbox_demo_1234567890abcdef
```

## Mock Chain Executor

The sandbox uses `SimulatedMPCSigner` which:

1. **Returns deterministic hashes**: Based on wallet ID and nonce
2. **Simulates gas estimation**: Returns realistic gas values
3. **Generates mock addresses**: Consistent per wallet
4. **Tracks transaction count**: For nonce management

### Mock Transaction Response

```json
{
  "tx_hash": "0x1234567890abcdef...",
  "chain": "base_sepolia",
  "block_number": 0,
  "status": "confirmed",
  "audit_anchor": "merkle::..."
}
```

## Testing with Sandbox

### Using the CLI
```bash
# Configure sandbox API
sardis login
# Enter: sk_sandbox_demo_1234567890abcdef
# URL: http://localhost:8001

# List agents
sardis agents list

# Execute payment
sardis payments execute \
    --from wallet_alice \
    --to 0x1234567890123456789012345678901234567890 \
    --amount 50 \
    --token USDC
```

### Using the Python SDK
```python
from sardis_sdk import SardisClient

client = SardisClient(
    api_key="sk_sandbox_demo_1234567890abcdef",
    base_url="http://localhost:8001",
)

# Execute payment
result = await client.payments.execute(
    from_wallet="wallet_alice",
    destination="0x1234...",
    amount=50.00,
    token="USDC",
)
```

### Using cURL
```bash
# Health check
curl http://localhost:8001/health

# List agents
curl -H "Authorization: Bearer sk_sandbox_demo_1234567890abcdef" \
     http://localhost:8001/api/v2/agents
```

## Directory Structure

```
sandbox/
├── README.md           # This file
├── .env.sandbox        # Environment configuration
├── seed_data.json      # Pre-seeded test data
├── start.sh            # Startup script
└── data/               # SQLite database (gitignored)
    └── sardis.db
```

## Resetting Sandbox

```bash
# Remove existing data
rm -rf sandbox/data/

# Re-seed
python -m scripts.seed_demo --sandbox
```

## Known Limitations

1. **No real blockchain transactions**: All chain interactions are simulated
2. **No external integrations**: KYC, sanctions screening use mock providers
3. **Webhooks not delivered**: Webhook events are logged but not sent
4. **No persistence between restarts**: Unless using persistent SQLite

## Switching from Sandbox to Production

```bash
# Unset sandbox environment
unset SARDIS_ENVIRONMENT

# Set production environment
export SARDIS_ENVIRONMENT=prod
export SARDIS_CHAIN_MODE=live
export DATABASE_URL=postgresql://...

# Get real API key from dashboard
sardis login
```


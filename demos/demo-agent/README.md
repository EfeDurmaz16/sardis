# Sardis Demo Agent

An interactive demonstration of AI agent payment capabilities with policy enforcement.

## Overview

This demo showcases how Sardis enables AI agents to make autonomous payments within defined policy constraints. The agent demonstrates:

- **Policy-Enforced Spending**: Payments are checked against spending policies before execution
- **Category Restrictions**: Only approved vendor categories are allowed
- **Amount Limits**: Per-transaction and daily limits are enforced
- **Merchant Blocking**: Specific merchant categories can be blocked
- **Audit Trail**: All transactions are logged for compliance

## Quick Start

### Prerequisites

- Python 3.10+
- Sardis API server running (optional - demo can run in simulation mode)

### Installation

```bash
# Navigate to demo directory
cd demos/demo-agent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running the Demo

**Simulation Mode** (no API server required):
```bash
python run_demo.py
```

**With Sardis API**:
```bash
# Set environment variables
export SARDIS_API_KEY="sk_test_your_key"
export SARDIS_API_URL="http://localhost:8000"

python run_demo.py
```

### Command Line Options

```bash
# Run all scenarios automatically
python run_demo.py --run-all

# Interactive mode
python run_demo.py --interactive

# Use existing wallet
python run_demo.py --wallet-id wallet_abc123

# Specify API endpoint
python run_demo.py --api-url http://localhost:8000 --api-key sk_test_xxx
```

## Demo Scenarios

The demo includes 8 pre-configured scenarios:

| Scenario | Vendor | Amount | Expected | Reason |
|----------|--------|--------|----------|--------|
| SaaS Subscription | OpenAI | $20 | APPROVED | Within limits |
| Cloud Infrastructure | Vercel | $50 | APPROVED | Allowed category |
| Development Tools | GitHub | $45 | APPROVED | DevTools allowed |
| Blocked Category | Amazon | $150 | BLOCKED | Retail not allowed |
| Over Limit | Anthropic | $600 | BLOCKED | Exceeds $500 limit |
| Infrastructure | AWS | $200 | APPROVED | Cloud allowed |
| Blocked Merchant | BetOnline | $50 | BLOCKED | Gambling blocked |
| Small Purchase | Figma | $15 | APPROVED | Within all limits |

## Default Policy

The demo uses this default spending policy:

```python
{
    "daily_limit": 500.00,
    "per_transaction_limit": 500.00,
    "monthly_limit": 5000.00,
    "allowed_categories": ["saas", "cloud", "devtools", "api"],
    "blocked_merchants": ["gambling", "adult", "crypto_exchange"],
    "require_purpose": True,
}
```

## Interactive Commands

When running in interactive mode:

| Command | Description |
|---------|-------------|
| `pay` | Make a custom payment |
| `balance` | Check wallet balance |
| `history` | View transaction history |
| `scenarios` | List demo scenarios |
| `policy` | View spending policy |
| `run` | Run all scenarios |
| `run N` | Run scenario N |
| `help` | Show available commands |
| `quit` | Exit demo |

## Example Session

```
$ python run_demo.py --interactive

  ____                  _ _
 / ___|  __ _ _ __ __| (_)___
 \___ \ / _` | '__/ _` | / __|
  ___) | (_| | | | (_| | \__ \
 |____/ \__,_|_|  \__,_|_|___/

AI Agent Payment Infrastructure Demo

┌─────────────────────────────────────────────────────┐
│                  Spending Policy                     │
├─────────────────────┬───────────────────────────────┤
│ Rule                │ Value                         │
├─────────────────────┼───────────────────────────────┤
│ Daily Limit         │ $500.00                       │
│ Per-Transaction     │ $500.00                       │
│ Allowed Categories  │ saas, cloud, devtools, api    │
└─────────────────────┴───────────────────────────────┘

sardis> run 1

Running: SaaS Subscription - OpenAI
Within daily limit, approved vendor category

╭───────────── Payment Result ─────────────╮
│ APPROVED                                  │
│                                           │
│ Vendor: OpenAI                            │
│ Amount: $20.00                            │
│ Purpose: API credits for GPT-4 usage      │
╰───────────────────────────────────────────╯

sardis> balance
Balance: $980.00

sardis> quit
```

## Architecture

```
┌─────────────────┐     ┌─────────────────┐
│   Demo Agent    │────▶│  Sardis SDK     │
│  (run_demo.py)  │     │  (LangChain)    │
└─────────────────┘     └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │   Sardis API    │
                        │  Policy Engine  │
                        └────────┬────────┘
                                 │
                                 ▼
                        ┌─────────────────┐
                        │  Blockchain     │
                        │  (Base Sepolia) │
                        └─────────────────┘
```

## Files

- `run_demo.py` - Interactive CLI runner
- `agent.py` - Sardis agent with LangChain tools
- `scenarios.py` - Pre-configured demo scenarios
- `requirements.txt` - Python dependencies

## Troubleshooting

**"sardis_sdk not installed"**
```bash
pip install sardis-sdk
# Or install from local packages:
pip install -e ../../packages/sardis-sdk-python
```

**"Connection refused"**
```bash
# Start the Sardis API server first:
cd ../../packages/sardis-api
uvicorn sardis_api.main:app --port 8000
```

**Running in simulation mode**
The demo will automatically fall back to simulation mode if the API is unavailable. All policy checks are performed locally.

## Next Steps

- Try modifying `scenarios.py` to add custom scenarios
- Adjust `DEFAULT_POLICY` to test different policy configurations
- Connect to a real Sardis API for on-chain transactions
- Integrate into your own LangChain agent

## License

MIT License - See repository root for details.

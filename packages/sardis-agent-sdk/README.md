# sardis-agent-sdk

Anthropic Claude Agent SDK integration for [Sardis](https://sardis.sh) payments.

## Installation

```bash
pip install sardis-agent-sdk
```

## Quick Start

```python
import anthropic
from sardis import SardisClient
from sardis_agent_sdk import SardisToolkit

sardis = SardisClient(api_key="sk_test_demo")
wallet = sardis.wallets.create(agent_id="my-agent", chain="base", currency="USDC")

toolkit = SardisToolkit(client=sardis, wallet_id=wallet.wallet_id)

# Automated agent loop
client = anthropic.Anthropic()
result = toolkit.run_agent_loop(
    client=client,
    model="claude-sonnet-4-5-20250929",
    system_prompt="You are a shopping assistant with a Sardis wallet.",
    user_message="Buy $20 of API credits from openai.com",
)
print(result["response"])
```

## Tools Provided

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute a policy-checked payment |
| `sardis_check_balance` | Check wallet balance and limits |
| `sardis_check_policy` | Dry-run a payment against policy |
| `sardis_set_policy` | Update spending policy (natural language) |
| `sardis_list_transactions` | View transaction history |
| `sardis_create_hold` | Create a temporary fund hold |

## Read-Only Mode

```python
toolkit = SardisToolkit(client=sardis, wallet_id=wallet_id, read_only=True)
# Only exposes balance, policy check, and transaction listing tools
```

## License

MIT

# sardis-composio

Sardis payment tools for [Composio](https://composio.dev)'s tool marketplace. Gives AI agents policy-controlled access to real payments via Sardis.

## Install

```bash
pip install sardis-composio
```

## Quick Start

### Python

```python
from sardis_composio import sardis_pay, sardis_check_balance, sardis_check_policy

# Check balance before paying
balance = sardis_check_balance(token="USDC")
print(f"Balance: ${balance['balance']} | Remaining limit: ${balance['remaining']}")

# Dry-run policy check
policy = sardis_check_policy(amount=49.99, merchant="vendor.example.com")
if policy["allowed"]:
    # Execute payment
    result = sardis_pay(amount=49.99, merchant="vendor.example.com", purpose="SaaS renewal")
    print(f"Payment {result['status']}: {result['tx_id']}")
```

### Environment Variables

```bash
SARDIS_API_KEY=sk_...         # Your Sardis API key
SARDIS_WALLET_ID=wallet_...   # Agent wallet ID
```

API keys and wallet IDs can also be passed directly to each function.

## Tools

| Function | Description |
|---|---|
| `sardis_pay(amount, merchant, purpose)` | Execute a policy-controlled payment |
| `sardis_check_balance(token)` | Get wallet balance and remaining spend limit |
| `sardis_check_policy(amount, merchant)` | Dry-run a payment against spending policy |

### `sardis_pay`

```python
result = sardis_pay(
    amount=49.99,
    merchant="vendor.example.com",
    purpose="SaaS subscription",  # optional, default: "Payment"
    api_key="sk_...",              # optional, falls back to env var
    wallet_id="wallet_...",        # optional, falls back to env var
)
# {"success": True, "status": "APPROVED", "tx_id": "tx_...", "amount": 49.99, ...}
```

### `sardis_check_balance`

```python
result = sardis_check_balance(token="USDC")
# {"success": True, "balance": 500.0, "remaining": 200.0, "token": "USDC"}
```

### `sardis_check_policy`

```python
result = sardis_check_policy(amount=100.0, merchant="shop.com")
# {"allowed": True, "reason": "Allowed: $100.0 to shop.com", "balance": 500.0, "remaining": 200.0}
```

## Composio Import (OpenAPI)

Import the Sardis API into Composio using the bundled OpenAPI spec:

1. Go to [app.composio.dev](https://app.composio.dev) → **Tools** → **Import OpenAPI**
2. Upload `openapi.yaml` from this package (find it at `packages/sardis-composio/openapi.yaml` or after install at `$(pip show sardis-composio | grep Location | awk '{print $2}')/sardis_composio/../../openapi.yaml`)
3. Set your `X-API-Key` authentication in Composio's credential manager
4. The following actions will be available:
   - `executePayment` — POST /v2/wallets/{wallet_id}/transfer
   - `getBalance` — GET /v2/wallets/{wallet_id}/balance
   - `checkPolicy` — POST /v2/payments/policy-check

### Using with an AI Framework

```python
# Example: LangChain + Composio
from composio_langchain import ComposioToolSet

toolset = ComposioToolSet(api_key="<composio-key>")
tools = toolset.get_tools(actions=["executePayment", "getBalance", "checkPolicy"])
```

```python
# Example: Direct SARDIS_TOOLS dict (no Composio required)
from sardis_composio import SARDIS_TOOLS

# Pass to any agent framework that accepts a dict of callables
agent_tools = SARDIS_TOOLS
```

## Development

```bash
uv sync
uv run pytest tests/
```

## Links

- [Sardis Docs](https://sardis.sh/docs)
- [Composio Docs](https://docs.composio.dev)
- [API Reference](https://api.sardis.sh/v2/docs)

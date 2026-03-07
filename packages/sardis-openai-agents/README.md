# sardis-openai-agents

Sardis payment tools for the [OpenAI Agents SDK](https://github.com/openai/openai-agents-python). Gives your agents policy-controlled spending via non-custodial MPC wallets.

## Install

```bash
# Core only (plain functions)
pip install sardis-openai-agents

# With OpenAI Agents SDK integration (@function_tool decorated)
pip install 'sardis-openai-agents[agents]'
```

## Quickstart

```python
from agents import Agent, Runner
from sardis_openai_agents import get_sardis_tools

agent = Agent(
    name="ProcurementAgent",
    instructions="You are a procurement agent. Check policy before paying.",
    tools=get_sardis_tools(),
)
```

Set env vars:

```bash
export SARDIS_API_KEY=sk_...
export SARDIS_WALLET_ID=wid_...
```

Or configure programmatically:

```python
from sardis_openai_agents import configure
configure(api_key="sk_...", wallet_id="wid_...")
```

## Tools

| Tool | Description |
|------|-------------|
| `sardis_pay(amount, merchant, purpose)` | Execute a payment; blocked if policy denies |
| `sardis_check_balance(token)` | Check wallet balance and remaining spend limit |
| `sardis_check_policy(amount, merchant)` | Dry-run policy check without executing |

## Example

See `examples/payment_agent.py` for an interactive agent demo.

## How It Works

Every payment is validated against the wallet's spending policy before execution. If a transaction would exceed daily limits or violate policy rules, it is blocked and the agent receives a clear explanation — no funds move.

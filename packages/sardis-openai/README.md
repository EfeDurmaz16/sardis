# sardis-openai

> **DEPRECATED — use [`sardis-openai-agents`](https://pypi.org/project/sardis-openai-agents/) instead.**
>
> This package targets the OpenAI **Chat Completions / Assistants** function-calling
> shape. It has been superseded by `sardis-openai-agents`, which targets the
> modern **OpenAI Agents SDK** and has ~10x more installs. OpenAI itself is
> deprecating the Assistants API in favor of the Responses / Agents API.
>
> `sardis-openai` will be **yanked from PyPI after a 30-day deprecation window**.
> A `DeprecationWarning` is emitted on import. Existing installs keep working
> for now — migrate at your earliest convenience.

## Migration

**Before** (`sardis-openai`, Chat Completions function calling):

```python
from openai import OpenAI
from sardis_openai import get_sardis_tools, SardisToolHandler

client = OpenAI()
handler = SardisToolHandler(api_key="...")
tools = get_sardis_tools()
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Pay $25 to OpenAI"}],
    tools=tools,
)
for tool_call in response.choices[0].message.tool_calls:
    result = await handler.handle(tool_call)
```

**After** (`sardis-openai-agents`, OpenAI Agents SDK):

```python
from agents import Agent, Runner
from sardis import SardisClient
from sardis_openai_agents import SardisAgentToolkit

sardis = SardisClient(api_key="...")
wallet = sardis.wallets.create(agent_id="my-agent", chain="base", currency="USDC")
toolkit = SardisAgentToolkit(client=sardis, wallet_id=wallet.wallet_id)

agent = Agent(name="Payer", instructions="You can pay.", tools=toolkit.tools())
result = await Runner.run(agent, "Pay $25 to OpenAI")
```

See [`sardis-openai-agents`](../sardis-openai-agents/README.md) for full docs.

OpenAI function calling tools for Sardis - Payment OS for AI Agents.

## Installation (legacy)

```bash
pip install sardis-openai
```

## Quick Start

```python
from openai import OpenAI
from sardis_openai import get_sardis_tools, SardisToolHandler

client = OpenAI()
handler = SardisToolHandler(api_key="sk_sardis_...")

# Get Sardis tool definitions
tools = get_sardis_tools()

# Use with Chat Completions
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Pay $25 to OpenAI for API credits"}],
    tools=tools,
)

# Handle tool calls
for tool_call in response.choices[0].message.tool_calls:
    result = await handler.handle(tool_call)
    print(result)
```

## Available Tools

| Tool | Description |
|------|-------------|
| `sardis_pay` | Execute payment with policy enforcement |
| `sardis_check_balance` | Check wallet balance and limits |
| `sardis_check_policy` | Dry-run policy validation |
| `sardis_issue_card` | Issue virtual card for agent |
| `sardis_get_spending_summary` | Get spending analytics |

All tools use **strict mode** to prevent hallucination.

## Links

- [Sardis Documentation](https://sardis.sh/docs)
- [OpenAI Function Calling Guide](https://platform.openai.com/docs/guides/function-calling)

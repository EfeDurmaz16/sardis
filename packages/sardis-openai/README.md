# sardis-openai

OpenAI function calling tools for Sardis - Payment OS for AI Agents.

## Installation

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

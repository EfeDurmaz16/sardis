# sardis-claude

Anthropic Claude integration for [Sardis](https://sardis.sh) payments — give
Claude agents real, policy-checked spending power.

This package is a **thin alias** of [`sardis-agent-sdk`](https://pypi.org/project/sardis-agent-sdk/).
It exists to provide a clearer install name that does not collide with the
main `sardis` SDK. All symbols are re-exported from `sardis_agent_sdk`.

In Sardis v2.0 the canonical home for this integration will be
`sardis.integrations.anthropic`; this package will continue to work as an alias.

## Installation

```bash
pip install sardis-claude
```

## Quick Start

```python
import anthropic
from sardis import SardisClient
from sardis_claude import SardisToolkit

sardis = SardisClient(api_key="...your Sardis API key...")
wallet = sardis.wallets.create(agent_id="my-agent", chain="base", currency="USDC")

toolkit = SardisToolkit(client=sardis, wallet_id=wallet.wallet_id)

client = anthropic.Anthropic()
result = toolkit.run_agent_loop(
    client=client,
    model="claude-sonnet-4-5-20250929",
    system_prompt="You are a shopping assistant with a Sardis wallet.",
    user_message="Buy $20 of API credits from openai.com",
)
print(result["response"])
```

For full documentation, tool reference, and advanced usage, see the
[`sardis-agent-sdk` README](../sardis-agent-sdk/README.md) and
[sardis.sh/docs](https://sardis.sh/docs).

## License

MIT

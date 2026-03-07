# sardis-browser-use

Sardis payment tools for [Browser Use](https://github.com/browser-use/browser-use) — enable browser automation agents to make policy-controlled USDC payments with built-in spending limits and audit trails.

## Install

```bash
pip install sardis-browser-use
```

## Quick Start

**Step 1:** Create a Sardis wallet with a spending policy.

**Step 2:** Register Sardis actions on your Browser Use controller.

**Step 3:** Run your agent — it can now check balances, verify policies, and pay.

```python
import asyncio, os
from browser_use import Agent, Controller
from sardis import SardisClient
from sardis_browser_use import register_sardis_actions

controller = Controller()

# Simulation mode — no API key required
client = SardisClient()
wallet = client.wallets.create(name="shopping-agent", policy="Max $100/day")
os.environ["SARDIS_WALLET_ID"] = wallet.id

register_sardis_actions(controller)

async def main():
    agent = Agent(
        task="Find the cheapest USB-C cable on Amazon and buy it if under $15",
        controller=controller,
    )
    await agent.run()

asyncio.run(main())
```

This gives your agent three actions:
- `sardis_pay(amount, merchant, purpose)` — execute a payment
- `sardis_balance(token)` — check current wallet balance
- `sardis_check_policy(amount, merchant)` — verify a purchase before committing

## Docs

[sardis.sh/docs/integrations/browser-use](https://sardis.sh/docs/integrations/browser-use)

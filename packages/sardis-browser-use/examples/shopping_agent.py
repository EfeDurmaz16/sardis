"""Example: Browser Use agent that can shop online with Sardis payments."""
import asyncio
import os

from browser_use import Agent, Controller
from sardis_browser_use import register_sardis_actions

from sardis import SardisClient

# Set up controller with Sardis payment actions
controller = Controller()

# Create a Sardis client in simulation mode (no API key needed)
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

if __name__ == "__main__":
    asyncio.run(main())

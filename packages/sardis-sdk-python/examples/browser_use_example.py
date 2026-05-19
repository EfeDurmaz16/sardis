"""Sardis + Browser Use — AI Agent Shopping Example

Demonstrates how to give a Browser Use agent a Sardis wallet for online purchases.
Requires: pip install sardis-browser-use browser-use
"""
import asyncio
import os

from sardis_sdk import AsyncSardisClient


async def main():
    api_key = os.environ.get("SARDIS_API_KEY")
    wallet_id = os.environ.get("SARDIS_WALLET_ID")
    if not api_key or not wallet_id:
        print("Set SARDIS_API_KEY and SARDIS_WALLET_ID environment variables.")
        print("Configure a sandbox key with your Sardis API deployment: https://sardis.sh/docs/authentication")
        return

    # Initialize Sardis client
    async with AsyncSardisClient(api_key=api_key) as client:
        # Check balance before starting
        balance = await client.wallets.get_balance(wallet_id)
        print(f"Wallet balance: {balance.balance} {balance.currency}")

        # In production, integrate with Browser Use by importing Controller
        # from browser_use and register_sardis_actions from sardis_browser_use.
        # Then register actions with the controller, client, wallet_id,
        # and allowed_origins. The agent can then use sardis_pay,
        # sardis_balance, sardis_check_policy, and select_best_card actions.

        print("Browser Use integration ready!")
        print("See sardis-browser-use package for full integration.")


if __name__ == "__main__":
    asyncio.run(main())

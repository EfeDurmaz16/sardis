"""Sardis Python SDK — Quickstart Example

Demonstrates: create agent → set spending policy → make payment → check balance.
"""
import asyncio
import os

from sardis_sdk import AsyncSardisClient


async def main():
    api_key = os.environ.get("SARDIS_API_KEY")
    if not api_key:
        print("Set SARDIS_API_KEY environment variable first.")
        print("Get your key at: https://dashboard.sardis.sh/api-keys")
        return

    async with AsyncSardisClient(api_key=api_key) as client:
        # 1. Create an AI agent
        agent = await client.agents.create(name="My First Agent")
        print(f"Agent created: {agent.agent_id}")

        # 2. Create a wallet for the agent
        wallet = await client.wallets.create(
            agent_id=agent.agent_id,
            chain="base",
        )
        print(f"Wallet created: {wallet.wallet_id} ({wallet.address})")

        # 3. Set a spending policy (natural language)
        policy = await client.policies.parse(
            text="Max $100 per transaction, $500 per day, no gambling"
        )
        await client.policies.apply(
            wallet_id=wallet.wallet_id,
            policy=policy,
        )
        print(f"Policy applied: {policy.summary}")

        # 4. Make a test payment
        payment = await client.payments.send(
            wallet_id=wallet.wallet_id,
            to="merchant_demo",
            amount="25.00",
            purpose="API usage - OpenAI",
        )
        print(f"Payment: {payment.status} (tx: {payment.tx_id})")

        # 5. Check balance
        balance = await client.wallets.get_balance(wallet.wallet_id)
        print(f"Balance: {balance.balance} {balance.currency}")


if __name__ == "__main__":
    asyncio.run(main())

"""Runtime contract tests for root `sardis.SardisClient` quickstart surface."""

from __future__ import annotations

from decimal import Decimal

from sardis import SardisClient


def test_root_client_quickstart_surface_runtime() -> None:
    client = SardisClient(api_key="sk_demo")

    agent = client.agents.create(name="demo-agent", description="runtime contract")
    wallet = client.wallets.create(
        agent_id=agent.agent_id,
        chain="base_sepolia",
        currency="USDC",
        limit_per_tx=Decimal("100.00"),
        limit_total=Decimal("500.00"),
    )

    tx = client.wallets.transfer(
        wallet.wallet_id,
        destination="openai.com",
        amount=Decimal("25.00"),
        token="USDC",
        chain="base_sepolia",
        domain="openai.com",
    )

    assert hasattr(client, "agents")
    assert hasattr(client, "wallets")
    assert hasattr(client, "groups")
    assert tx.token == "USDC"
    assert tx.chain == "base_sepolia"
    assert tx.tx_hash

    balance = client.wallets.get_balance(wallet.wallet_id, chain="base_sepolia", token="USDC")
    assert balance.wallet_id == wallet.wallet_id
    assert balance["token"] == "USDC"



def test_root_client_group_and_ledger_example_surface() -> None:
    client = SardisClient(api_key="sk_demo")

    group = client.groups.create(
        name="engineering-procurement",
        budget={
            "per_transaction": "200.00",
            "daily": "1000.00",
            "monthly": "30000.00",
        },
        merchant_policy={"blocked_categories": ["gambling"]},
    )
    agent = client.agents.create(name="purchaser-agent")
    wallet = client.wallets.create(agent_id=agent.agent_id, currency="USDC")
    client.groups.add_agent(group.group_id, agent.agent_id)

    client.wallets.transfer(
        wallet.wallet_id,
        destination="notion.so",
        amount=Decimal("10.00"),
        token="USDC",
        chain="base_sepolia",
        domain="crewai-finance.local",
        memo="tool purchase",
    )

    spending = client.groups.get_spending(group.group_id)
    entries = client.ledger.list_entries(wallet_id=wallet.wallet_id, limit=10)

    assert "budget" in spending
    assert "per_transaction" in spending["budget"]
    assert entries
    assert entries[0].created_at
    assert entries[0].currency == "USDC"



def test_root_client_legacy_wallet_create_still_works() -> None:
    client = SardisClient(api_key="sk_demo")

    wallet = client.wallets.create(
        name="legacy-agent-wallet",
        chain="base",
        token="USDC",
        policy="Max $100/day",
    )

    assert wallet.name == "legacy-agent-wallet"
    assert wallet.chain == "base"
    assert wallet.token == "USDC"

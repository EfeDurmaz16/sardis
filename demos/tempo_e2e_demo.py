"""Sardis E2E Demo — Tempo Mainnet Flow

Complete runnable script that exercises the full Sardis payment flow
on the Tempo network:

1. Sign up / Login → get JWT
2. Create wallet on Tempo
3. Get deposit address (for manual funding)
4. Get on-ramp URL (Tempo wallet fiat funding)
5. Create spending mandate ($100/day, cloud APIs only)
6. Create agent
7. Create MPP session
8. Agent makes MPP payment via Sardis
9. Check balance & audit trail
10. Close MPP session

Usage:
    uv run python demos/tempo_e2e_demo.py [--base-url URL] [--email EMAIL] [--password PASS]

Requirements:
    pip install httpx rich
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from decimal import Decimal

import httpx

# Optional: rich for pretty output
try:
    from rich.console import Console
    from rich.table import Table
    console = Console()
    def pprint(title: str, data: dict | list | str) -> None:
        console.print(f"\n[bold cyan]{'─' * 60}[/]")
        console.print(f"[bold green]✓ {title}[/]")
        if isinstance(data, (dict, list)):
            console.print_json(json.dumps(data, indent=2, default=str))
        else:
            console.print(str(data))
except ImportError:
    console = None  # type: ignore[assignment]
    def pprint(title: str, data: dict | list | str) -> None:
        print(f"\n{'─' * 60}")
        print(f"✓ {title}")
        if isinstance(data, (dict, list)):
            print(json.dumps(data, indent=2, default=str))
        else:
            print(str(data))


DEFAULT_BASE_URL = "http://localhost:8000"


async def login(client: httpx.AsyncClient, email: str, password: str) -> str:
    """Step 1: Login and get JWT token."""
    resp = await client.post("/api/v2/auth/login", json={
        "email": email,
        "password": password,
    })
    if resp.status_code == 401:
        # Try signup first
        print("  → User not found, creating account...")
        signup_resp = await client.post("/api/v2/auth/signup", json={
            "email": email,
            "password": password,
            "organization_name": "Sardis Demo",
        })
        if signup_resp.status_code not in (200, 201):
            raise RuntimeError(f"Signup failed: {signup_resp.status_code} {signup_resp.text}")
        data = signup_resp.json()
        pprint("Account Created", {"email": email, "org": data.get("organization_id")})
        # Login with new account
        resp = await client.post("/api/v2/auth/login", json={
            "email": email,
            "password": password,
        })

    resp.raise_for_status()
    data = resp.json()
    token = data.get("access_token") or data.get("token")
    if not token:
        raise RuntimeError(f"No token in login response: {data}")
    return token


async def create_wallet(client: httpx.AsyncClient, chain: str = "tempo") -> dict:
    """Step 2: Create wallet on Tempo."""
    resp = await client.post("/api/v2/wallets", json={
        "chain": chain,
        "label": f"demo-{chain}-wallet",
    })
    resp.raise_for_status()
    return resp.json()


async def get_deposit_address(client: httpx.AsyncClient, chain: str = "tempo") -> dict:
    """Step 3: Get deposit address for manual funding."""
    resp = await client.get("/api/v2/ramp/deposit-address", params={"chain": chain})
    resp.raise_for_status()
    return resp.json()


async def get_onramp_url(client: httpx.AsyncClient, chain: str = "tempo", amount: float | None = None) -> dict:
    """Step 4: Get fiat on-ramp URL."""
    params: dict = {"chain": chain}
    if amount:
        params["amount_usd"] = str(amount)
    resp = await client.get("/api/v2/ramp/onramp-url", params=params)
    resp.raise_for_status()
    return resp.json()


async def create_mandate(client: httpx.AsyncClient, mandate: dict) -> dict:
    """Step 5: Create spending mandate."""
    resp = await client.post("/api/v2/spending-mandates", json=mandate)
    resp.raise_for_status()
    return resp.json()


async def create_agent(client: httpx.AsyncClient, agent: dict) -> dict:
    """Step 6: Create agent."""
    resp = await client.post("/api/v2/agents", json=agent)
    resp.raise_for_status()
    return resp.json()


async def create_mpp_session(client: httpx.AsyncClient, session: dict) -> dict:
    """Step 7: Create MPP payment session."""
    resp = await client.post("/api/v2/mpp/sessions", json=session)
    resp.raise_for_status()
    return resp.json()


async def execute_mpp_payment(client: httpx.AsyncClient, session_id: str, payment: dict) -> dict:
    """Step 8: Execute payment within MPP session."""
    resp = await client.post(f"/api/v2/mpp/sessions/{session_id}/execute", json=payment)
    resp.raise_for_status()
    return resp.json()


async def get_ledger_entries(client: httpx.AsyncClient, limit: int = 10) -> list:
    """Step 9: Get audit trail."""
    resp = await client.get("/api/v2/ledger/entries", params={"limit": limit})
    resp.raise_for_status()
    data = resp.json()
    return data.get("entries", data) if isinstance(data, dict) else data


async def close_mpp_session(client: httpx.AsyncClient, session_id: str) -> dict:
    """Step 10: Close MPP session."""
    resp = await client.post(f"/api/v2/mpp/sessions/{session_id}/close")
    resp.raise_for_status()
    return resp.json()


async def main(base_url: str, email: str, password: str) -> None:
    print(f"""
╔══════════════════════════════════════════════════════════╗
║        Sardis E2E Demo — Tempo Mainnet Flow             ║
║                                                          ║
║  signup → wallet → fund → mandate → agent → pay → audit ║
╚══════════════════════════════════════════════════════════╝

API: {base_url}
""")

    async with httpx.AsyncClient(
        base_url=base_url,
        timeout=30.0,
    ) as client:
        # ── Step 1: Login ──
        print("Step 1: Authenticating...")
        token = await login(client, email, password)
        client.headers["Authorization"] = f"Bearer {token}"
        pprint("Authenticated", {"email": email, "token": token[:20] + "..."})

        # ── Step 2: Create Wallet ──
        print("\nStep 2: Creating wallet on Tempo...")
        wallet = await create_wallet(client, chain="tempo")
        wallet_id = wallet.get("wallet_id") or wallet.get("id")
        wallet_address = wallet.get("address") or wallet.get("addresses", {}).get("tempo", "")
        pprint("Wallet Created", {
            "wallet_id": wallet_id,
            "address": wallet_address,
            "chain": "tempo",
        })

        # ── Step 3: Get Deposit Address ──
        print("\nStep 3: Getting deposit address...")
        deposit = await get_deposit_address(client, chain="tempo")
        pprint("Deposit Address", deposit)

        # ── Step 4: Get On-Ramp URL ──
        print("\nStep 4: Getting fiat on-ramp URL...")
        onramp = await get_onramp_url(client, chain="tempo", amount=100)
        pprint("On-Ramp URL", onramp)

        # ── Manual Funding Step ──
        print("\n" + "=" * 60)
        print("  MANUAL STEP: Fund the wallet")
        print(f"  Send pathUSD or USDC.e to: {deposit.get('address', wallet_address)}")
        print(f"  Or use fiat on-ramp: {onramp.get('url', 'N/A')}")
        print("=" * 60)

        proceed = input("\nPress Enter to continue (or 'q' to quit): ")
        if proceed.strip().lower() == "q":
            print("Demo cancelled.")
            return

        # ── Step 5: Create Spending Mandate ──
        print("\nStep 5: Creating spending mandate...")
        mandate = await create_mandate(client, {
            "purpose": "Cloud infrastructure and API subscriptions",
            "amount_per_tx": 50,
            "amount_daily": 100,
            "allowed_merchants": ["openai.com", "anthropic.com", "aws.amazon.com"],
            "chain": "tempo",
        })
        mandate_id = mandate.get("mandate_id") or mandate.get("id")
        pprint("Spending Mandate Created", {
            "mandate_id": mandate_id,
            "daily_limit": "$100",
            "per_tx_limit": "$50",
            "merchants": ["openai.com", "anthropic.com", "aws.amazon.com"],
        })

        # ── Step 6: Create Agent ──
        print("\nStep 6: Creating AI agent...")
        agent = await create_agent(client, {
            "name": "procurement-agent",
            "description": "AI agent that purchases API credits and cloud services",
        })
        agent_id = agent.get("agent_id") or agent.get("id")
        pprint("Agent Created", {
            "agent_id": agent_id,
            "name": "procurement-agent",
        })

        # ── Step 7: Create MPP Session ──
        print("\nStep 7: Creating MPP payment session...")
        session = await create_mpp_session(client, {
            "spending_limit": 100,
            "method": "tempo",
            "chain": "tempo",
            "currency": "USDC",
            "mandate_id": mandate_id,
            "wallet_id": wallet_id,
            "agent_id": agent_id,
        })
        session_id = session.get("session_id")
        pprint("MPP Session Created", {
            "session_id": session_id,
            "spending_limit": session.get("spending_limit"),
            "status": session.get("status"),
            "expires_at": session.get("expires_at"),
        })

        # ── Step 8: Execute Payments ──
        print("\nStep 8: Executing MPP payments...")

        # Payment 1: OpenAI API credits
        pay1 = await execute_mpp_payment(client, session_id, {
            "amount": 10.00,
            "merchant": "openai.com",
            "memo": "GPT-4 API credits",
        })
        pprint("Payment 1 — OpenAI", {
            "payment_id": pay1.get("payment_id"),
            "amount": pay1.get("amount"),
            "merchant": pay1.get("merchant"),
            "status": pay1.get("status"),
            "remaining": pay1.get("remaining"),
        })

        # Payment 2: Anthropic API credits
        pay2 = await execute_mpp_payment(client, session_id, {
            "amount": 15.00,
            "merchant": "anthropic.com",
            "memo": "Claude API credits",
        })
        pprint("Payment 2 — Anthropic", {
            "payment_id": pay2.get("payment_id"),
            "amount": pay2.get("amount"),
            "merchant": pay2.get("merchant"),
            "status": pay2.get("status"),
            "remaining": pay2.get("remaining"),
        })

        # ── Step 9: Check Audit Trail ──
        print("\nStep 9: Checking audit trail...")
        entries = await get_ledger_entries(client)
        pprint("Audit Trail", {
            "total_entries": len(entries),
            "entries": entries[:3] if entries else [],
        })

        # ── Step 10: Close Session ──
        print("\nStep 10: Closing MPP session...")
        closed = await close_mpp_session(client, session_id)
        pprint("Session Closed", {
            "session_id": closed.get("session_id"),
            "status": closed.get("status"),
            "total_spent": closed.get("total_spent"),
            "payment_count": closed.get("payment_count"),
        })

        # ── Summary ──
        print(f"""
╔══════════════════════════════════════════════════════════╗
║                    Demo Complete!                        ║
╠══════════════════════════════════════════════════════════╣
║  Wallet:    {str(wallet_id)[:42]:42s}  ║
║  Agent:     {str(agent_id)[:42]:42s}  ║
║  Mandate:   {str(mandate_id)[:42]:42s}  ║
║  Session:   {str(session_id)[:42]:42s}  ║
║  Payments:  2 executed, ${float(closed.get('total_spent', 25)):>6.2f} total spent       ║
║  Audit:     {len(entries)} ledger entries                            ║
╚══════════════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sardis E2E Demo — Tempo Mainnet Flow")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API base URL")
    parser.add_argument("--email", default="demo@sardis.sh", help="Demo account email")
    parser.add_argument("--password", default="demo_password_2026", help="Demo account password")
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.email, args.password))

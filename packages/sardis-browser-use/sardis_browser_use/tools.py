"""Sardis payment tools for Browser Use agents."""
from __future__ import annotations

import os

from sardis import SardisClient


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
    return client, wid


def register_sardis_actions(controller, *, api_key: str | None = None, wallet_id: str | None = None):
    """Register all Sardis payment actions on a Browser Use controller.

    Args:
        controller: Browser Use Controller instance
        api_key: Sardis API key (or set SARDIS_API_KEY env var)
        wallet_id: Default wallet ID (or set SARDIS_WALLET_ID env var)
    """
    client, default_wallet_id = _get_client(api_key, wallet_id)

    @controller.action("Pay for a product or service using Sardis wallet with spending policy controls")
    async def sardis_pay(amount: float, merchant: str, purpose: str = "Purchase") -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or pass wallet_id."
        result = client.payments.send(wid, to=merchant, amount=amount, purpose=purpose)
        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"

    @controller.action("Check wallet balance before making a purchase")
    async def sardis_balance(token: str = "USDC") -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wid, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    @controller.action("Check if a purchase would be allowed by Sardis spending policy")
    async def sardis_check_policy(amount: float, merchant: str) -> str:
        wid = default_wallet_id
        if not wid:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wid)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant} (balance: ${balance.balance}, remaining: ${balance.remaining})"

    return [sardis_pay, sardis_balance, sardis_check_policy]

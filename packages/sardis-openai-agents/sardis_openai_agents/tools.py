"""Sardis payment tools for OpenAI Agents SDK."""
from __future__ import annotations

import os
from typing import Optional

from sardis import SardisClient


def _get_client(api_key: Optional[str] = None, wallet_id: Optional[str] = None):
    key = api_key or os.getenv("SARDIS_API_KEY")
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    client = SardisClient(api_key=key)
    return client, wid


# Module-level client for decorator-based tools
_default_client: Optional[SardisClient] = None
_default_wallet_id: Optional[str] = None


def configure(api_key: Optional[str] = None, wallet_id: Optional[str] = None):
    """Configure the default Sardis client for tool functions.

    Call this before using the tools, or set SARDIS_API_KEY and SARDIS_WALLET_ID env vars.
    """
    global _default_client, _default_wallet_id
    _default_client, _default_wallet_id = _get_client(api_key, wallet_id)


def _ensure_client():
    global _default_client, _default_wallet_id
    if _default_client is None:
        _default_client, _default_wallet_id = _get_client()
    return _default_client, _default_wallet_id


try:
    from agents import function_tool

    @function_tool
    def sardis_pay(amount: float, merchant: str, purpose: str = "Payment") -> str:
        """Execute a policy-controlled payment from the agent's Sardis wallet. Checks spending limits before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured. Set SARDIS_WALLET_ID or call configure()."
        result = client.payments.send(wallet_id, to=merchant, amount=amount, purpose=purpose)
        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"

    @function_tool
    def sardis_check_balance(token: str = "USDC") -> str:
        """Check current wallet balance and spending limits."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    @function_tool
    def sardis_check_policy(amount: float, merchant: str) -> str:
        """Check if a payment would pass spending policy before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant}"

except ImportError:
    # openai-agents not installed - provide plain function versions
    def sardis_pay(amount: float, merchant: str, purpose: str = "Payment") -> str:
        """Execute a policy-controlled payment from the agent's Sardis wallet."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        result = client.payments.send(wallet_id, to=merchant, amount=amount, purpose=purpose)
        if result.success:
            return f"APPROVED: ${amount} to {merchant} (tx: {result.tx_id})"
        return f"BLOCKED by policy: {result.message}"

    def sardis_check_balance(token: str = "USDC") -> str:
        """Check current wallet balance and spending limits."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id, token=token)
        return f"Balance: ${balance.balance} {token} | Remaining limit: ${balance.remaining}"

    def sardis_check_policy(amount: float, merchant: str) -> str:
        """Check if a payment would pass spending policy before executing."""
        client, wallet_id = _ensure_client()
        if not wallet_id:
            return "Error: No wallet ID configured."
        balance = client.wallets.get_balance(wallet_id)
        if amount > balance.remaining:
            return f"WOULD BE BLOCKED: ${amount} exceeds remaining limit ${balance.remaining}"
        if amount > balance.balance:
            return f"WOULD BE BLOCKED: ${amount} exceeds balance ${balance.balance}"
        return f"WOULD BE ALLOWED: ${amount} to {merchant}"


def get_sardis_tools() -> list:
    """Get all Sardis tools for an OpenAI Agent."""
    return [sardis_pay, sardis_check_balance, sardis_check_policy]

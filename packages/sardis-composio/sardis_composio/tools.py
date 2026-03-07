"""Sardis payment tools for Composio."""
from __future__ import annotations

import os
from typing import Optional

from sardis import SardisClient


_cached_clients: dict[str, SardisClient] = {}


def _get_client(api_key: Optional[str] = None, wallet_id: Optional[str] = None):
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


def sardis_pay(amount: float, merchant: str, purpose: str = "Payment", api_key: str = "", wallet_id: str = "") -> dict:
    """Execute a policy-controlled payment from a Sardis wallet."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {"success": False, "error": "No wallet ID configured"}
    result = client.payments.send(wid, to=merchant, amount=amount, purpose=purpose)
    return {
        "success": result.success,
        "status": "APPROVED" if result.success else "BLOCKED",
        "tx_id": result.tx_id,
        "message": result.message or "",
        "amount": float(result.amount),
        "merchant": merchant,
    }


def sardis_check_balance(token: str = "USDC", api_key: str = "", wallet_id: str = "") -> dict:
    """Check wallet balance and spending limits."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {"success": False, "error": "No wallet ID configured"}
    balance = client.wallets.get_balance(wid, token=token)
    return {
        "success": True,
        "balance": float(balance.balance),
        "remaining": float(balance.remaining),
        "token": token,
    }


def sardis_check_policy(amount: float, merchant: str, api_key: str = "", wallet_id: str = "") -> dict:
    """Check if a payment would pass spending policy."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {"success": False, "error": "No wallet ID configured"}
    balance = client.wallets.get_balance(wid)
    allowed = amount <= balance.remaining and amount <= balance.balance
    return {
        "allowed": allowed,
        "reason": f"{'Allowed' if allowed else 'Would exceed limits'}: ${amount} to {merchant}",
        "balance": float(balance.balance),
        "remaining": float(balance.remaining),
    }


SARDIS_TOOLS = {
    "sardis_pay": sardis_pay,
    "sardis_check_balance": sardis_check_balance,
    "sardis_check_policy": sardis_check_policy,
}

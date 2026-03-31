"""Sardis payment tools for Composio."""
from __future__ import annotations

import os
from decimal import Decimal

try:
    from sardis_sdk import SardisClient
except ImportError:  # pragma: no cover - backwards compatibility
    from sardis import SardisClient

_cached_clients: dict[str, SardisClient] = {}


def _get_client(api_key: str | None = None, wallet_id: str | None = None):
    key = api_key or os.getenv("SARDIS_API_KEY") or ""
    wid = wallet_id or os.getenv("SARDIS_WALLET_ID")
    if key not in _cached_clients:
        _cached_clients[key] = SardisClient(api_key=key or None)
    return _cached_clients[key], wid


def sardis_pay(amount: float, merchant: str, purpose: str = "Payment", api_key: str = "", wallet_id: str = "") -> dict:
    """Execute a policy-controlled payment from a Sardis wallet."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {
            "success": False,
            "status": "BLOCKED",
            "tx_id": None,
            "message": "No wallet ID configured",
            "amount": float(amount),
            "merchant": merchant,
            "error": "No wallet ID configured",
        }
    try:
        result = client.wallets.transfer(
            wid,
            destination=merchant,
            amount=Decimal(str(amount)),
            token="USDC",
            memo=purpose,
        )
        return {
            "success": True,
            "status": getattr(result, "status", "APPROVED"),
            "tx_id": getattr(result, "tx_hash", None),
            "message": "Payment submitted",
            "amount": float(amount),
            "merchant": merchant,
        }
    except Exception as exc:
        return {
            "success": False,
            "status": "BLOCKED",
            "tx_id": None,
            "message": str(exc),
            "amount": float(amount),
            "merchant": merchant,
            "error": str(exc),
        }


def sardis_check_balance(token: str = "USDC", api_key: str = "", wallet_id: str = "") -> dict:
    """Check wallet balance and spending limits."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {"success": False, "error": "No wallet ID configured"}
    try:
        balance = client.wallets.get_balance(wid, token=token)
        return {
            "success": True,
            "balance": float(balance.balance),
            "remaining": float(balance.remaining),
            "token": token,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc), "token": token}


def sardis_check_policy(amount: float, merchant: str, api_key: str = "", wallet_id: str = "") -> dict:
    """Check if a payment would pass spending policy."""
    client, wid = _get_client(api_key or None, wallet_id or None)
    if not wid:
        return {"success": False, "allowed": False, "reason": "No wallet ID configured", "error": "No wallet ID configured"}
    try:
        wallet = client.wallets.get(wid)
        agent_id = getattr(wallet, "agent_id", None)
        if not agent_id:
            return {
                "success": False,
                "allowed": False,
                "reason": f"Wallet {wid} is not linked to an agent; cannot run canonical policy check",
                "error": f"Wallet {wid} is not linked to an agent; cannot run canonical policy check",
            }

        policy = client.policies.check(
            agent_id=agent_id,
            amount=Decimal(str(amount)),
            currency="USD",
            merchant_id=merchant,
        )
        balance = client.wallets.get_balance(wid)
        return {
            "success": True,
            "allowed": bool(policy.allowed),
            "reason": f"{policy.reason}: ${amount} to {merchant}",
            "policy_id": policy.policy_id,
            "agent_id": agent_id,
            "balance": float(balance.balance),
            "remaining": float(balance.remaining),
        }
    except Exception as exc:
        return {
            "success": False,
            "allowed": False,
            "reason": f"{exc}: ${amount} to {merchant}",
            "error": str(exc),
        }


SARDIS_TOOLS = {
    "sardis_pay": sardis_pay,
    "sardis_check_balance": sardis_check_balance,
    "sardis_check_policy": sardis_check_policy,
}

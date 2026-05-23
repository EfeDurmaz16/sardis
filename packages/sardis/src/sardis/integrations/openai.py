"""
OpenAI Function Calling integration for Sardis SDK.

DEPRECATED: This module is a compatibility shim. Use sardis-openai directly:
    pip install sardis-openai

    from sardis_openai import get_sardis_tools, handle_tool_call, SardisToolHandler
"""
from __future__ import annotations

import hashlib
import json
import os
import uuid
import warnings
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from typing import Any

warnings.warn(
    "sardis_sdk.integrations.openai is deprecated. "
    "Use sardis-openai package directly: pip install sardis-openai\n"
    "  from sardis_openai import get_sardis_tools, handle_tool_call",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sardis_openai import (  # type: ignore
        SARDIS_TOOL_DEFINITIONS,
        SardisToolHandler,
        get_sardis_tools,
        handle_tool_call,
    )
except ImportError:  # pragma: no cover - optional dependency bridge
    SARDIS_TOOL_DEFINITIONS: list[dict[str, Any]] = []
    SardisToolHandler = None  # type: ignore[assignment]

    def get_sardis_tools() -> list[dict[str, Any]]:
        return []

    async def handle_tool_call(*args: Any, **kwargs: Any) -> str:
        return json.dumps({"error": "sardis-openai package not installed"})


def _legacy_schema() -> dict[str, Any]:
    return {
        "name": "sardis_pay",
        "description": "Execute a payment with Sardis policy enforcement.",
        "parameters": {
            "type": "object",
            "properties": {
                "amount": {"type": "number"},
                "merchant": {"type": "string"},
                "merchant_address": {"type": "string"},
                "purpose": {"type": "string"},
                "token": {"type": "string", "default": "USDC"},
            },
            "required": ["amount", "merchant"],
        },
    }


def get_openai_function_schema() -> dict[str, Any]:
    """Legacy single-function schema compatibility."""
    return deepcopy(_legacy_schema())


def get_openai_tools() -> list[dict[str, Any]]:
    """Legacy OpenAI tool list compatibility (4 tools)."""
    pay = _legacy_schema()
    return [
        {"type": "function", "function": pay},
        {
            "type": "function",
            "function": {
                "name": "sardis_check_balance",
                "description": "Check wallet balance.",
                "parameters": {
                    "type": "object",
                    "properties": {"token": {"type": "string", "default": "USDC"}},
                    "required": [],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "sardis_get_wallet",
                "description": "Get wallet details.",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "sardis_check_policy",
                "description": "Dry-run policy check.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "amount": {"type": "number"},
                        "merchant": {"type": "string"},
                        "purpose": {"type": "string"},
                    },
                    "required": ["amount"],
                },
            },
        },
    ]


def _generate_mandate_id() -> str:
    """Generate deterministic-format mandate identifiers."""
    return f"mnd_{uuid.uuid4().hex[:24]}"


def _create_audit_hash(data: str) -> str:
    """Create a SHA-256 hash for audit correlation."""
    return hashlib.sha256(str(data).encode("utf-8")).hexdigest()


def create_tool_response(tool_call_id: str, content: str) -> dict[str, str]:
    """Create an OpenAI tool response payload."""
    return {
        "role": "tool",
        "tool_call_id": tool_call_id,
        "content": content,
    }


def _normalize_wallet_id(wallet_id: str | None) -> str:
    return str(wallet_id or os.getenv("SARDIS_WALLET_ID", "")).strip()


def _parse_amount(value: Any) -> Decimal:
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("amount must be a valid number")


def _json(payload: dict[str, Any]) -> str:
    return json.dumps(payload)


async def handle_function_call(
    client: Any,
    function_name: str,
    arguments: dict[str, Any] | None,
    *,
    wallet_id: str | None = None,
) -> str:
    """Legacy async function-call executor used by SDK tests."""
    args = arguments or {}
    resolved_wallet_id = _normalize_wallet_id(wallet_id)

    if function_name not in {
        "sardis_pay",
        "sardis_check_balance",
        "sardis_get_wallet",
        "sardis_check_policy",
    }:
        return _json({"success": False, "error": f"Unknown function: {function_name}"})

    if function_name in {"sardis_pay", "sardis_check_balance", "sardis_get_wallet", "sardis_check_policy"} and not resolved_wallet_id:
        return _json({"success": False, "error": "wallet ID is required"})

    if function_name == "sardis_pay":
        try:
            amount = _parse_amount(args.get("amount"))
            if amount <= 0:
                return _json({"success": False, "error": "amount must be positive"})

            merchant = str(args.get("merchant") or "").strip()
            if not merchant:
                return _json({"success": False, "error": "merchant is required"})

            result = await client.payments.execute_mandate(
                wallet_id=resolved_wallet_id,
                amount=float(amount),
                merchant=merchant,
                purpose=str(args.get("purpose") or ""),
                token=str(args.get("token") or "USDC"),
                mandate_id=_generate_mandate_id(),
            )
            return _json(
                {
                    "success": True,
                    "status": getattr(result, "status", "submitted"),
                    "payment_id": getattr(result, "payment_id", None),
                    "tx_hash": getattr(result, "tx_hash", None),
                    "chain": getattr(result, "chain", None),
                    "ledger_tx_id": getattr(result, "ledger_tx_id", None),
                    "audit_anchor": getattr(result, "audit_anchor", None),
                    "audit_hash": _create_audit_hash(f"{resolved_wallet_id}:{merchant}:{amount}"),
                }
            )
        except Exception as exc:
            message = str(exc)
            if any(marker in message.lower() for marker in ("policy", "blocked", "limit", "deny")):
                return _json({"success": False, "blocked": True, "error": message})
            return _json({"success": False, "error": message})

    if function_name == "sardis_check_balance":
        try:
            balance = await client.wallets.get_balance(
                resolved_wallet_id,
                token=str(args.get("token") or "USDC"),
            )
            return _json(
                {
                    "success": True,
                    "wallet_id": getattr(balance, "wallet_id", resolved_wallet_id),
                    "balance": str(getattr(balance, "balance", "0")),
                    "token": getattr(balance, "token", "USDC"),
                    "chain": getattr(balance, "chain", "base_sepolia"),
                    "address": getattr(balance, "address", ""),
                }
            )
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    if function_name == "sardis_get_wallet":
        try:
            wallet = await client.wallets.get(resolved_wallet_id)
            return _json(
                {
                    "success": True,
                    "wallet": {
                        "id": getattr(wallet, "id", resolved_wallet_id),
                        "agent_id": getattr(wallet, "agent_id", ""),
                        "currency": getattr(wallet, "currency", "USDC"),
                        "limit_per_tx": getattr(wallet, "limit_per_tx", None),
                        "limit_total": getattr(wallet, "limit_total", None),
                        "is_active": getattr(wallet, "is_active", False),
                        "addresses": getattr(wallet, "addresses", {}),
                    },
                }
            )
        except Exception as exc:
            return _json({"success": False, "error": str(exc)})

    try:
        amount = _parse_amount(args.get("amount"))
        wallet = await client.wallets.get(resolved_wallet_id)
        limit_raw = getattr(wallet, "limit_per_tx", None)
        limit = Decimal(str(limit_raw)) if limit_raw not in (None, "") else None
        is_active = bool(getattr(wallet, "is_active", True))

        allowed = is_active and (limit is None or amount <= limit)
        reason = ""
        if not is_active:
            reason = "wallet is inactive"
        elif limit is not None and amount > limit:
            reason = "amount exceeds per-tx limit"

        return _json(
            {
                "success": True,
                "allowed": allowed,
                "reason": reason,
            }
        )
    except Exception as exc:
        return _json({"success": False, "error": str(exc)})


__all__ = [
    "SARDIS_TOOL_DEFINITIONS",
    "SardisToolHandler",
    "_create_audit_hash",
    "_generate_mandate_id",
    "create_tool_response",
    "get_openai_function_schema",
    "get_openai_tools",
    "get_sardis_tools",
    "handle_function_call",
    "handle_tool_call",
]

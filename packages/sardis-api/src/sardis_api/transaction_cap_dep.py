"""FastAPI dependency for transaction cap enforcement on payment endpoints."""
from __future__ import annotations

import asyncio
import logging
from decimal import Decimal, InvalidOperation

from fastapi import Depends, HTTPException, Request, status
from sardis_guardrails.transaction_caps import get_transaction_cap_engine

from .authz import Principal, require_principal
from .operational_alerts import alert_cap_exceeded

logger = logging.getLogger("sardis.api.transaction_caps")


async def enforce_transaction_caps(
    request: Request,
    principal: Principal = Depends(require_principal),
) -> None:
    """FastAPI dependency that enforces transaction spend caps.

    Extracts amount from the request body and checks global/org/agent caps.
    Raises HTTP 429 if cap would be exceeded.
    """
    amount = await _extract_amount(request)
    if amount is None or amount <= 0:
        return  # No amount to check (read-only or zero-value op)

    org_id = principal.organization_id
    agent_id = _extract_agent_id(request)

    engine = get_transaction_cap_engine()
    result = await engine.check_and_record(
        amount=amount,
        org_id=org_id,
        agent_id=agent_id,
    )

    if not result.allowed:
        logger.warning(
            "Transaction cap exceeded: %s (org=%s, agent=%s, amount=%s)",
            result.message, org_id, agent_id, amount,
        )
        asyncio.create_task(alert_cap_exceeded(
            cap_type=result.cap_type,
            org_id=org_id,
            agent_id=agent_id,
            amount=str(amount),
            daily_total=str(result.daily_total),
        ))
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "detail": "transaction_cap_exceeded",
                "cap_type": result.cap_type,
                "remaining": str(result.remaining),
                "message": result.message,
            },
        )


async def _extract_amount(request: Request) -> Decimal | None:
    """Best-effort extraction of transaction amount from request body."""
    try:
        body = await request.json()
    except Exception:
        return None

    if not isinstance(body, dict):
        return None

    # Check common amount field names
    for key in ("amount", "total_amount", "payment_amount", "value"):
        val = body.get(key)
        if val is not None:
            try:
                return Decimal(str(val))
            except (InvalidOperation, ValueError):
                continue

    return None


def _extract_agent_id(request: Request) -> str | None:
    """Best-effort agent ID extraction from request state or path params."""
    if hasattr(request.state, "agent_id"):
        return request.state.agent_id

    path_params = request.path_params
    for key in ("agent_id", "sender_agent_id"):
        if key in path_params:
            return path_params[key]

    return None

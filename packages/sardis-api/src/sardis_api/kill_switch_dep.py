"""FastAPI dependency for kill switch enforcement on payment endpoints."""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import Depends, HTTPException, Request, status

from sardis_guardrails.kill_switch import KillSwitchError, get_kill_switch

from .authz import Principal, require_principal

logger = logging.getLogger("sardis.api.kill_switch")


def _detect_rail(request: Request) -> Optional[str]:
    """Detect payment rail from route prefix."""
    path = request.url.path
    if "/a2a" in path:
        return "a2a"
    if "/ap2" in path or "/mandates" in path:
        return "ap2"
    if "/checkout" in path or "/sessions" in path:
        return "checkout"
    return None


def _detect_chain(request: Request) -> Optional[str]:
    """Detect target chain from request body or path."""
    # Check path params first
    chain = request.path_params.get("chain")
    if chain:
        return chain
    # Check request state (set by earlier middleware)
    if hasattr(request.state, "chain"):
        return request.state.chain
    return None


async def require_kill_switch_clear(
    request: Request,
    principal: Principal = Depends(require_principal),
) -> None:
    """FastAPI dependency that blocks payment if any kill switch is active.

    Checks global, organization, agent, rail, and chain scopes.
    Raises HTTP 503 if payments are suspended.
    """
    org_id = principal.organization_id
    # Try to extract agent_id from the request body or path
    agent_id = _extract_agent_id(request)

    kill_switch = get_kill_switch()

    # Always check global and org scope
    try:
        # If we have an agent_id, check all three scopes
        if agent_id:
            await kill_switch.check(agent_id=agent_id, org_id=org_id)
        else:
            # Check global and org only
            global_activation = await kill_switch._backend.get_activation("global")
            if global_activation is not None:
                raise KillSwitchError(f"Global kill switch active: {global_activation.reason}")
            org_activation = await kill_switch._backend.get_activation(f"org:{org_id}")
            if org_activation is not None:
                raise KillSwitchError(f"Organization kill switch active: {org_activation.reason}")

        # Check rail-level kill switch
        rail = _detect_rail(request)
        if rail:
            await kill_switch.check_rail(rail)

        # Check chain-level kill switch
        chain = _detect_chain(request)
        if chain:
            await kill_switch.check_chain(chain)

    except KillSwitchError as e:
        msg = str(e)
        if "Global" in msg:
            scope = "global"
        elif "Organization" in msg:
            scope = "organization"
        elif "Agent" in msg:
            scope = "agent"
        elif "Rail" in msg:
            scope = "rail"
        elif "Chain" in msg:
            scope = "chain"
        else:
            scope = "unknown"
        logger.warning("Kill switch blocked payment: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "payments_suspended", "scope": scope},
        )


def _extract_agent_id(request: Request) -> Optional[str]:
    """Best-effort agent ID extraction from request state or path params."""
    # Check if agent_id was set on request state by earlier middleware/deps
    if hasattr(request.state, "agent_id"):
        return request.state.agent_id

    # Check path parameters
    path_params = request.path_params
    for key in ("agent_id", "sender_agent_id"):
        if key in path_params:
            return path_params[key]

    return None


async def require_kill_switch_clear_checkout(
    request: Request,
) -> None:
    """Kill switch check for public checkout endpoints (no principal required).

    Checks global and checkout rail scopes.
    """
    kill_switch = get_kill_switch()
    if await kill_switch.is_active_global():
        logger.warning("Kill switch blocked checkout payment (global)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "payments_suspended", "scope": "global"},
        )
    if await kill_switch.is_active_rail("checkout"):
        logger.warning("Kill switch blocked checkout payment (rail:checkout)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"detail": "payments_suspended", "scope": "rail"},
        )

"""Provider-layer execution surface.

Exposes the unified capability ports (see :mod:`server.providers`) over HTTP so
clients reach every external money/identity service through ONE env-gated
registry instead of provider-specific endpoints.

Authority boundary (the moat from #396):
  * Read / quote / screen operations (``GET .../matrix``, ``swap/quote``,
    ``bridge/quote``, ``kyt/screen``) are side-effect-free and run directly
    against the resolved port.
  * Money-MOVING operations (onramp/offramp/payout/card-issue/swap-execute)
    are NOT exposed here as fire-and-forget calls — they must be authorized by
    the :class:`PaymentOrchestrator` first; the adapter then *executes* the
    already-authorized instruction.  This router never authorizes, initiates,
    or settles money on its own.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from server.authz import require_principal
from server.dependencies import (
    get_bridge_port,
    get_kyt_port,
    get_provider_registry,
    get_swap_port,
)
from server.providers.ports import ProviderCapability, ProviderError, to_minor_units

logger = logging.getLogger(__name__)
router = APIRouter(dependencies=[Depends(require_principal)], tags=["provider-layer"])


# ── Capability matrix (introspection) ────────────────────────────────────


@router.get("/providers/matrix")
async def provider_matrix(registry: Any = Depends(get_provider_registry)) -> dict[str, Any]:
    """Return the resolved provider per capability: which adapter backs each
    port, whether it is live or sandbox, and its custody model.
    """
    rows: list[dict[str, Any]] = []
    for cap in ProviderCapability:
        try:
            port = registry.get(cap)
        except ProviderError as exc:  # required-in-prod, unconfigured
            rows.append(
                {
                    "capability": cap.value,
                    "provider": None,
                    "available": False,
                    "error": str(exc),
                }
            )
            continue
        rows.append(
            {
                "capability": cap.value,
                "provider": port.provider,
                "live": registry.has_real(cap),
                "sandbox": port.sandbox,
                "custody_model": port.custody_model.value,
            }
        )
    return {"providers": rows}


# ── Swap quote (read-only) ────────────────────────────────────────────────


class SwapQuoteRequest(BaseModel):
    chain: str = Field(description="Chain name (e.g. base, tempo)")
    sell_token: str = Field(description="Token to sell (address or symbol)")
    buy_token: str = Field(description="Token to buy (address or symbol)")
    sell_amount: Decimal = Field(description="Amount to sell (human units)")
    sell_decimals: int = Field(default=6, description="Decimals of sell_token (6 for USDC)")


@router.post("/providers/swap/quote")
async def swap_quote(
    request: SwapQuoteRequest,
    port: Any = Depends(get_swap_port),
) -> dict[str, Any]:
    """Quote a same-chain swap via the resolved SwapPort (LI.FI / 0x / Jupiter
    / sandbox).  Read-only: returns a quote the orchestrator can later authorize
    for execution.
    """
    try:
        sell_minor = to_minor_units(request.sell_amount, request.sell_decimals)
        result = await port.quote(
            chain=request.chain,
            sell_token=request.sell_token,
            buy_token=request.buy_token,
            sell_amount_minor=sell_minor,
        )
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {
        "provider": result.provider,
        "sandbox": result.sandbox,
        "custody_model": result.custody_model.value,
        "reference": result.reference,
        "status": result.status,
        "raw": result.raw,
    }


# ── Bridge quote (read-only) ──────────────────────────────────────────────


class BridgeQuoteRequest(BaseModel):
    from_chain: str
    to_chain: str
    token: str
    amount: Decimal
    decimals: int = Field(default=6)


@router.post("/providers/bridge/quote")
async def bridge_quote(
    request: BridgeQuoteRequest,
    port: Any = Depends(get_bridge_port),
) -> dict[str, Any]:
    """Quote a cross-chain bridge via the resolved BridgePort (Squid / CCTP v2
    / sandbox).  Read-only.
    """
    try:
        amount_minor = to_minor_units(request.amount, request.decimals)
        result = await port.quote(
            from_chain=request.from_chain,
            to_chain=request.to_chain,
            token=request.token,
            amount_minor=amount_minor,
        )
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc
    return {
        "provider": result.provider,
        "sandbox": result.sandbox,
        "custody_model": result.custody_model.value,
        "reference": result.reference,
        "status": result.status,
        "raw": result.raw,
    }


# ── KYT screening (report-only — the moat decides allow/deny) ─────────────


class KytScreenRequest(BaseModel):
    address: str
    chain: str | None = None


@router.post("/providers/kyt/screen")
async def kyt_screen(
    request: KytScreenRequest,
    port: Any = Depends(get_kyt_port),
) -> dict[str, Any]:
    """Screen an address via the resolved KytPort (OpenSanctions / Didit /
    sandbox).  The port REPORTS a verdict; it never decides allow/deny — the
    orchestrator (moat) does that in Phase 2.
    """
    try:
        result = await port.screen_address(address=request.address, chain=request.chain)
    except ProviderError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc
    return {
        "provider": result.provider,
        "sandbox": result.sandbox,
        "status": result.status,
        "raw": result.raw,
    }

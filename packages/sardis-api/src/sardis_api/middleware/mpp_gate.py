"""MPP dual-access gate — FastAPI dependency for pay-per-request endpoints.

Dual access logic:
- Authorization header present and does NOT start with "Payment " → authenticated
  user, pass through free.  The endpoint's own auth dependency (require_principal,
  require_api_key) handles full validation.
- Authorization header starts with "Payment " → MPP credential, validate payment.
- No Authorization header → return 402 with WWW-Authenticate challenge via pympp.

Env vars:
    MPP_SECRET_KEY      — HMAC secret shared with MPP network (required for challenge)
    MPP_RECIPIENT       — Wallet address that receives payments
    SARDIS_MPP_NETWORK  — "testnet" (default) or "mainnet"
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse


class _Mpp402(Exception):
    """Raised by mpp_gate to return a 402 with WWW-Authenticate header.

    We use a custom exception + handler instead of HTTPException because
    FastAPI's default error handler can strip custom headers (and some
    reverse proxies like Vercel do the same with problem+json).
    """

    def __init__(self, response: JSONResponse) -> None:
        self.response = response


async def _mpp_402_handler(_request: StarletteRequest, exc: _Mpp402) -> StarletteResponse:
    """Global exception handler — returns the pre-built 402 response."""
    return exc.response

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Conditional pympp import
# ---------------------------------------------------------------------------

try:
    from mpp import Challenge, Credential, Receipt, format_payment_receipt
    from mpp.methods.tempo import ChargeIntent, tempo
    from mpp.server import Mpp

    _HAS_MPP = True
except ImportError:
    _HAS_MPP = False
    Challenge = Credential = Receipt = Mpp = None  # type: ignore[assignment,misc]

# ---------------------------------------------------------------------------
# Network configuration
# ---------------------------------------------------------------------------

_NETWORK_CONFIG: dict[str, dict[str, Any]] = {
    "testnet": {
        "chain_id": 42431,
        "currency": "0x20c0000000000000000000000000000000000000",  # PATH_USD
    },
    "mainnet": {
        "chain_id": 4217,
        "currency": "0x20c000000000000000000000b9537d11c60e8b50",  # USDC
    },
}

_DEFAULT_RECIPIENT = "0x99085505f506576c5C5342cAFEf14d6be43e0E9C"

# ---------------------------------------------------------------------------
# Lazy-initialised Mpp server singleton
# ---------------------------------------------------------------------------

_mpp_server: Any = None


def _get_mpp_server() -> Any:
    """Create and cache the Mpp server instance."""
    global _mpp_server
    if _mpp_server is not None:
        return _mpp_server

    if not _HAS_MPP:
        return None

    network = os.getenv("SARDIS_MPP_NETWORK", "testnet").strip().lower()
    cfg = _NETWORK_CONFIG.get(network, _NETWORK_CONFIG["testnet"])

    recipient = os.getenv("MPP_RECIPIENT", _DEFAULT_RECIPIENT)

    method = tempo(
        intents={"charge": ChargeIntent()},
        chain_id=cfg["chain_id"],
        currency=cfg["currency"],
        recipient=recipient,
    )

    _mpp_server = Mpp.create(
        method=method,
        realm="sardis.sh",
    )
    logger.info(
        "MPP gate server initialised (network=%s, chain=%s, recipient=%s)",
        network,
        cfg["chain_id"],
        recipient,
    )
    return _mpp_server


# ---------------------------------------------------------------------------
# Public API — the dependency factory
# ---------------------------------------------------------------------------


def mpp_gate(
    price: str = "0.01",
    description: str = "Sardis API",
) -> Callable:
    """FastAPI dependency that gates an endpoint with MPP for unauthenticated users.

    Usage::

        @router.get("/intel", dependencies=[Depends(mpp_gate(price="0.05"))])
        async def get_intel(): ...

    Authenticated callers (Bearer token, API key) pass through free.
    Unauthenticated callers must pay via MPP (HTTP 402 flow).
    """

    async def dependency(request: Request):
        authorization = request.headers.get("Authorization", "")

        # -----------------------------------------------------------
        # 1. Authenticated user — pass through, let endpoint auth
        #    dependency do full validation.
        # -----------------------------------------------------------
        if authorization and not authorization.startswith("Payment "):
            return  # free access for authenticated users

        # -----------------------------------------------------------
        # Helper: build 402 response with WWW-Authenticate header.
        # Uses Response directly (not HTTPException) to guarantee the
        # header survives FastAPI error handlers and reverse proxies.
        # -----------------------------------------------------------
        def _challenge_response(challenge_obj: Any, msg: str) -> JSONResponse:
            return JSONResponse(
                status_code=402,
                headers={
                    "WWW-Authenticate": challenge_obj.to_www_authenticate(server.realm),
                },
                content={
                    "error": "payment_required",
                    "message": msg,
                    "method": challenge_obj.method,
                    "amount": price,
                    "docs": "https://docs.sardis.sh/mpp",
                },
            )

        server = _get_mpp_server()

        # -----------------------------------------------------------
        # 2. MPP payment credential — validate
        # -----------------------------------------------------------
        if authorization.startswith("Payment "):
            if server is None:
                return  # pympp not installed → no-op

            result = await server.charge(
                authorization=authorization,
                amount=price,
                description=description,
            )

            if isinstance(result, Challenge):
                from starlette.responses import Response as StarletteResponse
                # Raise a special exception that carries the full Response
                raise _Mpp402(
                    response=_challenge_response(
                        result,
                        f"Invalid or expired payment credential. This endpoint costs ${price} per request via MPP.",
                    )
                )

            # Payment verified — attach receipt to request state
            credential: Any = result[0]
            receipt: Any = result[1]
            request.state.mpp_receipt = receipt
            request.state.mpp_credential = credential
            logger.info(
                "MPP gate: payment verified (receipt=%s, amount=%s, desc=%s)",
                receipt.reference,
                price,
                description,
            )
            return  # paid access

        # -----------------------------------------------------------
        # 3. No auth, no payment → issue 402 challenge
        # -----------------------------------------------------------
        if server is None:
            return  # pympp not installed → no-op passthrough

        result = await server.charge(
            authorization=None,
            amount=price,
            description=description,
        )

        if isinstance(result, Challenge):
            logger.info(
                "MPP gate: issuing 402 challenge (price=%s, desc=%s)",
                price,
                description,
            )
            raise _Mpp402(
                response=_challenge_response(
                    result,
                    f"This endpoint costs ${price} per request via MPP. Authenticate with an API key for free access.",
                )
            )

        # Shouldn't happen — handle gracefully.
        return

    return dependency


# ---------------------------------------------------------------------------
# Convenience: attach Payment-Receipt header to response
# ---------------------------------------------------------------------------


def add_mpp_receipt_header(request: Request, response: JSONResponse) -> None:
    """If the request was paid via MPP, add the Payment-Receipt header."""
    receipt = getattr(getattr(request, "state", None), "mpp_receipt", None)
    if receipt is not None and _HAS_MPP:
        response.headers["Payment-Receipt"] = format_payment_receipt(receipt)


__all__ = [
    "mpp_gate",
    "add_mpp_receipt_header",
    "_Mpp402",
    "_mpp_402_handler",
]

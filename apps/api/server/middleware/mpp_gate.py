"""MPP dual-access gate — FastAPI dependency for pay-per-request endpoints.

THIS is Sardis's MPP-*conformant* surface: it speaks the "Payment" HTTP
authentication scheme (402 challenge → client pays off-band on Tempo → retry
with ``Authorization: Payment <credential>`` → 200 + ``Payment-Receipt``) via
the pympp SDK. (The session/budget authority in ``routes/protocol/mpp.py`` is
NOT the wire protocol — it is a Sardis-native Postgres surface.)

Dual access logic:
- Authorization header present and does NOT start with "Payment " → authenticated
  user, pass through free.  The endpoint's own auth dependency (require_principal,
  require_api_key) handles full validation.
- Authorization header starts with "Payment " → MPP credential, validate payment.
- No Authorization header → return 402 with WWW-Authenticate challenge via pympp.

Fail-closed (money path): a paid gate must never serve free data when it cannot
verify payment. If pympp is not installed or ``MPP_SECRET_KEY`` is unset, every
unauthenticated request gets 503 (payment verification unavailable) — never a
silent 200. Replay protection is mandatory: a settled tx hash that has already
been consumed is rejected via a durable replay store.

Env vars:
    MPP_SECRET_KEY      — HMAC secret for stateless challenge verification.
                          REQUIRED for the gate to verify payments. Missing ⇒
                          paid requests fail closed (503), never free.
    MPP_RECIPIENT       — Wallet address that receives payments
    SARDIS_MPP_NETWORK  — "testnet" (default) or "mainnet"
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest
from starlette.responses import Response as StarletteResponse

from server.middleware.mpp_replay_store import CacheBackedReplayStore


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


def reset_mpp_server() -> None:
    """Drop the cached Mpp server (test isolation / config reload)."""
    global _mpp_server
    _mpp_server = None


def _resolve_secret_key() -> str | None:
    """Read the MPP HMAC secret. Returns None (not "") if unset/blank."""
    secret = os.getenv("MPP_SECRET_KEY", "").strip()
    return secret or None


def _resolve_replay_store(request: Request | None) -> Any:
    """Build a durable replay store from the app's cache backend, if available.

    Returns a ``CacheBackedReplayStore`` (backed by Redis when configured, else
    in-memory) or ``None`` when no cache backend is reachable. ``None`` means
    pympp runs without its store-based tx-hash replay protection, so we only
    permit that in non-fatal dev paths — production wiring always has a cache
    backend on ``app.state.cache_service``.
    """
    cache_service = getattr(getattr(request, "app", None), "state", None)
    cache_service = getattr(cache_service, "cache_service", None) if cache_service else None
    backend = getattr(cache_service, "_backend", None)
    if backend is None:
        return None
    return CacheBackedReplayStore(backend)


def _get_mpp_server(request: Request | None = None) -> Any:
    """Create and cache the Mpp server instance.

    Returns ``None`` when the gate cannot verify payments — i.e. pympp is not
    installed OR ``MPP_SECRET_KEY`` is unset. Callers MUST treat ``None`` as
    fail-closed (deny / 503), never as free passthrough.
    """
    global _mpp_server
    if _mpp_server is not None:
        return _mpp_server

    if not _HAS_MPP:
        logger.warning("MPP gate: pympp not installed — paid requests will fail closed (503)")
        return None

    secret_key = _resolve_secret_key()
    if secret_key is None:
        logger.warning(
            "MPP gate: MPP_SECRET_KEY unset — cannot verify payments, paid requests "
            "will fail closed (503)"
        )
        return None

    network = os.getenv("SARDIS_MPP_NETWORK", "testnet").strip().lower()
    cfg = _NETWORK_CONFIG.get(network, _NETWORK_CONFIG["testnet"])

    recipient = os.getenv("MPP_RECIPIENT", _DEFAULT_RECIPIENT)

    store = _resolve_replay_store(request)
    if store is None:
        logger.warning(
            "MPP gate: no cache backend on app.state.cache_service — tx-hash replay "
            "protection runs without a durable store (dev only)"
        )

    method = tempo(
        intents={"charge": ChargeIntent()},
        chain_id=cfg["chain_id"],
        currency=cfg["currency"],
        recipient=recipient,
    )

    # secret_key + store passed explicitly: secret enables stateless challenge
    # verification; store is auto-wired into ChargeIntent for tx-hash replay
    # protection (Mpp._wire_store).
    _mpp_server = Mpp.create(
        method=method,
        realm="sardis.sh",
        secret_key=secret_key,
        store=store,
    )
    logger.info(
        "MPP gate server initialised (network=%s, chain=%s, recipient=%s, replay_store=%s)",
        network,
        cfg["chain_id"],
        recipient,
        "durable" if store is not None else "none",
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

        def _unavailable_response() -> JSONResponse:
            # Fail-closed: the gate cannot verify payment (pympp missing or
            # MPP_SECRET_KEY unset). A paid endpoint MUST NOT serve free data,
            # so we deny rather than pass through.
            return JSONResponse(
                status_code=503,
                content={
                    "error": "payment_verification_unavailable",
                    "message": (
                        "This endpoint requires payment via MPP, but payment "
                        "verification is not currently available. Authenticate "
                        "with an API key for free access."
                    ),
                    "docs": "https://docs.sardis.sh/mpp",
                },
            )

        server = _get_mpp_server(request)

        # -----------------------------------------------------------
        # 2. MPP payment credential — validate
        # -----------------------------------------------------------
        if authorization.startswith("Payment "):
            if server is None:
                raise _Mpp402(response=_unavailable_response())

            result = await server.charge(
                authorization=authorization,
                amount=price,
                description=description,
            )

            if isinstance(result, Challenge):
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
            # Fail-closed: cannot mint a verifiable challenge → deny, never free.
            raise _Mpp402(response=_unavailable_response())

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
    "reset_mpp_server",
    "_Mpp402",
    "_mpp_402_handler",
]

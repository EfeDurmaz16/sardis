"""MPP Demo — Paid API endpoint for Stripe MPP team demo.

Demonstrates the full HTTP 402 payment flow using the pympp SDK:
1. GET /api/v2/demo/paid-data → 402 with WWW-Authenticate challenge (no credential)
2. Client pays via Tempo and resends with Authorization header
3. Server validates credential, returns data + Payment-Receipt header

Designed for Ben Berke (Stripe) to test with `npx mppx`.

Env vars:
    MPP_SECRET_KEY — HMAC secret for stateless challenge verification (required)
    MPP_DEMO_RECIPIENT — Sardis wallet address to receive payments
    MPP_DEMO_PRICE — Price per request in USD (default: "0.001")
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from mpp import Challenge, Credential, Receipt, format_payment_receipt
from mpp.methods.tempo import ChargeIntent, tempo

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Lazy-initialized Mpp server instance
# ---------------------------------------------------------------------------

_mpp_server = None


def _get_mpp_server():
    """Create and cache the Mpp server instance."""
    global _mpp_server
    if _mpp_server is not None:
        return _mpp_server

    from mpp.server import Mpp

    recipient = os.getenv(
        "MPP_DEMO_RECIPIENT",
        # MPC wallet on Base Sepolia + Tempo testnet
        "0x99085505f506576c5C5342cAFEf14d6be43e0E9C",
    )

    # Use Tempo testnet (Moderato, chain 42431) for demo
    method = tempo(
        intents={"charge": ChargeIntent()},
        chain_id=42431,
        currency="0x20c0000000000000000000000000000000000000",  # PATH_USD (testnet)
        recipient=recipient,
    )

    _mpp_server = Mpp.create(
        method=method,
        realm="sardis.sh",
    )
    logger.info("MPP demo server initialized (recipient=%s)", recipient)
    return _mpp_server


# ---------------------------------------------------------------------------
# Sardis policy check (lightweight for demo)
# ---------------------------------------------------------------------------

_MAX_SINGLE_PAYMENT = 100.0  # $100 max per request
_DAILY_LIMIT = 1000.0  # $1,000 daily cap
_daily_total = 0.0
_daily_reset: str = ""


def _policy_check(amount_usd: float) -> tuple[bool, str]:
    """Run basic Sardis policy checks on the payment."""
    global _daily_total, _daily_reset

    today = datetime.now(UTC).strftime("%Y-%m-%d")
    if _daily_reset != today:
        _daily_total = 0.0
        _daily_reset = today

    if amount_usd > _MAX_SINGLE_PAYMENT:
        return False, f"Amount ${amount_usd} exceeds single-payment limit (${_MAX_SINGLE_PAYMENT})"

    if _daily_total + amount_usd > _DAILY_LIMIT:
        return False, f"Daily limit reached (${_daily_total:.2f} / ${_DAILY_LIMIT})"

    return True, "ALLOWED by Sardis policy (3 checks passed)"


# ---------------------------------------------------------------------------
# Demo endpoint
# ---------------------------------------------------------------------------

DEMO_PRICE = os.getenv("MPP_DEMO_PRICE", "0.001")


@router.get("/paid-data")
async def paid_data(request: Request):
    """Sardis paid API endpoint — returns market intelligence data.

    First request (no Authorization): returns 402 with WWW-Authenticate challenge.
    Second request (with credential): validates payment, returns data + receipt.
    """
    server = _get_mpp_server()
    authorization = request.headers.get("Authorization")

    result = await server.charge(
        authorization=authorization,
        amount=DEMO_PRICE,
        description="Sardis market intelligence - real-time agent economy data",
    )

    # -- 402: payment required --
    if isinstance(result, Challenge):
        logger.info(
            "MPP demo: issuing 402 challenge (price=%s, method=%s)",
            DEMO_PRICE, result.method,
        )
        return JSONResponse(
            status_code=402,
            headers={"WWW-Authenticate": result.to_www_authenticate(server.realm)},
            content={
                "error": "payment_required",
                "message": f"This endpoint costs ${DEMO_PRICE} per request via MPP",
                "method": result.method,
                "currency": "PATH_USD",
                "amount": DEMO_PRICE,
                "docs": "https://docs.sardis.sh/mpp",
            },
        )

    # -- Payment verified --
    credential: Credential = result[0]
    receipt: Receipt = result[1]

    # Sardis policy gate
    price_float = float(DEMO_PRICE)
    allowed, reason = _policy_check(price_float)
    if not allowed:
        logger.warning("MPP demo: payment blocked by policy — %s", reason)
        return JSONResponse(
            status_code=403,
            content={"error": "policy_denied", "reason": reason},
        )

    # Track spend
    global _daily_total
    _daily_total += price_float

    # Log payment
    logger.info(
        "MPP demo: payment verified (receipt=%s, method=%s, amount=%s)",
        receipt.reference, receipt.method, DEMO_PRICE,
    )

    # Build response with paid data
    now = datetime.now(UTC)
    data = {
        "market": "USDC/USD",
        "price": 1.0001,
        "agents_online": 47,
        "volume_24h": 125000,
        "sardis_policy_checks": 3,
        "sardis_policy_result": reason,
        "timestamp": now.isoformat(),
        "powered_by": "Sardis × MPP",
    }

    receipt_header = format_payment_receipt(receipt)

    return JSONResponse(
        status_code=200,
        headers={"Payment-Receipt": receipt_header},
        content=data,
    )


@router.get("/info")
async def demo_info():
    """Public info about the demo paid endpoint — no auth required."""
    return {
        "endpoint": "/api/v2/demo/paid-data",
        "price": DEMO_PRICE,
        "currency": "PATH_USD",
        "network": "tempo-testnet",
        "chain_id": 42431,
        "method": "tempo",
        "description": "Sardis market intelligence API - pay-per-request via MPP",
        "test_command": f"npx mppx https://sardis-api-staging-482463483786.us-central1.run.app/api/v2/demo/paid-data",
    }

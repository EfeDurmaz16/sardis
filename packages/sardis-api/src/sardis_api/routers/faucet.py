"""Testnet faucet — drips test USDC to user wallets."""
from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

logger = logging.getLogger(__name__)
router = APIRouter()

DRIP_AMOUNT = Decimal("100")
DRIP_COOLDOWN = 86400  # 24 hours

# Rate limit: 1 drip per org per day
_drip_timestamps: dict[str, float] = defaultdict(float)


class DripRequest(BaseModel):
    wallet_id: str | None = Field(default=None, description="Target wallet (uses default if omitted)")


class DripResponse(BaseModel):
    tx_hash: str | None
    amount: str
    token: str
    chain: str
    wallet_address: str
    status: str
    next_steps: list[str]


@router.post("/drip", response_model=DripResponse)
async def faucet_drip(
    req: DripRequest = DripRequest(),
    principal: Principal = Depends(require_principal),
):
    """Drip 100 test USDC to the caller's wallet.

    Only available in test environment (sk_test_ keys).
    Rate limited: 1 drip per organization per 24 hours.
    """
    # Check environment
    env = getattr(principal, "environment", "test")
    if env != "test":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faucet is only available in test environment (sk_test_ keys)",
        )

    # Rate limit check
    last_drip = _drip_timestamps.get(principal.org_id, 0)
    now = time.time()
    if now - last_drip < DRIP_COOLDOWN:
        remaining = int(DRIP_COOLDOWN - (now - last_drip))
        hours = remaining // 3600
        mins = (remaining % 3600) // 60
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Faucet cooldown: {hours}h {mins}m remaining (1 drip per 24h)",
        )

    # Find wallet
    wallet_address = None
    wallet_id_resolved = req.wallet_id

    # Try to find wallet — gracefully handle missing dependencies
    try:
        from sardis_api.dependencies import get_container
        container = get_container()

        if req.wallet_id:
            wallet = await container.wallet_repository.get(req.wallet_id)
            if wallet:
                wallet_address = wallet.get_address("base_sepolia")
                wallet_id_resolved = wallet.wallet_id
        else:
            # Find default wallet for this org
            wallets = await container.wallet_repository.list(limit=100)
            for w in wallets:
                addr = w.get_address("base_sepolia")
                if addr:
                    wallet_address = addr
                    wallet_id_resolved = w.wallet_id
                    break
    except Exception as e:
        logger.warning("Could not resolve wallet: %s", e)

    if not wallet_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No testnet wallet found. Create one first: POST /api/v2/wallets {\"chain\": \"base_sepolia\"}",
        )

    # Execute drip
    tx_hash = None
    drip_status = "completed"

    faucet_key = os.getenv("SARDIS_FAUCET_PRIVATE_KEY")
    if faucet_key:
        try:
            from sardis_api.dependencies import get_container
            container = get_container()
            tx_hash = await container.chain_executor.transfer_erc20(
                chain="base_sepolia",
                token="USDC",
                to_address=wallet_address,
                amount=DRIP_AMOUNT,
                private_key=faucet_key,
            )
            logger.info("Faucet drip: %s USDC to %s tx=%s", DRIP_AMOUNT, wallet_address, tx_hash)
        except Exception as e:
            logger.error("Faucet drip failed: %s", e)
            drip_status = "simulated"
    else:
        logger.info("Faucet drip (simulated): %s USDC to %s (no SARDIS_FAUCET_PRIVATE_KEY)", DRIP_AMOUNT, wallet_address)
        drip_status = "simulated"

    _drip_timestamps[principal.org_id] = now

    return DripResponse(
        tx_hash=tx_hash,
        amount=str(DRIP_AMOUNT),
        token="USDC",
        chain="base_sepolia",
        wallet_address=wallet_address,
        status=drip_status,
        next_steps=[
            "POST /api/v2/spending-mandates — Set spending policy (required before payments)",
            "POST /api/v2/agents — Create an AI agent",
        ],
    )

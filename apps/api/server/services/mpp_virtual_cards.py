"""MPP virtual card issuance helpers."""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import UTC, datetime
from uuid import uuid4

from server.models.mpp import IssueCardRequest, IssueCardResponse

logger = logging.getLogger(__name__)


def should_issue_sandbox_card() -> bool:
    chain_mode = os.getenv("SARDIS_CHAIN_MODE", "simulated").strip().lower()
    sandbox_override = os.getenv("SARDIS_VIRTUAL_CARDS_SANDBOX", "").strip().lower() == "true"
    return chain_mode != "live" or sandbox_override


def issue_sandbox_card(request: IssueCardRequest) -> IssueCardResponse:
    card_id = f"sandbox_card_{uuid4().hex[:12]}"
    now = datetime.now(UTC)
    seed = hashlib.sha256(f"{card_id}{request.amount}{now.isoformat()[:10]}".encode()).hexdigest()
    card_number = f"4000 00{seed[:2]} {seed[2:6]} {seed[6:10]}"
    cvv = seed[10:13]
    expiry_month = str((int(seed[13:15], 16) % 12) + 1).zfill(2)

    return IssueCardResponse(
        card_id=card_id,
        card_number=card_number,
        cvv=cvv,
        expiry=f"{expiry_month}/{now.year + 2}",
        amount=str(request.amount),
        currency=request.currency,
        status="ready",
        card_type="single_use",
        sandbox=True,
    )


async def issue_live_card(request: IssueCardRequest) -> IssueCardResponse:
    from sardis_mpp.services.laso import LasoMPPService

    laso = LasoMPPService()
    card = await laso.issue_card(amount=request.amount, currency=request.currency)
    return IssueCardResponse(
        card_id=card.card_id,
        card_number=card.card_number,
        cvv=card.cvv,
        expiry=card.expiry,
        amount=str(card.amount),
        currency=card.currency,
        status=card.status,
        card_type=card.card_type,
        sandbox=False,
    )


async def issue_mpp_virtual_card(request: IssueCardRequest) -> IssueCardResponse:
    if should_issue_sandbox_card():
        response = issue_sandbox_card(request)
        logger.info("Sandbox virtual card issued: %s amount=%s", response.card_id, request.amount)
        return response

    response = await issue_live_card(request)
    logger.info("Virtual card issued: %s amount=%s via Laso/Locus MPP", response.card_id, request.amount)
    return response

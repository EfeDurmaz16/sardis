"""MPP payment execution helpers."""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import uuid4

from server.models.mpp import ExecutePaymentRequest
from server.repositories.mpp_session_repository import get_db_pool

logger = logging.getLogger(__name__)


def chain_executor_key(chain: str) -> str:
    return {
        "tempo": "tempo",
        "tempo_testnet": "tempo_testnet",
        "tempo_moderato": "tempo_testnet",
    }.get(chain, chain)


async def resolve_wallet_address(wallet_id: str) -> str | None:
    pool = await get_db_pool()
    if not pool:
        return None

    async with pool.acquire() as conn:
        addr_row = await conn.fetchrow(
            "SELECT addresses FROM wallets WHERE external_id = $1",
            wallet_id,
        )
    if not addr_row or not addr_row["addresses"]:
        return None

    addresses = addr_row["addresses"]
    if not isinstance(addresses, dict):
        addresses = json.loads(addresses)
    return (
        addresses.get("tempo")
        or addresses.get("base_sepolia")
        or addresses.get("base")
        or next(iter(addresses.values()), None)
    )


async def execute_chain_payment(
    *,
    chain_executor: Any,
    session: dict[str, Any],
    request: ExecutePaymentRequest,
    payment_id: str,
    organization_id: str,
) -> str | None:
    """Build and dispatch the on-chain MPP payment mandate."""
    from sardis.core.mandates import PaymentMandate, VCProof

    chain_key = chain_executor_key(session["chain"])
    wallet_id = session.get("wallet_id")
    if not wallet_id:
        raise RuntimeError("Session has no wallet_id — cannot sign transaction")

    amount_minor = int(request.amount * Decimal("1000000"))

    from_address = None
    try:
        from_address = await resolve_wallet_address(wallet_id)
        if from_address:
            logger.info("Resolved wallet address from DB: %s -> %s", wallet_id, from_address)
    except Exception as exc:
        logger.warning("Could not resolve wallet address from DB: %s", exc)

    mandate = PaymentMandate(
        mandate_id=payment_id,
        mandate_type="payment",
        issuer=f"sardis:mpp:{session['session_id']}",
        subject=organization_id,
        expires_at=int(datetime.now(UTC).timestamp()) + 300,
        nonce=uuid4().hex,
        proof=VCProof(
            verification_method="sardis:mpp:internal",
            created=datetime.now(UTC).isoformat(),
            proof_value="mpp-session-authorized",
        ),
        domain=request.merchant,
        purpose="checkout",
        chain=chain_key,
        token=session.get("currency", "USDC"),
        amount_minor=amount_minor,
        destination=request.destination or request.merchant,
        audit_hash=f"mpp:{session['session_id']}:{payment_id}",
        wallet_id=wallet_id,
        from_address=from_address,
        ai_agent_presence=True,
        transaction_modality="human_not_present",
        merchant_domain=request.merchant_url or request.merchant,
    )

    receipt = await chain_executor.dispatch_payment(mandate)
    logger.info(
        "MPP on-chain payment success: %s tx=%s chain=%s",
        payment_id,
        receipt.tx_hash,
        chain_key,
    )
    return receipt.tx_hash

"""Across bridge adapter — optimistic cross-chain transfers.

Across uses an optimistic verification model with a network of
relayers for fast cross-chain token transfers. Used as fallback
when Relay is unavailable.

Usage::

    bridge = AcrossBridgeAdapter()
    quote = await bridge.quote("base", "tempo", "USDC", Decimal("100"))
    transfer = await bridge.initiate_transfer(quote.quote_id)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.chain.bridges.across")

ACROSS_API_BASE = "https://across.to/api"

# Across supported chain IDs
CHAIN_IDS = {
    "ethereum": 1,
    "base": 8453,
    "arbitrum": 42161,
    "optimism": 10,
    "polygon": 137,
    "tempo": 4217,
}

# Common token addresses per chain (USDC)
USDC_ADDRESSES = {
    "ethereum": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",
    "base": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
    "arbitrum": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",
    "optimism": "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",
    "polygon": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",
    "tempo": "0x20c0000000000000000000000000000000000000",
}


@dataclass
class AcrossQuote:
    """A bridge quote from Across."""
    quote_id: str = field(default_factory=lambda: f"axq_{uuid4().hex[:8]}")
    from_chain: str = ""
    to_chain: str = ""
    token: str = "USDC"
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    relay_fee: Decimal = field(default_factory=lambda: Decimal("0"))
    lp_fee: Decimal = field(default_factory=lambda: Decimal("0"))
    total_fee: Decimal = field(default_factory=lambda: Decimal("0"))
    output_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    estimated_fill_time_seconds: int = 60
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(seconds=30)
    )


@dataclass
class AcrossTransfer:
    """A bridge transfer via Across."""
    transfer_id: str = field(default_factory=lambda: f"axt_{uuid4().hex[:8]}")
    quote_id: str = ""
    deposit_tx_hash: str | None = None
    fill_tx_hash: str | None = None
    status: str = "pending"  # pending, deposited, filled, completed, expired
    from_chain: str = ""
    to_chain: str = ""
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class AcrossBridgeAdapter:
    """Cross-chain bridge adapter using Across Protocol.

    Across uses optimistic verification with a relayer network.
    Typical fill time: 30-120 seconds.
    """

    def __init__(self, api_base: str = ACROSS_API_BASE) -> None:
        self._api_base = api_base

    async def quote(
        self,
        from_chain: str,
        to_chain: str,
        token: str = "USDC",
        amount: Decimal = Decimal("0"),
    ) -> AcrossQuote:
        """Get a bridge quote from Across."""
        import httpx

        src_chain_id = CHAIN_IDS.get(from_chain)
        dst_chain_id = CHAIN_IDS.get(to_chain)
        token_addr = USDC_ADDRESSES.get(from_chain, "")

        if not src_chain_id or not dst_chain_id:
            raise ValueError(f"Unsupported chain pair: {from_chain} → {to_chain}")

        amount_raw = int(amount * Decimal("1000000"))  # 6 decimals

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._api_base}/suggested-fees",
                    params={
                        "originChainId": src_chain_id,
                        "destinationChainId": dst_chain_id,
                        "token": token_addr,
                        "amount": str(amount_raw),
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    relay_fee_pct = Decimal(str(data.get("relayFeePct", "0")))
                    lp_fee_pct = Decimal(str(data.get("lpFeePct", "0")))
                    relay_fee = (amount * relay_fee_pct / Decimal("1e18")).quantize(Decimal("0.000001"))
                    lp_fee = (amount * lp_fee_pct / Decimal("1e18")).quantize(Decimal("0.000001"))
                    total_fee = relay_fee + lp_fee
                    return AcrossQuote(
                        from_chain=from_chain,
                        to_chain=to_chain,
                        token=token,
                        amount=amount,
                        relay_fee=relay_fee,
                        lp_fee=lp_fee,
                        total_fee=total_fee,
                        output_amount=amount - total_fee,
                        estimated_fill_time_seconds=data.get("estimatedFillTimeSec", 60),
                    )
        except Exception:
            logger.debug("Across API unavailable, using estimated fees")

        # Fallback: estimate ~8bps fee
        fee = (amount * Decimal("8") / Decimal("10000")).quantize(Decimal("0.000001"))
        return AcrossQuote(
            from_chain=from_chain,
            to_chain=to_chain,
            token=token,
            amount=amount,
            total_fee=fee,
            output_amount=amount - fee,
        )

    async def initiate_transfer(self, quote: AcrossQuote) -> AcrossTransfer:
        """Initiate a bridge transfer from a quote.

        In production, this submits the deposit transaction on the source chain.
        """
        transfer = AcrossTransfer(
            quote_id=quote.quote_id,
            from_chain=quote.from_chain,
            to_chain=quote.to_chain,
            amount=quote.amount,
            status="pending",
        )

        logger.info(
            "Across transfer %s: %s %s %s→%s (fee: %s)",
            transfer.transfer_id, quote.amount, quote.token,
            quote.from_chain, quote.to_chain, quote.total_fee,
        )
        return transfer

    async def check_status(self, transfer_id: str) -> str:
        """Check the status of a bridge transfer."""
        # In production, query Across API for fill status
        return "pending"

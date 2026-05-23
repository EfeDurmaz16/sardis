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

    async def initiate_transfer(
        self,
        quote: AcrossQuote,
        signer=None,
    ) -> AcrossTransfer:
        """Initiate a bridge transfer by signing and broadcasting deposit tx.

        Across deposit flow:
        1. Call Across API to get deposit tx data (to, data, value)
        2. Sign the tx via FXSigner (Turnkey MPC or EOA)
        3. Broadcast to source chain RPC
        4. Return transfer with deposit_tx_hash

        Args:
            quote: Bridge quote from quote().
            signer: Optional FXSigner instance. Created from env if None.
        """
        import httpx

        transfer = AcrossTransfer(
            quote_id=quote.quote_id,
            from_chain=quote.from_chain,
            to_chain=quote.to_chain,
            amount=quote.amount,
            status="pending",
        )

        src_chain_id = CHAIN_IDS.get(quote.from_chain)
        dst_chain_id = CHAIN_IDS.get(quote.to_chain)
        token_addr = USDC_ADDRESSES.get(quote.from_chain, "")

        if not (src_chain_id and dst_chain_id and token_addr):
            return transfer

        # Get signer if not provided
        if signer is None:
            try:
                from sardis.chain.fx_signer import create_fx_signer
                signer = await create_fx_signer()
            except ImportError:
                pass

        try:
            amount_raw = int(quote.amount * Decimal("1000000"))

            # Get deposit tx data from Across API
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self._api_base}/deposit/tx",
                    json={
                        "originChainId": src_chain_id,
                        "destinationChainId": dst_chain_id,
                        "inputToken": token_addr,
                        "outputToken": USDC_ADDRESSES.get(quote.to_chain, token_addr),
                        "inputAmount": str(amount_raw),
                    },
                )

            if resp.status_code != 200:
                logger.warning("Across deposit API returned %d", resp.status_code)
                return transfer

            data = resp.json()

            # If we have a signer, sign and broadcast the deposit tx
            if signer and signer.is_available and data.get("to"):
                rpc_url = self._get_rpc_for_chain(src_chain_id)
                if rpc_url:
                    tx_dict = {
                        "to": data["to"],
                        "data": data.get("data", "0x"),
                        "value": int(data.get("value", "0"), 16) if isinstance(data.get("value"), str) else data.get("value", 0),
                        "gas": 300_000,
                        "chainId": src_chain_id,
                    }

                    tx_hash = await signer.sign_and_broadcast_evm(
                        tx_dict=tx_dict,
                        rpc_url=rpc_url,
                        chain=quote.from_chain,
                    )
                    transfer.deposit_tx_hash = tx_hash
                    transfer.status = "deposited"

                    # Extract on-chain depositId from FundsDeposited event logs
                    deposit_id = await self._extract_deposit_id(rpc_url, tx_hash)
                    if deposit_id is not None:
                        transfer.transfer_id = str(deposit_id)

                    logger.info("Across deposit broadcast: %s (depositId=%s, %s→%s)", tx_hash, transfer.transfer_id, quote.from_chain, quote.to_chain)
                else:
                    logger.warning("No RPC URL for chain %d — deposit not broadcast", src_chain_id)
            else:
                # No signer — just record the API response
                transfer.deposit_tx_hash = data.get("txHash")
                transfer.status = "pending_signature"
                logger.info("Across deposit data received but not signed (no signer)")

        except Exception as e:
            logger.warning("Across deposit failed: %s", e)

        if transfer.status == "pending":
            logger.info(
                "Across transfer %s queued: %s %s %s→%s (fee: %s)",
                transfer.transfer_id, quote.amount, quote.token,
                quote.from_chain, quote.to_chain, quote.total_fee,
            )

        return transfer

    async def check_status(self, transfer_id: str, origin_chain_id: int | None = None) -> str:
        """Check the status of a bridge transfer via Across API.

        Args:
            transfer_id: The on-chain depositId (not local UUID).
            origin_chain_id: Source chain ID (required by Across V3 API).
        """
        import httpx

        try:
            params: dict[str, Any] = {"depositId": transfer_id}
            if origin_chain_id is not None:
                params["originChainId"] = origin_chain_id

            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(
                    f"{self._api_base}/deposit/status",
                    params=params,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    status = data.get("status", "pending")
                    if status == "filled":
                        return "completed"
                    return status
        except Exception:
            logger.debug("Across status check failed for %s", transfer_id)

        return "pending"

    async def _extract_deposit_id(self, rpc_url: str, tx_hash: str) -> int | None:
        """Extract depositId from FundsDeposited event in transaction receipt.

        Across V3 FundsDeposited event signature:
        FundsDeposited(uint256,uint256,uint256,int64,uint32,uint32,...)
        Topic0: 0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f
        The depositId is the 4th indexed field (int64).
        """
        import httpx

        # FundsDeposited event topic0 (Across V3 SpokePool)
        FUNDS_DEPOSITED_TOPIC = "0xa123dc29aebf7d0c3322c8eeb5b999e859f39937950ed31056532713d0de396f"

        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                        "id": 1,
                    },
                )
                result = resp.json()

            receipt = result.get("result")
            if not receipt or not receipt.get("logs"):
                return None

            for log in receipt["logs"]:
                topics = log.get("topics", [])
                if topics and topics[0] == FUNDS_DEPOSITED_TOPIC:
                    # depositId is encoded in the log data; first 32 bytes
                    # of non-indexed data after the indexed topics
                    log_data = log.get("data", "0x")
                    if len(log_data) >= 66:
                        deposit_id = int(log_data[2:66], 16)
                        logger.info("Extracted on-chain depositId: %d from %s", deposit_id, tx_hash)
                        return deposit_id

        except Exception as e:
            logger.warning("Failed to extract depositId from %s: %s", tx_hash, e)

        return None

    @staticmethod
    def _get_rpc_for_chain(chain_id: int) -> str:
        """Get RPC URL for a chain from env vars."""
        import os
        rpc_map = {
            4217: os.getenv("SARDIS_TEMPO_RPC_URL", "https://rpc.tempo.xyz"),
            42431: os.getenv("SARDIS_TEMPO_RPC_URL", "https://rpc.moderato.tempo.xyz"),
            8453: os.getenv("SARDIS_BASE_RPC_URL", ""),
            1: os.getenv("SARDIS_ETH_RPC_URL", ""),
            137: os.getenv("SARDIS_POLYGON_RPC_URL", ""),
            42161: os.getenv("SARDIS_ARBITRUM_RPC_URL", ""),
        }
        return rpc_map.get(chain_id, "")

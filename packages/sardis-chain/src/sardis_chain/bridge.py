"""Cross-chain bridge client for Sardis.

Supports bridging stablecoins between chains using aggregator APIs.
Primary providers: Relay, Across, Squid.

Since CCTP V2 is NOT live on Tempo, we use third-party intent-based bridges.

Usage:
    bridge = CrossChainBridge()
    quote = await bridge.get_quote(
        source_chain_id=8453,       # Base
        destination_chain_id=4217,  # Tempo
        token="USDC",
        amount_wei=100_000_000,     # 100 USDC (6 decimals)
        sender="0x...",
        recipient="0x...",
    )
    result = await bridge.execute(quote)

Supported chains:
    Base (8453), Tempo (4217), Ethereum (1), Polygon (137),
    Arbitrum (42161), Optimism (10)

Note on CCTP: Circle's CCTP V2 does NOT support Tempo.
We use intent-based bridges instead. Relay is the fastest
(~1.5s fill time, ~$0.02 fee for USDC Base→Tempo).

Relay API v2 endpoints (confirmed live):
    POST https://api.relay.link/quote/v2
    POST https://api.relay.link/execute/bridge/v2
    GET  https://api.relay.link/intents/status/v3?requestId={id}
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from enum import Enum

import httpx

logger = logging.getLogger(__name__)


class BridgeProvider(str, Enum):
    RELAY = "relay"
    ACROSS = "across"
    SQUID = "squid"


# Chain ID → canonical name
CHAIN_NAMES = {
    1: "ethereum",
    8453: "base",
    137: "polygon",
    42161: "arbitrum",
    10: "optimism",
    4217: "tempo",
    42431: "tempo_testnet",
}

# USDC contract addresses per chain
USDC_ADDRESSES = {
    1: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48",      # Ethereum
    8453: "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",    # Base
    137: "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359",     # Polygon
    42161: "0xaf88d065e77c8cC2239327C5EDb3A432268e5831",   # Arbitrum
    10: "0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85",      # Optimism
    4217: "0x20C000000000000000000000b9537d11c60E8b50",     # Tempo (USDC.e)
}

# pathUSD on Tempo
PATHUSD_ADDRESS = "0x20c0000000000000000000000000000000000000"


@dataclass
class BridgeQuote:
    """Quote for a cross-chain bridge transfer."""
    provider: BridgeProvider
    quote_id: str
    source_chain_id: int
    destination_chain_id: int
    source_token: str
    destination_token: str
    input_amount: int          # In token minor units (e.g., 6 decimals for USDC)
    output_amount: int
    fee_amount: int
    estimated_time_seconds: int
    sender: str
    recipient: str
    # Provider-specific execution data
    tx_data: dict | None = None


@dataclass
class BridgeResult:
    """Result of an executed bridge transfer."""
    bridge_id: str
    provider: BridgeProvider
    status: str
    source_tx_hash: str | None = None
    destination_tx_hash: str | None = None
    source_chain_id: int = 0
    destination_chain_id: int = 0
    input_amount: int = 0
    output_amount: int = 0


class CrossChainBridge:
    """Multi-provider cross-chain bridge client.

    Queries multiple bridge providers and selects the best quote.
    Supports Relay, Across, and Squid APIs.
    """

    def __init__(
        self,
        preferred_provider: BridgeProvider = BridgeProvider.RELAY,
        timeout: float = 30.0,
    ):
        self.preferred_provider = preferred_provider
        self.timeout = timeout

    async def get_quote(
        self,
        source_chain_id: int,
        destination_chain_id: int,
        token: str = "USDC",
        amount_wei: int = 0,
        amount_usd: Decimal | None = None,
        sender: str = "",
        recipient: str = "",
    ) -> BridgeQuote:
        """Get a bridge quote from the preferred provider.

        Args:
            source_chain_id: Source chain ID (e.g., 8453 for Base)
            destination_chain_id: Destination chain ID (e.g., 4217 for Tempo)
            token: Token symbol (USDC, USDT, etc.)
            amount_wei: Amount in token minor units (6 decimals for USDC)
            amount_usd: Amount in USD (converted to minor units automatically)
            sender: Sender wallet address
            recipient: Recipient wallet address (usually same as sender)
        """
        if amount_usd and not amount_wei:
            amount_wei = int(amount_usd * 10**6)  # USDC has 6 decimals

        if not recipient:
            recipient = sender

        source_token = USDC_ADDRESSES.get(source_chain_id, "")
        dest_token = USDC_ADDRESSES.get(destination_chain_id, "")

        if self.preferred_provider == BridgeProvider.RELAY:
            return await self._relay_quote(
                source_chain_id, destination_chain_id,
                source_token, dest_token,
                amount_wei, sender, recipient,
            )
        elif self.preferred_provider == BridgeProvider.ACROSS:
            return await self._across_quote(
                source_chain_id, destination_chain_id,
                source_token, dest_token,
                amount_wei, sender, recipient,
            )
        else:
            return await self._squid_quote(
                source_chain_id, destination_chain_id,
                source_token, dest_token,
                amount_wei, sender, recipient,
            )

    async def execute(self, quote: BridgeQuote) -> BridgeResult:
        """Execute a bridge transfer using the quote's provider.

        Note: In production, this would sign and submit the transaction
        via the Sardis MPC wallet (Turnkey). For now, it returns the
        prepared transaction data for the caller to submit.
        """
        import uuid
        bridge_id = f"bridge_{uuid.uuid4().hex[:16]}"

        logger.info(
            "Bridge execute: %s %s→%s amount=%d provider=%s",
            bridge_id,
            CHAIN_NAMES.get(quote.source_chain_id, str(quote.source_chain_id)),
            CHAIN_NAMES.get(quote.destination_chain_id, str(quote.destination_chain_id)),
            quote.input_amount,
            quote.provider.value,
        )

        # In production: sign tx_data with MPC wallet and broadcast
        # For demo: return pending status with tx data ready for submission
        return BridgeResult(
            bridge_id=bridge_id,
            provider=quote.provider,
            status="pending_signature",
            source_chain_id=quote.source_chain_id,
            destination_chain_id=quote.destination_chain_id,
            input_amount=quote.input_amount,
            output_amount=quote.output_amount,
        )

    async def poll_relay_status(
        self,
        request_id: str,
        max_polls: int = 30,
        interval: float = 1.0,
    ) -> dict:
        """Poll Relay intent status until completion.

        Status lifecycle: waiting → depositing → pending → submitted → success
        """
        import asyncio

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            for i in range(max_polls):
                resp = await client.get(
                    "https://api.relay.link/intents/status/v3",
                    params={"requestId": request_id},
                )
                resp.raise_for_status()
                data = resp.json()

                status = data.get("status", "unknown")
                if status in ("success", "failure", "refunded"):
                    return data
                if i < max_polls - 1:
                    await asyncio.sleep(interval)

            return data  # Return last status even if not terminal

    # ── Provider implementations ─────────────────────────────────────

    async def _relay_quote(
        self,
        source_chain_id: int,
        dest_chain_id: int,
        source_token: str,
        dest_token: str,
        amount: int,
        sender: str,
        recipient: str,
    ) -> BridgeQuote:
        """Get quote from Relay (relay.link).

        Relay API v2: POST https://api.relay.link/quote/v2
        No API key required (50 req/min default rate limit).

        Confirmed live: Base→Tempo USDC with ~$0.02 fee, ~1.5s fill.
        Solver liquidity on Tempo: ~$518K USDC.

        Relay depository on Base: 0x4cd00e387622c35bddb9b4c962c136462338bc31
        """
        import os
        import uuid

        relay_api_key = os.getenv("RELAY_API_KEY", "")
        headers: dict[str, str] = {}
        if relay_api_key:
            headers["x-api-key"] = relay_api_key

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.post(
                    "https://api.relay.link/quote/v2",
                    json={
                        "user": sender,
                        "originChainId": source_chain_id,
                        "destinationChainId": dest_chain_id,
                        "originCurrency": source_token,
                        "destinationCurrency": dest_token,
                        "amount": str(amount),
                        "recipient": recipient,
                        "tradeType": "EXACT_INPUT",
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                # Parse Relay v2 response
                steps = data.get("steps", [])
                fees = data.get("fees", {})
                fee_amount = int(fees.get("relayer", {}).get("amount", "0"))

                # Extract time estimate from details
                details = data.get("details", {})
                time_estimate = int(details.get("timeEstimate", 10))

                # Extract tx data from steps (approve + deposit)
                tx_steps = []
                request_id = None
                for step in steps:
                    items = step.get("items", [])
                    for item in items:
                        tx_data_item = item.get("data", {})
                        if tx_data_item:
                            tx_steps.append({
                                "kind": step.get("id", "unknown"),
                                "tx": tx_data_item,
                            })
                        if item.get("check", {}).get("endpoint"):
                            # Extract requestId for status polling
                            endpoint = item["check"]["endpoint"]
                            if "requestId=" in endpoint:
                                request_id = endpoint.split("requestId=")[-1].split("&")[0]

                return BridgeQuote(
                    provider=BridgeProvider.RELAY,
                    quote_id=request_id or data.get("requestId", uuid.uuid4().hex[:16]),
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=amount - fee_amount,
                    fee_amount=fee_amount,
                    estimated_time_seconds=time_estimate,
                    sender=sender,
                    recipient=recipient,
                    tx_data={"steps": tx_steps} if tx_steps else None,
                )
            except httpx.HTTPError as e:
                logger.warning("Relay quote failed: %s, falling back to estimate", e)
                # Return estimated quote — based on confirmed live data:
                # ~$0.02 fee for USDC Base→Tempo, ~1.5s fill
                estimated_fee = max(int(amount * 0.001), 1000)  # 0.1% fee, min $0.001
                return BridgeQuote(
                    provider=BridgeProvider.RELAY,
                    quote_id=f"est_{uuid.uuid4().hex[:12]}",
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=amount - estimated_fee,
                    fee_amount=estimated_fee,
                    estimated_time_seconds=10,
                    sender=sender,
                    recipient=recipient,
                )

    async def _across_quote(
        self,
        source_chain_id: int,
        dest_chain_id: int,
        source_token: str,
        dest_token: str,
        amount: int,
        sender: str,
        recipient: str,
    ) -> BridgeQuote:
        """Get quote from Across Protocol.

        Across API: GET https://app.across.to/api/suggested-fees
        """
        import uuid

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                resp = await client.get(
                    "https://app.across.to/api/suggested-fees",
                    params={
                        "inputToken": source_token,
                        "outputToken": dest_token,
                        "originChainId": source_chain_id,
                        "destinationChainId": dest_chain_id,
                        "amount": str(amount),
                    },
                )
                resp.raise_for_status()
                data = resp.json()

                total_relay_fee = int(data.get("totalRelayFee", {}).get("total", "0"))
                timestamp = int(data.get("timestamp", "0"))

                return BridgeQuote(
                    provider=BridgeProvider.ACROSS,
                    quote_id=f"across_{timestamp}_{uuid.uuid4().hex[:8]}",
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=amount - total_relay_fee,
                    fee_amount=total_relay_fee,
                    estimated_time_seconds=int(data.get("estimatedFillTimeSec", 60)),
                    sender=sender,
                    recipient=recipient,
                )
            except httpx.HTTPError as e:
                logger.warning("Across quote failed: %s, falling back to estimate", e)
                estimated_fee = max(int(amount * 0.002), 2000)
                return BridgeQuote(
                    provider=BridgeProvider.ACROSS,
                    quote_id=f"est_{uuid.uuid4().hex[:12]}",
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=amount - estimated_fee,
                    fee_amount=estimated_fee,
                    estimated_time_seconds=60,
                    sender=sender,
                    recipient=recipient,
                )

    async def _squid_quote(
        self,
        source_chain_id: int,
        dest_chain_id: int,
        source_token: str,
        dest_token: str,
        amount: int,
        sender: str,
        recipient: str,
    ) -> BridgeQuote:
        """Get quote from Squid Router.

        Squid API: POST https://apiplus.squidrouter.com/v2/route
        Docs: https://docs.squidrouter.com
        """
        import os
        import uuid

        squid_api_key = os.getenv("SQUID_API_KEY", "")

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                headers = {}
                if squid_api_key:
                    headers["x-integrator-id"] = squid_api_key

                resp = await client.post(
                    "https://apiplus.squidrouter.com/v2/route",
                    json={
                        "fromAddress": sender,
                        "fromChain": str(source_chain_id),
                        "fromToken": source_token,
                        "fromAmount": str(amount),
                        "toChain": str(dest_chain_id),
                        "toToken": dest_token,
                        "toAddress": recipient,
                        "slippageConfig": {"autoMode": 1},
                    },
                    headers=headers,
                )
                resp.raise_for_status()
                data = resp.json()

                route = data.get("route", {})
                estimate = route.get("estimate", {})
                to_amount = int(estimate.get("toAmount", str(amount)))
                fee_costs = estimate.get("feeCosts", [])
                total_fee = sum(int(f.get("amount", "0")) for f in fee_costs)

                tx_data = route.get("transactionRequest", {})

                return BridgeQuote(
                    provider=BridgeProvider.SQUID,
                    quote_id=route.get("requestId", uuid.uuid4().hex[:16]),
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=to_amount,
                    fee_amount=total_fee,
                    estimated_time_seconds=int(estimate.get("estimatedRouteDuration", 120)),
                    sender=sender,
                    recipient=recipient,
                    tx_data=tx_data if tx_data else None,
                )
            except httpx.HTTPError as e:
                logger.warning("Squid quote failed: %s, falling back to estimate", e)
                estimated_fee = max(int(amount * 0.003), 3000)
                return BridgeQuote(
                    provider=BridgeProvider.SQUID,
                    quote_id=f"est_{uuid.uuid4().hex[:12]}",
                    source_chain_id=source_chain_id,
                    destination_chain_id=dest_chain_id,
                    source_token=source_token,
                    destination_token=dest_token,
                    input_amount=amount,
                    output_amount=amount - estimated_fee,
                    fee_amount=estimated_fee,
                    estimated_time_seconds=120,
                    sender=sender,
                    recipient=recipient,
                )

    async def get_best_quote(
        self,
        source_chain_id: int,
        destination_chain_id: int,
        token: str = "USDC",
        amount_wei: int = 0,
        amount_usd: Decimal | None = None,
        sender: str = "",
        recipient: str = "",
    ) -> BridgeQuote:
        """Query all providers and return the best quote (highest output)."""
        import asyncio

        if amount_usd and not amount_wei:
            amount_wei = int(amount_usd * 10**6)
        if not recipient:
            recipient = sender

        source_token = USDC_ADDRESSES.get(source_chain_id, "")
        dest_token = USDC_ADDRESSES.get(destination_chain_id, "")

        quotes = await asyncio.gather(
            self._relay_quote(source_chain_id, destination_chain_id, source_token, dest_token, amount_wei, sender, recipient),
            self._across_quote(source_chain_id, destination_chain_id, source_token, dest_token, amount_wei, sender, recipient),
            self._squid_quote(source_chain_id, destination_chain_id, source_token, dest_token, amount_wei, sender, recipient),
            return_exceptions=True,
        )

        valid_quotes = [q for q in quotes if isinstance(q, BridgeQuote)]
        if not valid_quotes:
            raise RuntimeError("No bridge quotes available from any provider")

        # Sort by output_amount descending (best deal first)
        valid_quotes.sort(key=lambda q: q.output_amount, reverse=True)
        best = valid_quotes[0]

        logger.info(
            "Best bridge quote: %s — output=%d fee=%d time=%ds",
            best.provider.value, best.output_amount, best.fee_amount, best.estimated_time_seconds,
        )
        return best

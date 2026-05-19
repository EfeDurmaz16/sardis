"""FX and Bridge API endpoints.

Cross-currency stablecoin swaps and cross-chain bridge transfers.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from server.authz import Principal, optional_principal, require_principal
from server.middleware.mpp_gate import mpp_gate

router = APIRouter()
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Request / Response Models
# ---------------------------------------------------------------------------

class FXQuoteRequest(BaseModel):
    from_currency: str = Field(..., description="Source currency (e.g., USDC)")
    to_currency: str = Field(..., description="Target currency (e.g., EURC)")
    from_amount: Decimal = Field(..., gt=0)
    chain: str = Field(default="tempo")
    slippage_bps: int = Field(default=50, ge=1, le=1000)


class FXQuoteResponse(BaseModel):
    quote_id: str
    from_currency: str
    to_currency: str
    from_amount: str
    to_amount: str
    rate: str
    effective_rate: str
    slippage_bps: int
    provider: str
    chain: str
    status: str
    expires_at: str
    created_at: str


class FXExecuteRequest(BaseModel):
    quote_id: str = Field(..., description="Quote ID to execute")


class FXRatesResponse(BaseModel):
    rates: list[dict]
    updated_at: str


class BridgeTransferRequest(BaseModel):
    from_chain: str = Field(...)
    to_chain: str = Field(...)
    token: str = Field(default="USDC")
    amount: Decimal = Field(..., gt=0)
    bridge_provider: str = Field(default="relay")


class BridgeTransferResponse(BaseModel):
    transfer_id: str
    from_chain: str
    to_chain: str
    token: str
    amount: str
    bridge_provider: str
    bridge_fee: str
    status: str
    estimated_seconds: int
    created_at: str


# ---------------------------------------------------------------------------
# FX Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/fx/quote",
    response_model=FXQuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Request an FX quote for a stablecoin swap",
    dependencies=[Depends(mpp_gate(price="0.005", description="FX quote"))],
)
async def create_fx_quote(
    req: FXQuoteRequest,
    principal: Principal | None = Depends(optional_principal),
) -> FXQuoteResponse:
    from sardis_v2_core.database import Database

    # Route through LiquidityRouter for real adapter-driven quotes
    try:
        from sardis_chain.liquidity_router import LiquidityRouter
        router_instance = LiquidityRouter()
        route = await router_instance.find_best_route(
            from_token=req.from_currency,
            to_token=req.to_currency,
            amount=req.from_amount,
            from_chain=req.chain,
        )
        provider = route.provider
        rate = route.estimated_rate
        to_amount = route.estimated_output
    except Exception:
        # Fallback to indicative rates if adapter unavailable
        provider = "tempo_dex" if req.chain == "tempo" else "uniswap_v3"
        rate = _get_indicative_rate(req.from_currency, req.to_currency)
        to_amount = (req.from_amount * rate).quantize(Decimal("0.000001"))

    quote_id = f"fxq_{uuid4().hex[:12]}"
    expires_at = datetime.now(UTC) + timedelta(seconds=30)

    await Database.execute(
        """INSERT INTO fx_quotes
           (quote_id, from_currency, to_currency, from_amount, to_amount,
            rate, slippage_bps, provider, chain, status, expires_at)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""",
        quote_id, req.from_currency, req.to_currency,
        req.from_amount, to_amount, rate, req.slippage_bps,
        provider, req.chain, "quoted", expires_at,
    )

    return FXQuoteResponse(
        quote_id=quote_id,
        from_currency=req.from_currency,
        to_currency=req.to_currency,
        from_amount=str(req.from_amount),
        to_amount=str(to_amount),
        rate=str(rate),
        effective_rate=str(to_amount / req.from_amount if req.from_amount else rate),
        slippage_bps=req.slippage_bps,
        provider=provider,
        chain=req.chain,
        status="quoted",
        expires_at=expires_at.isoformat(),
        created_at=datetime.now(UTC).isoformat(),
    )


@router.post(
    "/fx/execute",
    response_model=FXQuoteResponse,
    summary="Execute an FX swap from a quote",
)
async def execute_fx_quote(
    req: FXExecuteRequest,
    principal: Principal = Depends(require_principal),
) -> FXQuoteResponse:
    from sardis_v2_core.database import Database

    async with Database.transaction() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM fx_quotes WHERE quote_id = $1 FOR UPDATE NOWAIT",
            req.quote_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Quote not found")
        if row["status"] != "quoted":
            raise HTTPException(status_code=409, detail=f"Quote is {row['status']}")
        if datetime.now(UTC) > row["expires_at"]:
            await conn.execute(
                "UPDATE fx_quotes SET status = 'expired', updated_at = now() WHERE quote_id = $1",
                req.quote_id,
            )
            raise HTTPException(status_code=410, detail="Quote has expired")

        # Mark as executing
        await conn.execute(
            "UPDATE fx_quotes SET status = 'executing', updated_at = now() WHERE quote_id = $1",
            req.quote_id,
        )

    # Execute real swap via adapter
    tx_hash = None
    swap_status = "failed"
    try:
        # Get unified signer (Turnkey MPC or local EOA)
        from sardis_chain.fx_signer import create_fx_signer
        signer = await create_fx_signer()

        provider = row["provider"]

        # Chain-aware signing validation: Tempo needs access key, not Turnkey MPC
        if provider == "tempo_dex" and not signer.can_sign_tempo():
            raise HTTPException(
                status_code=503,
                detail="Tempo swaps require SARDIS_TEMPO_ACCESS_KEY (or SARDIS_EOA_PRIVATE_KEY). "
                       "Turnkey MPC is available but only supports Base/ETH (type 0x02). "
                       "Set SARDIS_TEMPO_ACCESS_KEY for Tempo type 0x76 signing.",
            )
        if provider in ("uniswap_v3", "uniswap_v4") and not signer.can_sign_evm():
            raise HTTPException(
                status_code=503,
                detail="EVM swaps require Turnkey MPC (TURNKEY_API_KEY) or SARDIS_EOA_PRIVATE_KEY.",
            )

        if provider == "tempo_dex":
            import os

            from sardis_chain.tempo.dex import DEXQuote, TempoDEXAdapter
            dex = TempoDEXAdapter(
                rpc_url=os.getenv("SARDIS_TEMPO_RPC_URL", "https://rpc.tempo.xyz"),
                private_key=signer.get_private_key(),  # From Turnkey or EOA
            )
            quote = DEXQuote(
                quote_id=row["quote_id"],
                from_token=row.get("from_currency", ""),
                to_token=row.get("to_currency", ""),
                from_amount=row["from_amount"],
                to_amount=row["to_amount"],
                rate=row["rate"],
                slippage_bps=row.get("slippage_bps", 50),
            )
            result = await dex.execute_swap(quote)
            tx_hash = result.get("tx_hash")
            swap_status = result.get("status", "failed")

        elif provider in ("uniswap_v3", "uniswap_v4"):
            import os

            from sardis_chain.uniswap_v3 import UniswapV3Adapter
            chain = row.get("chain", "base")
            rpc = os.getenv("SARDIS_BASE_RPC_URL", "")
            if not rpc:
                raise HTTPException(status_code=503, detail="SARDIS_BASE_RPC_URL not set for Uniswap V3")
            uni = UniswapV3Adapter(rpc_url=rpc, chain=chain)
            amount_raw = int(row["from_amount"] * Decimal("1000000"))
            from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType
            in_addr = TOKEN_REGISTRY[TokenType(row["from_currency"])].contract_addresses.get(chain, "")
            out_addr = TOKEN_REGISTRY[TokenType(row["to_currency"])].contract_addresses.get(chain, "")
            quote = await uni.get_quote(in_addr, out_addr, amount_raw)
            # Use unified signer for execution
            result = await uni.execute_swap(
                quote,
                private_key=signer.get_private_key(),
                recipient=signer.address,
            )
            tx_hash = result.get("tx_hash")
            swap_status = result.get("status", "failed")

        else:
            # Try CDPSwap if available
            try:
                import os

                from sardis_chain.cdp_swap import CDPSwapClient
                cdp_key = os.getenv("CDP_API_KEY")
                if cdp_key:
                    cdp = CDPSwapClient(api_key=cdp_key)
                    result = await cdp.execute_swap(
                        from_token=row["from_currency"],
                        to_token=row["to_currency"],
                        amount=str(row["from_amount"]),
                        chain=row.get("chain", "base"),
                    )
                    tx_hash = result.get("tx_hash")
                    swap_status = result.get("status", "completed")
                else:
                    raise NotImplementedError("No adapter available for this provider")
            except (ImportError, NotImplementedError):
                raise HTTPException(
                    status_code=503,
                    detail=f"No execution adapter available for provider '{provider}'. "
                           f"Set SARDIS_TEMPO_SIGNER_KEY for Tempo or CDP_API_KEY for Base.",
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Swap execution failed for %s: %s", req.quote_id, e)
        await Database.execute(
            "UPDATE fx_quotes SET status = 'failed', updated_at = now() WHERE quote_id = $1",
            req.quote_id,
        )
        raise HTTPException(status_code=502, detail=f"Swap execution failed: {e}")

    # Persist real execution result
    await Database.execute(
        "UPDATE fx_quotes SET status = $1, tx_hash = $2, updated_at = now() WHERE quote_id = $3",
        swap_status, tx_hash, req.quote_id,
    )

    updated = await Database.fetchrow(
        "SELECT * FROM fx_quotes WHERE quote_id = $1", req.quote_id
    )
    return _quote_row_to_response(updated)


@router.get(
    "/fx/rates",
    response_model=FXRatesResponse,
    summary="Get current indicative FX rates",
    dependencies=[Depends(mpp_gate(price="0.001", description="Stablecoin FX rates"))],
)
async def get_fx_rates(
    principal: Principal | None = Depends(optional_principal),
    chain: str = Query(default="tempo"),
) -> FXRatesResponse:
    """Get live FX rates from on-chain adapters (cached 30s)."""
    from sardis_chain.liquidity_router import LiquidityRouter

    router_instance = LiquidityRouter()
    pairs = [
        ("USDC", "EURC"), ("EURC", "USDC"),
        ("USDC", "USDT"), ("USDT", "USDC"),
    ]
    rates = []
    for from_c, to_c in pairs:
        try:
            route = await router_instance.find_best_route(
                from_token=from_c, to_token=to_c,
                amount=Decimal("1000"), from_chain=chain,
            )
            rates.append({
                "from": from_c,
                "to": to_c,
                "rate": str(route.estimated_rate),
                "provider": route.provider,
                "fee_bps": route.estimated_fee_bps,
            })
        except Exception:
            # Fallback to indicative
            rates.append({
                "from": from_c,
                "to": to_c,
                "rate": str(_get_indicative_rate(from_c, to_c)),
                "provider": "indicative",
                "fee_bps": 0,
            })
    return FXRatesResponse(
        rates=rates,
        updated_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Bridge Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/bridge/transfer",
    response_model=BridgeTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a cross-chain bridge transfer",
)
async def create_bridge_transfer(
    req: BridgeTransferRequest,
    principal: Principal = Depends(require_principal),
) -> BridgeTransferResponse:
    from sardis_v2_core.database import Database

    if req.from_chain == req.to_chain:
        raise HTTPException(status_code=422, detail="Source and destination chains must differ")

    # Try real bridge adapters with deterministic fallback: Relay → Across
    transfer_id = f"brt_{uuid4().hex[:12]}"
    actual_provider = req.bridge_provider
    fee = Decimal("0")
    estimated_seconds = 60

    for provider_name in ["relay", "across"]:
        try:
            if provider_name == "relay":
                from sardis_chain.bridges.relay import RelayBridgeAdapter
                adapter = RelayBridgeAdapter()
                quote = await adapter.quote(req.from_chain, req.to_chain, req.token, req.amount)
                fee = quote.total_fee if hasattr(quote, "total_fee") else _estimate_bridge_fee(provider_name, req.amount)
                estimated_seconds = quote.estimated_fill_time_seconds if hasattr(quote, "estimated_fill_time_seconds") else 30
                actual_provider = "relay"
                break
            elif provider_name == "across":
                from sardis_chain.bridges.across import AcrossBridgeAdapter
                adapter = AcrossBridgeAdapter()
                quote = await adapter.quote(req.from_chain, req.to_chain, req.token, req.amount)
                fee = quote.total_fee
                estimated_seconds = quote.estimated_fill_time_seconds
                actual_provider = "across"
                break
        except Exception as e:
            logger.warning("Bridge adapter %s failed: %s", provider_name, e)
            continue
    else:
        # Both adapters failed — use estimated values
        fee = _estimate_bridge_fee(req.bridge_provider, req.amount)
        estimated_seconds = _estimate_bridge_time(req.bridge_provider)

    # Initiate the actual bridge transfer after quoting
    bridge_status = "pending"
    source_tx_hash = None
    try:
        if actual_provider == "relay" and 'adapter' in dir():
            transfer_result = await adapter.initiate_transfer(quote)
            source_tx_hash = getattr(transfer_result, "deposit_tx_hash", None)
            bridge_status = "bridging" if source_tx_hash else "pending"
        elif actual_provider == "across" and 'adapter' in dir():
            transfer_result = await adapter.initiate_transfer(quote)
            source_tx_hash = getattr(transfer_result, "deposit_tx_hash", None)
            bridge_status = "bridging" if transfer_result.status == "deposited" else "pending"
    except Exception as e:
        logger.warning("Bridge initiate_transfer failed: %s", e)

    await Database.execute(
        """INSERT INTO bridge_transfers
           (transfer_id, from_chain, to_chain, token, amount,
            bridge_provider, bridge_fee, status, estimated_seconds,
            source_tx_hash)
           VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""",
        transfer_id, req.from_chain, req.to_chain, req.token,
        req.amount, actual_provider, fee, bridge_status, estimated_seconds,
        source_tx_hash,
    )

    return BridgeTransferResponse(
        transfer_id=transfer_id,
        from_chain=req.from_chain,
        to_chain=req.to_chain,
        token=req.token,
        amount=str(req.amount),
        bridge_provider=actual_provider,
        bridge_fee=str(fee),
        status=bridge_status,
        estimated_seconds=estimated_seconds,
        created_at=datetime.now(UTC).isoformat(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

# Indicative rates (in production, fetched from DEX orderbook)
_INDICATIVE_RATES: dict[tuple[str, str], Decimal] = {
    ("USDC", "EURC"): Decimal("0.9215"),
    ("EURC", "USDC"): Decimal("1.0852"),
    ("USDC", "USDT"): Decimal("1.0000"),
    ("USDT", "USDC"): Decimal("1.0000"),
}


def _get_indicative_rate(from_c: str, to_c: str) -> Decimal:
    return _INDICATIVE_RATES.get((from_c, to_c), Decimal("1.0"))


def _estimate_bridge_fee(provider: str, amount: Decimal) -> Decimal:
    # Simplified fee estimation
    fee_bps = {"relay": 5, "across": 8, "squid": 10, "bungee": 12, "layerzero": 15}
    bps = fee_bps.get(provider, 10)
    return (amount * Decimal(bps) / Decimal(10000)).quantize(Decimal("0.000001"))


def _estimate_bridge_time(provider: str) -> int:
    times = {"relay": 30, "across": 60, "squid": 120, "bungee": 90, "layerzero": 180}
    return times.get(provider, 60)


def _quote_row_to_response(row) -> FXQuoteResponse:
    return FXQuoteResponse(
        quote_id=row["quote_id"],
        from_currency=row["from_currency"],
        to_currency=row["to_currency"],
        from_amount=str(row["from_amount"]),
        to_amount=str(row["to_amount"]),
        rate=str(row["rate"]),
        effective_rate=str(row["to_amount"] / row["from_amount"] if row["from_amount"] else row["rate"]),
        slippage_bps=row["slippage_bps"],
        provider=row["provider"],
        chain=row["chain"],
        status=row["status"],
        expires_at=row["expires_at"].isoformat(),
        created_at=row["created_at"].isoformat(),
    )

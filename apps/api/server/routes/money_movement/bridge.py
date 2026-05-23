"""Cross-chain bridge API endpoints.

Enables bridging stablecoins (USDC) between EVM chains via the Relay protocol.
Flow: get quote -> sign & broadcast each step via MPC -> poll for completion.
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sardis.core import WalletRepository
from sardis_chain.bridge import (
    CHAIN_NAMES,
    USDC_ADDRESSES,
    BridgeProvider,
    CrossChainBridge,
)
from sardis_chain.executor import CHAIN_CONFIGS, ChainExecutor, TransactionRequest

from server.authz import Principal, require_principal

logger = logging.getLogger(__name__)

router = APIRouter(dependencies=[Depends(require_principal)])


# ── Request / Response Models ──────────────────────────────────────────


class BridgeQuoteRequest(BaseModel):
    source_chain_id: int = Field(..., description="Source chain ID (e.g., 8453 for Base)")
    dest_chain_id: int = Field(..., description="Destination chain ID (e.g., 4217 for Tempo)")
    token: str = Field(default="USDC", description="Token to bridge")
    amount: str = Field(..., description="Amount in USD (e.g., '100.00')")
    wallet_id: str = Field(..., description="Sardis wallet ID of the sender")


class BridgeQuoteResponse(BaseModel):
    quote_id: str
    provider: str
    source_chain_id: int
    source_chain_name: str
    dest_chain_id: int
    dest_chain_name: str
    source_token: str
    dest_token: str
    input_amount: str
    output_amount: str
    fee_amount: str
    fee_usd: str
    estimated_time_seconds: int
    sender: str
    recipient: str


class BridgeExecuteRequest(BaseModel):
    source_chain_id: int = Field(..., description="Source chain ID")
    dest_chain_id: int = Field(..., description="Destination chain ID")
    token: str = Field(default="USDC")
    amount: str = Field(..., description="Amount in USD (e.g., '100.00')")
    wallet_id: str = Field(..., description="Sardis wallet ID to sign from")


class BridgeExecuteResponse(BaseModel):
    bridge_id: str
    provider: str
    status: str
    source_tx_hash: str | None = None
    destination_tx_hash: str | None = None
    source_chain_id: int
    dest_chain_id: int
    input_amount: str
    output_amount: str


class BridgeStatusResponse(BaseModel):
    request_id: str
    status: str
    source_tx_hash: str | None = None
    destination_tx_hash: str | None = None
    raw: dict | None = None


class BridgeChainInfo(BaseModel):
    chain_id: int
    name: str
    usdc_address: str


class BridgeChainsResponse(BaseModel):
    chains: list[BridgeChainInfo]


# ── Dependencies ──────────────────────────────────────────────────────


class BridgeDependencies:
    def __init__(
        self,
        wallet_repo: WalletRepository,
        chain_executor: ChainExecutor | None = None,
    ):
        self.wallet_repo = wallet_repo
        self.chain_executor = chain_executor


def get_deps() -> BridgeDependencies:
    raise NotImplementedError("Dependency override required")


# ── Helpers ───────────────────────────────────────────────────────────


def _chain_id_to_sardis_name(chain_id: int) -> str:
    """Map a numeric chain ID to the Sardis internal chain name."""
    for name, cfg in CHAIN_CONFIGS.items():
        if cfg.get("chain_id") == chain_id:
            return name
    return CHAIN_NAMES.get(chain_id, "unknown")


def _format_usdc(amount_minor: int) -> str:
    """Format minor-unit USDC amount as human-readable USD string."""
    return f"{amount_minor / 1_000_000:.6f}"


async def _resolve_wallet_address(
    wallet_id: str,
    deps: BridgeDependencies,
    principal: Principal,
) -> str:
    """Resolve wallet_id to an on-chain address, with access check."""
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    address = getattr(wallet, "chain_address", None) or getattr(wallet, "address", None)
    if not address and deps.chain_executor and deps.chain_executor._mpc_signer:
        try:
            address = await deps.chain_executor._mpc_signer.get_address(wallet_id, "base")
        except Exception:
            pass

    if not address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Wallet has no on-chain address. Fund the wallet first.",
        )
    return address


def _make_sign_and_send(
    chain_executor: ChainExecutor,
    wallet_id: str,
):
    """Build a ``sign_and_send`` callable bound to a specific wallet.

    Returns an async function ``(to, data, value, chain_id) -> tx_hash``
    that uses the ChainExecutor's MPC signer to sign and broadcast.
    """
    async def sign_and_send(to: str, data: str, value: int, chain_id: int) -> str:
        signer = chain_executor._mpc_signer
        if not signer:
            raise RuntimeError("No MPC signer available on chain executor")

        # Map chain_id to sardis chain name
        chain_name = _chain_id_to_sardis_name(chain_id)

        # Get nonce
        rpc = chain_executor._get_rpc_client(chain_name)
        await rpc.connect()

        # Resolve the signing address
        turnkey_wallet_id = os.getenv("SARDIS_TURNKEY_WALLET_ID", wallet_id)
        address = await signer.get_address(turnkey_wallet_id, chain_name)
        nonce = await rpc.get_transaction_count(address)

        # Get gas estimates
        gas_limit = 200_000  # Safe default for bridge approve/deposit txs
        try:
            gas_estimate = await rpc._call(
                "eth_estimateGas",
                [{
                    "from": address,
                    "to": to,
                    "data": data,
                    "value": hex(value),
                }],
            )
            gas_limit = int(int(gas_estimate, 16) * 1.3)  # 30% buffer
        except Exception as e:
            logger.warning("Gas estimation failed, using default: %s", e)

        # Get current gas prices
        max_fee = 50_000_000_000  # 50 gwei default
        max_priority_fee = 1_500_000_000  # 1.5 gwei default
        try:
            base_fee_hex = await rpc._call("eth_gasPrice", [])
            base_fee = int(base_fee_hex, 16)
            max_priority_fee = min(base_fee // 5, 3_000_000_000)
            max_fee = base_fee * 2 + max_priority_fee
        except Exception:
            pass

        # Convert data to bytes
        data_bytes = bytes.fromhex(data[2:]) if data.startswith("0x") else bytes.fromhex(data) if data else b""

        tx_request = TransactionRequest(
            chain=chain_name,
            to_address=to,
            value=value,
            data=data_bytes,
            gas_limit=gas_limit,
            max_fee_per_gas=max_fee,
            max_priority_fee_per_gas=max_priority_fee,
            nonce=nonce,
        )

        signed_tx = await signer.sign_transaction(turnkey_wallet_id, tx_request)
        tx_hash = await rpc.send_raw_transaction(signed_tx)
        logger.info("Bridge tx broadcast: %s on chain %s", tx_hash, chain_name)
        return tx_hash

    return sign_and_send


# ── Endpoints ─────────────────────────────────────────────────────────


@router.post("/quote", response_model=BridgeQuoteResponse)
async def get_bridge_quote(
    request: BridgeQuoteRequest,
    deps: BridgeDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Get a bridge quote for cross-chain USDC transfer."""
    from decimal import Decimal

    address = await _resolve_wallet_address(request.wallet_id, deps, principal)

    bridge = CrossChainBridge(preferred_provider=BridgeProvider.RELAY)
    quote = await bridge.get_quote(
        source_chain_id=request.source_chain_id,
        destination_chain_id=request.dest_chain_id,
        token=request.token,
        amount_usd=Decimal(request.amount),
        sender=address,
        recipient=address,
    )

    return BridgeQuoteResponse(
        quote_id=quote.quote_id,
        provider=quote.provider.value,
        source_chain_id=quote.source_chain_id,
        source_chain_name=CHAIN_NAMES.get(quote.source_chain_id, "unknown"),
        dest_chain_id=quote.destination_chain_id,
        dest_chain_name=CHAIN_NAMES.get(quote.destination_chain_id, "unknown"),
        source_token=quote.source_token,
        dest_token=quote.destination_token,
        input_amount=_format_usdc(quote.input_amount),
        output_amount=_format_usdc(quote.output_amount),
        fee_amount=_format_usdc(quote.fee_amount),
        fee_usd=f"${quote.fee_amount / 1_000_000:.4f}",
        estimated_time_seconds=quote.estimated_time_seconds,
        sender=quote.sender,
        recipient=quote.recipient,
    )


@router.post("/execute", response_model=BridgeExecuteResponse)
async def execute_bridge(
    request: BridgeExecuteRequest,
    deps: BridgeDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    """Execute a cross-chain bridge transfer.

    1. Resolves wallet address
    2. Fetches fresh quote from Relay
    3. Signs each step via MPC signer
    4. Broadcasts and polls for completion
    """
    from decimal import Decimal

    if not deps.chain_executor:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Chain executor not available",
        )

    if not deps.chain_executor._mpc_signer:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="MPC signer not configured",
        )

    address = await _resolve_wallet_address(request.wallet_id, deps, principal)

    # Get a fresh quote (quotes are short-lived)
    bridge = CrossChainBridge(preferred_provider=BridgeProvider.RELAY)
    quote = await bridge.get_quote(
        source_chain_id=request.source_chain_id,
        destination_chain_id=request.dest_chain_id,
        token=request.token,
        amount_usd=Decimal(request.amount),
        sender=address,
        recipient=address,
    )

    if not quote.tx_data or not quote.tx_data.get("steps"):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Bridge provider returned no executable steps. Try again.",
        )

    sign_and_send = _make_sign_and_send(deps.chain_executor, request.wallet_id)

    try:
        result = await bridge.execute(quote, sign_and_send=sign_and_send)
    except Exception as e:
        logger.error("Bridge execution failed: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Bridge execution failed: {e}",
        )

    return BridgeExecuteResponse(
        bridge_id=result.bridge_id,
        provider=result.provider.value,
        status=result.status,
        source_tx_hash=result.source_tx_hash,
        destination_tx_hash=result.destination_tx_hash,
        source_chain_id=result.source_chain_id,
        dest_chain_id=result.destination_chain_id,
        input_amount=_format_usdc(result.input_amount),
        output_amount=_format_usdc(result.output_amount),
    )


@router.get("/status/{request_id}", response_model=BridgeStatusResponse)
async def get_bridge_status(
    request_id: str,
    principal: Principal = Depends(require_principal),
):
    """Poll bridge transfer status by Relay request ID."""
    bridge = CrossChainBridge(preferred_provider=BridgeProvider.RELAY)

    try:
        data = await bridge.poll_relay_status(request_id, max_polls=1, interval=0)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to fetch bridge status: {e}",
        )

    source_tx_hash = None
    dest_tx_hash = None
    for step in data.get("steps", []):
        for item in step.get("items", []):
            if item.get("txHash"):
                source_tx_hash = source_tx_hash or item["txHash"]
            if item.get("destinationTxHash"):
                dest_tx_hash = item["destinationTxHash"]

    return BridgeStatusResponse(
        request_id=request_id,
        status=data.get("status", "unknown"),
        source_tx_hash=source_tx_hash,
        destination_tx_hash=dest_tx_hash,
        raw=data,
    )


@router.get("/chains", response_model=BridgeChainsResponse)
async def list_bridge_chains(
    principal: Principal = Depends(require_principal),
):
    """List supported chains for bridging with their USDC addresses."""
    chains = []
    for chain_id, usdc_address in sorted(USDC_ADDRESSES.items()):
        name = CHAIN_NAMES.get(chain_id, f"chain_{chain_id}")
        chains.append(BridgeChainInfo(
            chain_id=chain_id,
            name=name,
            usdc_address=usdc_address,
        ))
    return BridgeChainsResponse(chains=chains)

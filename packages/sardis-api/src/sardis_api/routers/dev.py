"""Dev/testnet utility endpoints.

Provides:
- Testnet faucet: Send testnet USDC from a funded EOA to any address
- Only available in non-production environments
- Gated by SARDIS_EOA_PRIVATE_KEY env var
"""
from __future__ import annotations

import logging
import os
from decimal import Decimal
from typing import Optional

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from sardis_chain.executor import (
    CHAIN_CONFIGS,
    STABLECOIN_ADDRESSES,
    ChainRPCClient,
    encode_erc20_transfer,
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Testnet chain names
TESTNET_CHAINS = {
    "base_sepolia",
    "polygon_amoy",
    "ethereum_sepolia",
    "arbitrum_sepolia",
    "optimism_sepolia",
}

# Max faucet amount per request (100 USDC)
MAX_FAUCET_AMOUNT = Decimal("100")

# Default faucet amount (10 USDC)
DEFAULT_FAUCET_AMOUNT = Decimal("10")

# USDC has 6 decimals
USDC_DECIMALS = 6


class FaucetRequest(BaseModel):
    """Request to receive testnet tokens from the faucet."""
    wallet_address: str = Field(..., description="Destination wallet address (0x...)")
    chain: str = Field(default="base_sepolia", description="Testnet chain name")
    token: str = Field(default="USDC", description="Token symbol (USDC)")
    amount: Decimal = Field(default=DEFAULT_FAUCET_AMOUNT, description="Amount in token units (max 100)")


class FaucetResponse(BaseModel):
    """Faucet transaction response."""
    success: bool
    tx_hash: str
    chain: str
    token: str
    amount: str
    destination: str
    explorer_url: str


@router.post("/faucet", response_model=FaucetResponse)
async def dev_faucet(req: FaucetRequest):
    """
    Send testnet tokens from the Sardis faucet EOA to a wallet address.

    Requirements:
    - SARDIS_EOA_PRIVATE_KEY must be set (funded testnet EOA)
    - Only testnet chains are supported
    - Max 100 USDC per request
    - Not available in production
    """
    # Gate: block in production
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").lower()
    if env in ("prod", "production"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Faucet is not available in production",
        )

    # Gate: require EOA private key
    eoa_private_key = os.getenv("SARDIS_EOA_PRIVATE_KEY", "")
    if not eoa_private_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Faucet not configured: SARDIS_EOA_PRIVATE_KEY not set",
        )

    # Validate: testnet only
    if req.chain not in TESTNET_CHAINS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Faucet only works on testnets: {', '.join(sorted(TESTNET_CHAINS))}",
        )

    # Validate: chain exists
    chain_config = CHAIN_CONFIGS.get(req.chain)
    if not chain_config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown chain: {req.chain}",
        )

    # Validate: token supported on chain
    token_addresses = STABLECOIN_ADDRESSES.get(req.chain, {})
    token_address = token_addresses.get(req.token.upper())
    if not token_address:
        supported = list(token_addresses.keys()) or ["none"]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Token {req.token} not available on {req.chain}. Supported: {', '.join(supported)}",
        )

    # Validate: amount
    if req.amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be positive",
        )
    if req.amount > MAX_FAUCET_AMOUNT:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Max faucet amount is {MAX_FAUCET_AMOUNT} per request",
        )

    # Validate: wallet address format
    if not req.wallet_address.startswith("0x") or len(req.wallet_address) != 42:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid wallet address format (expected 0x... with 42 chars)",
        )

    # Convert amount to minor units (6 decimals for USDC)
    amount_minor = int(req.amount * (10**USDC_DECIMALS))

    try:
        tx_hash = await _send_faucet_tokens(
            private_key=eoa_private_key,
            chain=req.chain,
            token_address=token_address,
            destination=req.wallet_address,
            amount_minor=amount_minor,
        )
    except Exception as exc:
        logger.error(f"Faucet transfer failed: {exc}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Faucet transfer failed: {exc}",
        ) from exc

    explorer = chain_config.get("explorer", "")
    explorer_url = f"{explorer}/tx/{tx_hash}" if explorer else ""

    logger.info(
        f"Faucet: sent {req.amount} {req.token} to {req.wallet_address} "
        f"on {req.chain} (tx: {tx_hash})"
    )

    return FaucetResponse(
        success=True,
        tx_hash=tx_hash,
        chain=req.chain,
        token=req.token.upper(),
        amount=str(req.amount),
        destination=req.wallet_address,
        explorer_url=explorer_url,
    )


@router.get("/faucet/status")
async def faucet_status():
    """Check faucet availability and EOA balance."""
    env = os.getenv("SARDIS_ENVIRONMENT", "dev").lower()
    if env in ("prod", "production"):
        return {"available": False, "reason": "Not available in production"}

    eoa_private_key = os.getenv("SARDIS_EOA_PRIVATE_KEY", "")
    if not eoa_private_key:
        return {"available": False, "reason": "SARDIS_EOA_PRIVATE_KEY not set"}

    # Get EOA address
    try:
        from eth_account import Account
        account = Account.from_key(eoa_private_key)
        eoa_address = account.address
    except Exception as exc:
        return {"available": False, "reason": f"Invalid private key: {exc}"}

    # Check balances on supported testnet chains
    balances = {}
    for chain_name in sorted(TESTNET_CHAINS):
        chain_config = CHAIN_CONFIGS.get(chain_name)
        if not chain_config:
            continue

        token_addresses = STABLECOIN_ADDRESSES.get(chain_name, {})
        chain_balances = {}

        try:
            rpc = ChainRPCClient(chain_config["rpc_url"], chain=chain_name)

            # ETH balance for gas
            eth_balance_wei = await rpc.get_balance(eoa_address)
            chain_balances["ETH"] = str(Decimal(eth_balance_wei) / Decimal(10**18))

            # Token balances
            for token_symbol, token_addr in token_addresses.items():
                try:
                    token_balance = await _get_erc20_balance(rpc, token_addr, eoa_address)
                    chain_balances[token_symbol] = str(Decimal(token_balance) / Decimal(10**USDC_DECIMALS))
                except Exception:
                    chain_balances[token_symbol] = "error"

            balances[chain_name] = chain_balances
        except Exception as exc:
            balances[chain_name] = {"error": str(exc)}

    return {
        "available": True,
        "eoa_address": eoa_address,
        "supported_chains": sorted(TESTNET_CHAINS),
        "max_amount_per_request": str(MAX_FAUCET_AMOUNT),
        "balances": balances,
    }


async def _get_erc20_balance(rpc: ChainRPCClient, token_address: str, owner: str) -> int:
    """Read ERC-20 balanceOf for an address."""
    # balanceOf(address) selector: 0x70a08231
    selector = "70a08231"
    padded_owner = owner[2:].lower().zfill(64)
    data = f"0x{selector}{padded_owner}"

    result = await rpc._call("eth_call", [{"to": token_address, "data": data}, "latest"])
    return int(result, 16)


async def _send_faucet_tokens(
    private_key: str,
    chain: str,
    token_address: str,
    destination: str,
    amount_minor: int,
) -> str:
    """Sign and send an ERC-20 transfer from the faucet EOA."""
    from eth_account import Account
    from web3 import Web3

    w3 = Web3()
    account = Account.from_key(private_key)
    sender = account.address

    chain_config = CHAIN_CONFIGS[chain]
    chain_id = chain_config["chain_id"]
    rpc = ChainRPCClient(chain_config["rpc_url"], chain=chain)

    # Get nonce
    nonce = await rpc.get_nonce(sender)

    # Encode ERC-20 transfer calldata
    transfer_data = encode_erc20_transfer(destination, amount_minor)

    # Build tx params for gas estimation
    tx_params = {
        "from": sender,
        "to": token_address,
        "data": "0x" + transfer_data.hex(),
        "value": "0x0",
    }

    # Estimate gas
    try:
        gas_limit = await rpc.estimate_gas(tx_params)
        gas_limit = int(gas_limit * 1.3)  # 30% buffer for safety
    except Exception as exc:
        logger.warning(f"Gas estimation failed, using default: {exc}")
        gas_limit = 120_000

    # Get gas prices
    gas_price = await rpc.get_gas_price()
    max_priority_fee = await rpc.get_max_priority_fee()
    max_fee = gas_price + max_priority_fee

    # Build and sign EIP-1559 transaction
    tx_dict = {
        "to": token_address,
        "value": 0,
        "data": transfer_data,
        "gas": gas_limit,
        "maxFeePerGas": max_fee,
        "maxPriorityFeePerGas": max_priority_fee,
        "nonce": nonce,
        "chainId": chain_id,
        "type": 2,
    }

    signed = w3.eth.account.sign_transaction(tx_dict, account.key)
    raw_tx = signed.raw_transaction.hex()

    # Broadcast
    tx_hash = await rpc.send_raw_transaction(raw_tx)

    logger.info(
        f"Faucet tx broadcast: {tx_hash} | {sender} -> {destination} | "
        f"amount_minor={amount_minor} | chain={chain}"
    )

    return tx_hash

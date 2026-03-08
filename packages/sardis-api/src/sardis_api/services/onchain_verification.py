"""On-chain USDC transfer verification for external wallet checkout.

Verifies that a submitted tx_hash corresponds to a real, successful
USDC transfer with the correct recipient and amount before marking
a checkout session as paid.
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

import httpx

from sardis_v2_core.tokens import TOKEN_REGISTRY, TokenType

logger = logging.getLogger(__name__)

# ERC-20 Transfer(address,address,uint256) event topic0
TRANSFER_EVENT_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

# Chain name → USDC contract address
_USDC_ADDRESSES: dict[str, str] = {
    chain: addr.lower()
    for chain, addr in TOKEN_REGISTRY[TokenType.USDC].contract_addresses.items()
}


@dataclass
class VerificationResult:
    """Result of on-chain transfer verification."""
    verified: bool
    error: Optional[str] = None
    block_number: Optional[int] = None
    actual_amount: Optional[Decimal] = None


def _get_rpc_url(chain: str = "base") -> str:
    """Resolve RPC URL for the given chain."""
    # Try chain-specific env var first, then generic fallback
    chain_upper = chain.upper().replace("-", "_")
    url = (
        os.getenv(f"SARDIS_{chain_upper}_RPC_URL")
        or os.getenv("SARDIS_BASE_RPC_URL")
        or ""
    )
    if not url:
        # Public fallback (rate-limited, not for production)
        if chain in ("base", "base_mainnet"):
            url = "https://mainnet.base.org"
        elif chain == "base_sepolia":
            url = "https://sepolia.base.org"
    return url


def _get_usdc_address(chain: str = "base") -> str:
    """Get USDC contract address for chain."""
    return _USDC_ADDRESSES.get(chain, "")


async def verify_usdc_transfer(
    tx_hash: str,
    expected_recipient: str,
    expected_amount: Decimal,
    chain: str = "base",
    min_confirmations: int = 1,
) -> VerificationResult:
    """Verify an on-chain USDC transfer matches expected parameters.

    Steps:
    1. Fetch tx receipt via eth_getTransactionReceipt
    2. Verify tx succeeded (status == 0x1)
    3. Check confirmation count >= min_confirmations
    4. Parse Transfer event logs
    5. Verify recipient and exact amount match

    Args:
        tx_hash: Transaction hash to verify
        expected_recipient: Expected 'to' address (merchant settlement)
        expected_amount: Expected USDC amount (human-readable, 6 decimals)
        chain: Chain to verify on (default: base)
        min_confirmations: Minimum block confirmations required (default: 1)

    Returns:
        VerificationResult with verification outcome
    """
    rpc_url = _get_rpc_url(chain)
    if not rpc_url:
        return VerificationResult(
            verified=False,
            error=f"No RPC URL configured for chain '{chain}'",
        )

    usdc_address = _get_usdc_address(chain)
    if not usdc_address:
        return VerificationResult(
            verified=False,
            error=f"USDC contract address not found for chain '{chain}'",
        )

    # Normalize addresses to lowercase for comparison
    expected_recipient_lower = expected_recipient.lower()

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Fetch receipt and latest block number in parallel
            receipt_resp, block_resp = await asyncio.gather(
                client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": "eth_getTransactionReceipt",
                        "params": [tx_hash],
                    },
                ),
                client.post(
                    rpc_url,
                    json={
                        "jsonrpc": "2.0",
                        "id": 2,
                        "method": "eth_blockNumber",
                        "params": [],
                    },
                ),
            )
            data = receipt_resp.json()
            block_data = block_resp.json()
    except (httpx.HTTPError, ValueError) as e:
        logger.error("RPC call failed for tx %s: %s", tx_hash, e)
        return VerificationResult(verified=False, error=f"RPC error: {e}")

    if "error" in data:
        return VerificationResult(
            verified=False,
            error=f"RPC error: {data['error'].get('message', 'unknown')}",
        )

    receipt = data.get("result")
    if not receipt:
        return VerificationResult(verified=False, error="Transaction not found")

    # Check tx status (0x1 = success)
    tx_status = receipt.get("status", "0x0")
    if tx_status != "0x1":
        return VerificationResult(verified=False, error="Transaction reverted")

    block_number = int(receipt.get("blockNumber", "0x0"), 16) if receipt.get("blockNumber") else None

    # Check confirmation count
    if min_confirmations > 0 and block_number is not None:
        latest_block = int(block_data.get("result", "0x0"), 16) if block_data.get("result") else 0
        confirmations = latest_block - block_number
        if confirmations < min_confirmations:
            return VerificationResult(
                verified=False,
                error=f"Insufficient confirmations: {confirmations} < {min_confirmations}",
                block_number=block_number,
            )

    # Parse Transfer event logs
    logs = receipt.get("logs", [])
    expected_amount_raw = int(expected_amount * Decimal("1000000"))  # USDC has 6 decimals

    for log in logs:
        # Check topic0 is Transfer event
        topics = log.get("topics", [])
        if not topics or topics[0] != TRANSFER_EVENT_TOPIC:
            continue

        # Check log is from USDC contract
        log_address = (log.get("address") or "").lower()
        if log_address != usdc_address:
            continue

        # Decode Transfer event: topic1=from, topic2=to, data=amount
        if len(topics) < 3:
            continue

        # topic2 is the 'to' address (zero-padded to 32 bytes)
        to_address = "0x" + topics[2][-40:]
        if to_address.lower() != expected_recipient_lower:
            continue

        # Decode amount from log data
        log_data = log.get("data", "0x0")
        actual_amount_raw = int(log_data, 16)
        actual_amount = Decimal(actual_amount_raw) / Decimal("1000000")

        # Exact amount match required (no overpayment acceptance)
        if actual_amount_raw != expected_amount_raw:
            return VerificationResult(
                verified=False,
                error=f"Transfer amount {actual_amount} USDC does not match expected {expected_amount} USDC",
                block_number=block_number,
                actual_amount=actual_amount,
            )

        # All checks passed
        logger.info(
            "On-chain verification passed: tx=%s amount=%s to=%s block=%s",
            tx_hash, actual_amount, to_address, block_number,
        )
        return VerificationResult(
            verified=True,
            block_number=block_number,
            actual_amount=actual_amount,
        )

    # No matching Transfer event found
    return VerificationResult(
        verified=False,
        error="No matching USDC Transfer event found in transaction logs",
        block_number=block_number,
    )

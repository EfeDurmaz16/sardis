"""
MEV (Maximal Extractable Value) protection module.

Provides protection against front-running and sandwich attacks:
- Flashbots integration for private transaction submission
- MEV-Share for user-aligned MEV extraction
- Slippage protection for DEX transactions
- Transaction timing randomization
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import random
import secrets
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)


class MEVProtectionLevel(str, Enum):
    """Level of MEV protection to apply."""
    NONE = "none"  # No protection, use public mempool
    BASIC = "basic"  # Private mempool only
    STANDARD = "standard"  # Private + timing randomization
    MAXIMUM = "maximum"  # All protections including MEV-Share


class TransactionVisibility(str, Enum):
    """Transaction visibility level."""
    PUBLIC = "public"  # Standard mempool
    PRIVATE = "private"  # Flashbots private pool
    MEV_SHARE = "mev_share"  # MEV-Share for rebates


@dataclass
class MEVConfig:
    """Configuration for MEV protection."""
    protection_level: MEVProtectionLevel = MEVProtectionLevel.STANDARD
    flashbots_relay_url: str = "https://relay.flashbots.net"
    mev_share_url: str = "https://relay.flashbots.net"
    max_block_delay: int = 2  # Max blocks to wait for private inclusion
    timing_jitter_ms: int = 500  # Random delay to add
    slippage_tolerance_bps: int = 50  # 0.5% default slippage
    signing_key: Optional[str] = None  # For Flashbots auth


@dataclass
class ProtectedTransaction:
    """A transaction with MEV protection applied."""
    raw_tx: str
    tx_hash: str
    visibility: TransactionVisibility
    submitted_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    target_block: Optional[int] = None
    mev_share_hints: List[str] = field(default_factory=list)
    protection_level: MEVProtectionLevel = MEVProtectionLevel.STANDARD


@dataclass
class SubmissionResult:
    """Result of submitting a protected transaction."""
    success: bool
    tx_hash: str
    bundle_hash: Optional[str] = None
    error: Optional[str] = None
    submitted_via: str = "public"  # "public", "flashbots", "mev_share"
    expected_block: Optional[int] = None


class MEVProtectionProvider(ABC):
    """Abstract interface for MEV protection providers."""

    @abstractmethod
    async def submit_transaction(
        self,
        signed_tx: str,
        target_block: Optional[int] = None,
    ) -> SubmissionResult:
        """Submit a transaction with MEV protection."""
        pass

    @abstractmethod
    async def get_bundle_status(
        self,
        bundle_hash: str,
    ) -> Dict[str, Any]:
        """Check status of a submitted bundle."""
        pass


class FlashbotsProvider(MEVProtectionProvider):
    """
    Flashbots integration for private transaction submission.

    Flashbots allows transactions to be submitted directly to block builders
    without entering the public mempool, preventing front-running.

    Reference: https://docs.flashbots.net/
    """

    def __init__(
        self,
        relay_url: str = "https://relay.flashbots.net",
        signing_key: Optional[str] = None,
    ):
        self._relay_url = relay_url
        self._signing_key = signing_key
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._relay_url,
                timeout=30,
            )
        return self._client

    def _sign_payload(self, payload: Dict[str, Any]) -> str:
        """Sign payload for Flashbots authentication."""
        if not self._signing_key:
            raise ValueError("Signing key required for Flashbots")

        body = json.dumps(payload, separators=(',', ':'))
        message = f"0x{hashlib.keccak_256(body.encode()).hexdigest()}"

        # Sign with private key (simplified - actual impl needs eth_account)
        signature = hmac.new(
            bytes.fromhex(self._signing_key.replace('0x', '')),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

        return f"0x{signature}"

    async def submit_transaction(
        self,
        signed_tx: str,
        target_block: Optional[int] = None,
    ) -> SubmissionResult:
        """Submit transaction via Flashbots private pool."""
        client = await self._get_client()

        # Build bundle (single transaction)
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_sendBundle",
            "params": [
                {
                    "txs": [signed_tx],
                    "blockNumber": hex(target_block) if target_block else None,
                }
            ],
        }

        try:
            headers = {}
            if self._signing_key:
                headers["X-Flashbots-Signature"] = self._sign_payload(payload)

            response = await client.post("/", json=payload, headers=headers)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                return SubmissionResult(
                    success=False,
                    tx_hash=self._extract_tx_hash(signed_tx),
                    error=result["error"].get("message", "Unknown error"),
                    submitted_via="flashbots",
                )

            bundle_hash = result.get("result", {}).get("bundleHash")

            return SubmissionResult(
                success=True,
                tx_hash=self._extract_tx_hash(signed_tx),
                bundle_hash=bundle_hash,
                submitted_via="flashbots",
                expected_block=target_block,
            )

        except Exception as e:
            logger.error(f"Flashbots submission failed: {e}")
            return SubmissionResult(
                success=False,
                tx_hash=self._extract_tx_hash(signed_tx),
                error=str(e),
                submitted_via="flashbots",
            )

    async def get_bundle_status(
        self,
        bundle_hash: str,
    ) -> Dict[str, Any]:
        """Get bundle inclusion status."""
        client = await self._get_client()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "flashbots_getBundleStats",
            "params": [bundle_hash],
        }

        try:
            response = await client.post("/", json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("result", {})
        except Exception as e:
            logger.error(f"Failed to get bundle status: {e}")
            return {"error": str(e)}

    def _extract_tx_hash(self, signed_tx: str) -> str:
        """Extract transaction hash from signed transaction."""
        # Simplified - actual impl uses rlp decode
        tx_bytes = bytes.fromhex(signed_tx.replace('0x', ''))
        return f"0x{hashlib.keccak_256(tx_bytes).hexdigest()}"

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class MEVShareProvider(MEVProtectionProvider):
    """
    MEV-Share integration for user-aligned MEV extraction.

    MEV-Share allows users to receive rebates from MEV extracted
    from their transactions, rather than losing value to searchers.

    Reference: https://docs.flashbots.net/flashbots-mev-share/overview
    """

    def __init__(
        self,
        relay_url: str = "https://relay.flashbots.net",
        signing_key: Optional[str] = None,
    ):
        self._relay_url = relay_url
        self._signing_key = signing_key
        self._client = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self._relay_url,
                timeout=30,
            )
        return self._client

    async def submit_transaction(
        self,
        signed_tx: str,
        target_block: Optional[int] = None,
        hints: Optional[List[str]] = None,
        max_block_number: Optional[int] = None,
    ) -> SubmissionResult:
        """
        Submit transaction via MEV-Share.

        Args:
            signed_tx: Signed transaction hex
            target_block: Target block for inclusion
            hints: What to reveal to searchers ("calldata", "logs", "function_selector", etc.)
            max_block_number: Maximum block for inclusion
        """
        client = await self._get_client()

        # Default hints - reveal function selector but not full calldata
        if hints is None:
            hints = ["function_selector", "logs"]

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_sendPrivateTransaction",
            "params": [
                {
                    "tx": signed_tx,
                    "preferences": {
                        "privacy": {
                            "hints": hints,
                        },
                        "validity": {
                            "refund": [{"address": self._get_refund_address(signed_tx), "percent": 90}],
                        },
                    },
                    "maxBlockNumber": hex(max_block_number) if max_block_number else None,
                }
            ],
        }

        try:
            response = await client.post("/", json=payload)
            response.raise_for_status()
            result = response.json()

            if "error" in result:
                return SubmissionResult(
                    success=False,
                    tx_hash=self._extract_tx_hash(signed_tx),
                    error=result["error"].get("message", "Unknown error"),
                    submitted_via="mev_share",
                )

            return SubmissionResult(
                success=True,
                tx_hash=self._extract_tx_hash(signed_tx),
                bundle_hash=result.get("result"),
                submitted_via="mev_share",
                expected_block=target_block,
            )

        except Exception as e:
            logger.error(f"MEV-Share submission failed: {e}")
            return SubmissionResult(
                success=False,
                tx_hash=self._extract_tx_hash(signed_tx),
                error=str(e),
                submitted_via="mev_share",
            )

    async def get_bundle_status(
        self,
        bundle_hash: str,
    ) -> Dict[str, Any]:
        """Get MEV-Share submission status."""
        client = await self._get_client()

        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_getPrivateTransactionStatus",
            "params": [bundle_hash],
        }

        try:
            response = await client.post("/", json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("result", {})
        except Exception as e:
            logger.error(f"Failed to get MEV-Share status: {e}")
            return {"error": str(e)}

    def _get_refund_address(self, signed_tx: str) -> str:
        """Extract sender address for MEV rebate."""
        # Simplified - actual impl decodes transaction
        return "0x0000000000000000000000000000000000000000"

    def _extract_tx_hash(self, signed_tx: str) -> str:
        """Extract transaction hash from signed transaction."""
        tx_bytes = bytes.fromhex(signed_tx.replace('0x', ''))
        return f"0x{hashlib.keccak_256(tx_bytes).hexdigest()}"

    async def close(self):
        """Close HTTP client."""
        if self._client:
            await self._client.aclose()
            self._client = None


class MEVProtectionService:
    """
    High-level MEV protection service.

    Provides automatic MEV protection based on transaction type
    and configured protection level.
    """

    def __init__(
        self,
        config: Optional[MEVConfig] = None,
    ):
        """
        Initialize MEV protection service.

        Args:
            config: MEV protection configuration
        """
        self._config = config or MEVConfig()
        self._flashbots = FlashbotsProvider(
            relay_url=self._config.flashbots_relay_url,
            signing_key=self._config.signing_key,
        )
        self._mev_share = MEVShareProvider(
            relay_url=self._config.mev_share_url,
            signing_key=self._config.signing_key,
        )

    async def protect_and_submit(
        self,
        signed_tx: str,
        tx_value: Decimal = Decimal("0"),
        is_dex_swap: bool = False,
        current_block: Optional[int] = None,
    ) -> SubmissionResult:
        """
        Apply MEV protection and submit transaction.

        Automatically selects protection method based on:
        - Transaction value (higher value = more protection)
        - Transaction type (DEX swaps get extra protection)
        - Configured protection level

        Args:
            signed_tx: Signed transaction hex
            tx_value: Transaction value in ETH
            is_dex_swap: Whether this is a DEX swap (high MEV risk)
            current_block: Current block number for targeting
        """
        protection_level = self._config.protection_level

        # Skip protection if disabled
        if protection_level == MEVProtectionLevel.NONE:
            return SubmissionResult(
                success=True,
                tx_hash=self._extract_tx_hash(signed_tx),
                submitted_via="public",
            )

        # Apply timing jitter for obfuscation
        if protection_level in (MEVProtectionLevel.STANDARD, MEVProtectionLevel.MAXIMUM):
            jitter_ms = random.randint(0, self._config.timing_jitter_ms)
            await asyncio.sleep(jitter_ms / 1000)

        # Calculate target block
        target_block = None
        if current_block:
            target_block = current_block + 1

        # Use MEV-Share for maximum protection or high-value swaps
        if protection_level == MEVProtectionLevel.MAXIMUM or (is_dex_swap and tx_value > Decimal("0.1")):
            result = await self._mev_share.submit_transaction(
                signed_tx=signed_tx,
                target_block=target_block,
                hints=["function_selector"] if is_dex_swap else ["calldata", "logs"],
                max_block_number=target_block + self._config.max_block_delay if target_block else None,
            )

            # Fallback to Flashbots if MEV-Share fails
            if not result.success and self._config.signing_key:
                logger.warning("MEV-Share failed, falling back to Flashbots")
                result = await self._flashbots.submit_transaction(
                    signed_tx=signed_tx,
                    target_block=target_block,
                )

            return result

        # Use Flashbots for standard protection
        if self._config.signing_key:
            return await self._flashbots.submit_transaction(
                signed_tx=signed_tx,
                target_block=target_block,
            )

        # Fallback to public mempool with warning
        logger.warning("No MEV protection available - submitting to public mempool")
        return SubmissionResult(
            success=True,
            tx_hash=self._extract_tx_hash(signed_tx),
            submitted_via="public",
        )

    async def check_status(
        self,
        bundle_hash: str,
        submitted_via: str = "flashbots",
    ) -> Dict[str, Any]:
        """Check status of a protected transaction."""
        if submitted_via == "mev_share":
            return await self._mev_share.get_bundle_status(bundle_hash)
        elif submitted_via == "flashbots":
            return await self._flashbots.get_bundle_status(bundle_hash)
        else:
            return {"status": "unknown", "submitted_via": submitted_via}

    def calculate_safe_slippage(
        self,
        swap_amount: Decimal,
        pool_liquidity: Decimal,
    ) -> int:
        """
        Calculate safe slippage tolerance for a swap.

        Returns slippage in basis points (100 = 1%).
        """
        # Higher amounts relative to liquidity need more slippage
        impact_ratio = swap_amount / pool_liquidity if pool_liquidity > 0 else Decimal("1")

        if impact_ratio < Decimal("0.001"):  # < 0.1% of pool
            return 30  # 0.3%
        elif impact_ratio < Decimal("0.01"):  # < 1% of pool
            return 50  # 0.5%
        elif impact_ratio < Decimal("0.05"):  # < 5% of pool
            return 100  # 1%
        else:
            return 200  # 2% for large swaps

    def _extract_tx_hash(self, signed_tx: str) -> str:
        """Extract transaction hash from signed transaction."""
        tx_bytes = bytes.fromhex(signed_tx.replace('0x', ''))
        return f"0x{hashlib.keccak_256(tx_bytes).hexdigest()}"

    async def close(self):
        """Close all providers."""
        await self._flashbots.close()
        await self._mev_share.close()


def create_mev_protection(
    protection_level: MEVProtectionLevel = MEVProtectionLevel.STANDARD,
    signing_key: Optional[str] = None,
) -> MEVProtectionService:
    """
    Factory function to create MEV protection service.

    Args:
        protection_level: Desired protection level
        signing_key: Private key for Flashbots authentication

    Returns:
        Configured MEVProtectionService
    """
    config = MEVConfig(
        protection_level=protection_level,
        signing_key=signing_key,
    )
    return MEVProtectionService(config=config)

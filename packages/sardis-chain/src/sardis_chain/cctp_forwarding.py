"""Circle CCTP v2 Forwarding Service integration.

Enables "fund on any chain, arrive on Base" by generating deterministic
forwarding addresses. When USDC is sent to a forwarding address on any
supported chain, Circle's Forwarding Service automatically bridges it
to the destination chain (Base) and deposits into the agent's escrow.

Flow:
1. Create a forwarding address on source chain (e.g., Ethereum)
2. User sends USDC to that address
3. Circle detects the deposit and initiates CCTP transfer
4. USDC arrives on Base at the specified destination address
5. Sardis detects the deposit and credits the agent's escrow

Reference: https://developers.circle.com/circle-mint/docs/cctp-forwarding-service
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .cctp_constants import (
    CCTP_DOMAINS,
    USDC_ADDRESSES,
    get_cctp_domain,
    is_cctp_supported,
    get_bridge_estimate_seconds,
)

logger = logging.getLogger(__name__)

# Circle Forwarding Service API endpoints
FORWARDING_API_URL = "https://api.circle.com/v1/forwarding"
FORWARDING_API_SANDBOX_URL = "https://api-sandbox.circle.com/v1/forwarding"

# Chains that can serve as funding sources (all CCTP chains except Base itself)
FUNDING_SOURCE_CHAINS = [
    chain for chain in CCTP_DOMAINS
    if chain not in ("base", "arc_testnet")
]

# Default destination chain for Sardis
DEFAULT_DESTINATION_CHAIN = "base"


class ForwardingStatus(str, Enum):
    """Status of a forwarding address."""
    PENDING = "pending"
    ACTIVE = "active"
    DEPOSIT_DETECTED = "deposit_detected"
    BRIDGING = "bridging"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


@dataclass
class ForwardingAddress:
    """A CCTP forwarding address that auto-bridges USDC to Base."""
    forwarding_id: str = field(default_factory=lambda: f"fwd_{uuid.uuid4().hex[:16]}")
    source_chain: str = ""
    destination_chain: str = DEFAULT_DESTINATION_CHAIN
    forwarding_address: str = ""
    destination_address: str = ""
    wallet_id: str = ""
    agent_id: Optional[str] = None
    status: ForwardingStatus = ForwardingStatus.PENDING
    total_forwarded: Decimal = Decimal("0")
    last_deposit_amount: Optional[Decimal] = None
    circle_forwarding_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "forwarding_id": self.forwarding_id,
            "source_chain": self.source_chain,
            "destination_chain": self.destination_chain,
            "forwarding_address": self.forwarding_address,
            "destination_address": self.destination_address,
            "wallet_id": self.wallet_id,
            "agent_id": self.agent_id,
            "status": self.status.value,
            "total_forwarded": str(self.total_forwarded),
            "last_deposit_amount": str(self.last_deposit_amount) if self.last_deposit_amount else None,
            "circle_forwarding_id": self.circle_forwarding_id,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class ForwardingDeposit:
    """A deposit received on a forwarding address."""
    deposit_id: str = field(default_factory=lambda: f"fdep_{uuid.uuid4().hex[:16]}")
    forwarding_id: str = ""
    source_chain: str = ""
    destination_chain: str = DEFAULT_DESTINATION_CHAIN
    amount: Decimal = Decimal("0")
    source_tx_hash: str = ""
    destination_tx_hash: Optional[str] = None
    status: ForwardingStatus = ForwardingStatus.DEPOSIT_DETECTED
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "deposit_id": self.deposit_id,
            "forwarding_id": self.forwarding_id,
            "source_chain": self.source_chain,
            "destination_chain": self.destination_chain,
            "amount": str(self.amount),
            "source_tx_hash": self.source_tx_hash,
            "destination_tx_hash": self.destination_tx_hash,
            "status": self.status.value,
            "detected_at": self.detected_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class CCTPForwardingService:
    """Service for multi-chain USDC funding via Circle Forwarding Service.

    Creates deterministic forwarding addresses on source chains that
    automatically bridge USDC deposits to Base via CCTP v2.
    """

    def __init__(
        self,
        circle_api_key: str = "",
        *,
        sandbox: bool = True,
        destination_chain: str = DEFAULT_DESTINATION_CHAIN,
    ):
        self._api_key = circle_api_key
        self._sandbox = sandbox
        self._destination_chain = destination_chain
        self._api_url = FORWARDING_API_SANDBOX_URL if sandbox else FORWARDING_API_URL
        self._forwarding_addresses: dict[str, ForwardingAddress] = {}
        self._deposits: dict[str, ForwardingDeposit] = {}

    @property
    def supported_funding_chains(self) -> list[str]:
        """Chains that can fund an agent's Base wallet."""
        return FUNDING_SOURCE_CHAINS

    async def create_forwarding_address(
        self,
        source_chain: str,
        destination_address: str,
        wallet_id: str,
        agent_id: Optional[str] = None,
    ) -> ForwardingAddress:
        """Create a forwarding address on source_chain that auto-bridges to Base.

        Args:
            source_chain: Chain to create forwarding address on (e.g., "ethereum")
            destination_address: Base address to receive funds (0x...)
            wallet_id: Sardis wallet ID for tracking
            agent_id: Optional agent ID

        Returns:
            ForwardingAddress with the generated address

        Raises:
            ValueError: If source chain is invalid or same as destination
        """
        if not is_cctp_supported(source_chain):
            raise ValueError(f"Source chain '{source_chain}' not supported by CCTP")
        if source_chain == self._destination_chain:
            raise ValueError(
                f"Source chain cannot be the destination chain ({self._destination_chain}). "
                "Send USDC directly instead."
            )

        fwd = ForwardingAddress(
            source_chain=source_chain,
            destination_chain=self._destination_chain,
            destination_address=destination_address,
            wallet_id=wallet_id,
            agent_id=agent_id,
        )

        source_domain = get_cctp_domain(source_chain)
        dest_domain = get_cctp_domain(self._destination_chain)

        if not self._api_key:
            # Simulated mode — generate a deterministic pseudo-address
            import hashlib
            seed = f"{source_chain}:{destination_address}:{wallet_id}".encode()
            pseudo_addr = "0x" + hashlib.sha256(seed).hexdigest()[:40]
            fwd.forwarding_address = pseudo_addr
            fwd.status = ForwardingStatus.ACTIVE
            logger.info(
                "[SIMULATED] Forwarding address created: %s on %s -> %s on %s",
                pseudo_addr, source_chain, destination_address, self._destination_chain,
            )
            self._forwarding_addresses[fwd.forwarding_id] = fwd
            return fwd

        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                payload = {
                    "idempotencyKey": fwd.forwarding_id,
                    "sourceChain": source_chain.upper(),
                    "destinationChain": self._destination_chain.upper(),
                    "sourceDomain": source_domain,
                    "destinationDomain": dest_domain,
                    "destinationAddress": destination_address,
                    "currency": "USD",
                }
                headers = {
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                }
                async with session.post(
                    f"{self._api_url}/addresses",
                    json=payload,
                    headers=headers,
                ) as resp:
                    if resp.status in (200, 201):
                        data = await resp.json()
                        result = data.get("data", data)
                        fwd.forwarding_address = result.get("address", "")
                        fwd.circle_forwarding_id = result.get("id")
                        fwd.status = ForwardingStatus.ACTIVE
                        logger.info(
                            "Forwarding address created: %s on %s -> %s",
                            fwd.forwarding_address, source_chain, self._destination_chain,
                        )
                    else:
                        error_body = await resp.text()
                        fwd.status = ForwardingStatus.FAILED
                        fwd.error = f"Circle API error {resp.status}: {error_body}"
                        logger.error("Failed to create forwarding address: %s", fwd.error)

        except ImportError:
            fwd.status = ForwardingStatus.FAILED
            fwd.error = "aiohttp not available"
            logger.error("aiohttp required for Circle Forwarding Service API")
        except Exception as e:
            fwd.status = ForwardingStatus.FAILED
            fwd.error = str(e)
            logger.error("Error creating forwarding address: %s", e)

        self._forwarding_addresses[fwd.forwarding_id] = fwd
        return fwd

    async def create_all_funding_addresses(
        self,
        destination_address: str,
        wallet_id: str,
        agent_id: Optional[str] = None,
    ) -> dict[str, ForwardingAddress]:
        """Create forwarding addresses on ALL supported funding chains.

        This gives the agent a USDC deposit address on every chain,
        all auto-bridging to their Base wallet.

        Returns:
            Dict mapping chain name -> ForwardingAddress
        """
        results: dict[str, ForwardingAddress] = {}
        for chain in FUNDING_SOURCE_CHAINS:
            try:
                fwd = await self.create_forwarding_address(
                    source_chain=chain,
                    destination_address=destination_address,
                    wallet_id=wallet_id,
                    agent_id=agent_id,
                )
                results[chain] = fwd
            except Exception as e:
                logger.error("Failed to create forwarding address on %s: %s", chain, e)
                results[chain] = ForwardingAddress(
                    source_chain=chain,
                    destination_chain=self._destination_chain,
                    destination_address=destination_address,
                    wallet_id=wallet_id,
                    agent_id=agent_id,
                    status=ForwardingStatus.FAILED,
                    error=str(e),
                )
        return results

    async def get_forwarding_status(
        self,
        forwarding_id: str,
    ) -> Optional[ForwardingAddress]:
        """Get the current status of a forwarding address."""
        fwd = self._forwarding_addresses.get(forwarding_id)
        if fwd is None:
            return None

        # If we have a Circle ID, poll for updates
        if fwd.circle_forwarding_id and self._api_key:
            try:
                import aiohttp
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": f"Bearer {self._api_key}"}
                    async with session.get(
                        f"{self._api_url}/addresses/{fwd.circle_forwarding_id}",
                        headers=headers,
                    ) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            result = data.get("data", data)
                            api_status = result.get("status", "").lower()
                            if api_status == "active":
                                fwd.status = ForwardingStatus.ACTIVE
                            elif api_status == "expired":
                                fwd.status = ForwardingStatus.EXPIRED
            except Exception as e:
                logger.warning("Error polling forwarding status: %s", e)

        return fwd

    async def list_deposits(
        self,
        forwarding_id: str,
    ) -> list[ForwardingDeposit]:
        """List deposits received on a forwarding address."""
        return [
            d for d in self._deposits.values()
            if d.forwarding_id == forwarding_id
        ]

    def estimate_funding_time(self, source_chain: str) -> int:
        """Estimate time in seconds for USDC to arrive on Base from source chain."""
        return get_bridge_estimate_seconds(source_chain, self._destination_chain)

    def get_funding_instructions(
        self,
        forwarding_addresses: dict[str, ForwardingAddress],
    ) -> dict[str, dict]:
        """Generate user-friendly funding instructions for all chains.

        Returns:
            Dict mapping chain -> {address, token, estimated_time, usdc_contract}
        """
        instructions: dict[str, dict] = {}
        for chain, fwd in forwarding_addresses.items():
            if fwd.status != ForwardingStatus.ACTIVE:
                continue
            instructions[chain] = {
                "chain": chain,
                "deposit_address": fwd.forwarding_address,
                "token": "USDC",
                "usdc_contract": USDC_ADDRESSES.get(chain, ""),
                "estimated_arrival_seconds": self.estimate_funding_time(chain),
                "destination_chain": self._destination_chain,
                "destination_address": fwd.destination_address,
                "note": (
                    f"Send USDC on {chain.title()} to {fwd.forwarding_address}. "
                    f"It will automatically arrive on {self._destination_chain.title()} "
                    f"in ~{self.estimate_funding_time(chain) // 60} minutes."
                ),
            }
        return instructions


__all__ = [
    "ForwardingStatus",
    "ForwardingAddress",
    "ForwardingDeposit",
    "CCTPForwardingService",
    "FUNDING_SOURCE_CHAINS",
    "DEFAULT_DESTINATION_CHAIN",
]

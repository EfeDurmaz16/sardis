"""Circle CCTP V2 cross-chain USDC bridge service.

Enables zero-fee USDC transfers between supported EVM chains using
Circle's Cross-Chain Transfer Protocol V2.

Flow:
1. Approve USDC to TokenMessenger on source chain
2. Call depositForBurn on source TokenMessenger
3. Wait for Circle attestation (~13-20 minutes)
4. Call receiveMessage on destination MessageTransmitter
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from .cctp_constants import (
    CCTP_DOMAINS,
    TOKEN_MESSENGER_ADDRESSES,
    MESSAGE_TRANSMITTER_ADDRESSES,
    USDC_ADDRESSES,
    CIRCLE_ATTESTATION_API_URL,
    CIRCLE_ATTESTATION_API_SANDBOX_URL,
    get_cctp_domain,
    is_cctp_supported,
    get_bridge_estimate_seconds,
)

logger = logging.getLogger(__name__)


class BridgeStatus(str, Enum):
    """Status of a CCTP bridge transfer."""
    INITIATED = "initiated"
    DEPOSIT_SUBMITTED = "deposit_submitted"
    AWAITING_ATTESTATION = "awaiting_attestation"
    ATTESTATION_RECEIVED = "attestation_received"
    COMPLETING = "completing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class BridgeTransfer:
    """Tracks a CCTP bridge transfer."""
    transfer_id: str = field(default_factory=lambda: f"bridge_{uuid.uuid4().hex[:16]}")
    wallet_id: str = ""
    agent_id: Optional[str] = None
    from_chain: str = ""
    to_chain: str = ""
    amount: Decimal = Decimal("0")
    token: str = "USDC"
    message_hash: Optional[str] = None
    source_tx_hash: Optional[str] = None
    destination_tx_hash: Optional[str] = None
    status: BridgeStatus = BridgeStatus.INITIATED
    error: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "transfer_id": self.transfer_id,
            "wallet_id": self.wallet_id,
            "agent_id": self.agent_id,
            "from_chain": self.from_chain,
            "to_chain": self.to_chain,
            "amount": str(self.amount),
            "token": self.token,
            "message_hash": self.message_hash,
            "source_tx_hash": self.source_tx_hash,
            "destination_tx_hash": self.destination_tx_hash,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at.isoformat(),
        }


class CCTPBridgeService:
    """Service for cross-chain USDC transfers via Circle CCTP V2."""

    def __init__(
        self,
        chain_executor: Any | None = None,
        *,
        sandbox: bool = True,
    ):
        self._chain_executor = chain_executor
        self._sandbox = sandbox
        self._attestation_url = (
            CIRCLE_ATTESTATION_API_SANDBOX_URL if sandbox
            else CIRCLE_ATTESTATION_API_URL
        )

    async def bridge_usdc(
        self,
        from_chain: str,
        to_chain: str,
        amount: Decimal,
        recipient: str,
        wallet_id: str,
        agent_id: Optional[str] = None,
    ) -> BridgeTransfer:
        """
        Initiate a cross-chain USDC transfer via CCTP.

        Args:
            from_chain: Source chain (e.g., "base", "ethereum")
            to_chain: Destination chain
            amount: Amount in USDC (human-readable, e.g., 100.00)
            recipient: Destination address (0x...)
            wallet_id: Sardis wallet ID initiating the transfer
            agent_id: Optional agent ID for tracking

        Returns:
            BridgeTransfer with initial status

        Raises:
            ValueError: If chains are invalid or unsupported
        """
        # Validate chains
        if not is_cctp_supported(from_chain):
            raise ValueError(f"Source chain '{from_chain}' not supported by CCTP")
        if not is_cctp_supported(to_chain):
            raise ValueError(f"Destination chain '{to_chain}' not supported by CCTP")
        if from_chain == to_chain:
            raise ValueError("Source and destination chains must be different")
        if amount <= 0:
            raise ValueError("Amount must be positive")

        transfer = BridgeTransfer(
            wallet_id=wallet_id,
            agent_id=agent_id,
            from_chain=from_chain,
            to_chain=to_chain,
            amount=amount,
            token="USDC",
        )

        try:
            dest_domain = get_cctp_domain(to_chain)
            token_messenger = TOKEN_MESSENGER_ADDRESSES[from_chain]
            usdc_address = USDC_ADDRESSES[from_chain]
            amount_minor = int(amount * Decimal("1000000"))  # USDC has 6 decimals

            if self._chain_executor is None:
                # Simulated mode
                import secrets
                transfer.source_tx_hash = f"0x{secrets.token_hex(32)}"
                transfer.message_hash = f"0x{secrets.token_hex(32)}"
                transfer.status = BridgeStatus.AWAITING_ATTESTATION
                logger.info(
                    f"[SIMULATED] Bridge {transfer.transfer_id}: "
                    f"{amount} USDC {from_chain} -> {to_chain}"
                )
                return transfer

            # Step 1: Approve USDC to TokenMessenger
            logger.info(f"Bridge {transfer.transfer_id}: approving USDC to TokenMessenger")
            approve_tx = await self._chain_executor.send_raw_transaction(
                chain=from_chain,
                wallet_id=wallet_id,
                to=usdc_address,
                data=self._encode_approve(token_messenger, amount_minor),
            )

            # Step 2: Call depositForBurn
            logger.info(f"Bridge {transfer.transfer_id}: calling depositForBurn")
            deposit_data = self._encode_deposit_for_burn(
                amount=amount_minor,
                destination_domain=dest_domain,
                mint_recipient=recipient,
                burn_token=usdc_address,
            )
            deposit_tx = await self._chain_executor.send_raw_transaction(
                chain=from_chain,
                wallet_id=wallet_id,
                to=token_messenger,
                data=deposit_data,
            )

            transfer.source_tx_hash = deposit_tx.get("tx_hash", "")
            transfer.status = BridgeStatus.DEPOSIT_SUBMITTED

            # Extract message hash from deposit transaction logs
            message_hash = self._extract_message_hash(deposit_tx)
            transfer.message_hash = message_hash
            transfer.status = BridgeStatus.AWAITING_ATTESTATION

            logger.info(
                f"Bridge {transfer.transfer_id}: deposit submitted, "
                f"tx={transfer.source_tx_hash[:16]}..., awaiting attestation"
            )

            return transfer

        except Exception as e:
            transfer.status = BridgeStatus.FAILED
            transfer.error = str(e)
            logger.error(f"Bridge {transfer.transfer_id} failed: {e}")
            return transfer

    async def get_bridge_status(self, message_hash: str) -> dict:
        """
        Check attestation status for a bridge transfer.

        Args:
            message_hash: Message hash from depositForBurn transaction

        Returns:
            Dict with status and optional attestation data
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                url = f"{self._attestation_url}/{message_hash}"
                async with session.get(url) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return {
                            "status": data.get("status", "pending"),
                            "attestation": data.get("attestation"),
                        }
                    return {"status": "pending", "attestation": None}
        except ImportError:
            # aiohttp not available, return pending
            logger.warning("aiohttp not available for attestation polling")
            return {"status": "pending", "attestation": None}
        except Exception as e:
            logger.error(f"Error checking attestation: {e}")
            return {"status": "error", "error": str(e)}

    async def complete_bridge(
        self,
        transfer: BridgeTransfer,
        attestation: str,
        message_bytes: bytes,
    ) -> BridgeTransfer:
        """
        Complete bridge by calling receiveMessage on destination chain.

        Args:
            transfer: The bridge transfer to complete
            attestation: Circle attestation bytes
            message_bytes: Original message bytes from source chain

        Returns:
            Updated BridgeTransfer
        """
        if transfer.status not in (BridgeStatus.AWAITING_ATTESTATION, BridgeStatus.ATTESTATION_RECEIVED):
            raise ValueError(f"Cannot complete bridge in status {transfer.status.value}")

        transfer.status = BridgeStatus.COMPLETING
        to_chain = transfer.to_chain
        message_transmitter = MESSAGE_TRANSMITTER_ADDRESSES[to_chain]

        try:
            if self._chain_executor is None:
                # Simulated mode
                import secrets
                transfer.destination_tx_hash = f"0x{secrets.token_hex(32)}"
                transfer.status = BridgeStatus.COMPLETED
                logger.info(f"[SIMULATED] Bridge {transfer.transfer_id} completed")
                return transfer

            receive_data = self._encode_receive_message(message_bytes, bytes.fromhex(attestation.removeprefix("0x")))
            receive_tx = await self._chain_executor.send_raw_transaction(
                chain=to_chain,
                wallet_id=transfer.wallet_id,
                to=message_transmitter,
                data=receive_data,
            )

            transfer.destination_tx_hash = receive_tx.get("tx_hash", "")
            transfer.status = BridgeStatus.COMPLETED

            logger.info(
                f"Bridge {transfer.transfer_id} completed: "
                f"dest_tx={transfer.destination_tx_hash[:16]}..."
            )
            return transfer

        except Exception as e:
            transfer.status = BridgeStatus.FAILED
            transfer.error = str(e)
            logger.error(f"Bridge completion failed: {e}")
            return transfer

    def estimate_bridge_time(self, from_chain: str, to_chain: str) -> int:
        """Estimate bridge time in seconds."""
        return get_bridge_estimate_seconds(from_chain, to_chain)

    @staticmethod
    def _encode_approve(spender: str, amount: int) -> str:
        """Encode ERC-20 approve(address, uint256) call."""
        spender_padded = spender.lower().removeprefix("0x").zfill(64)
        amount_hex = hex(amount)[2:].zfill(64)
        return f"0x095ea7b3{spender_padded}{amount_hex}"

    @staticmethod
    def _encode_deposit_for_burn(
        amount: int,
        destination_domain: int,
        mint_recipient: str,
        burn_token: str,
    ) -> str:
        """Encode depositForBurn(uint256, uint32, bytes32, address) call."""
        amount_hex = hex(amount)[2:].zfill(64)
        domain_hex = hex(destination_domain)[2:].zfill(64)
        # Convert address to bytes32 (left-pad with zeros)
        recipient_padded = mint_recipient.lower().removeprefix("0x").zfill(64)
        token_padded = burn_token.lower().removeprefix("0x").zfill(64)
        return f"0x6fd3504e{amount_hex}{domain_hex}{recipient_padded}{token_padded}"

    @staticmethod
    def _encode_receive_message(message: bytes, attestation: bytes) -> str:
        """Encode receiveMessage(bytes, bytes) call."""
        # ABI encode two dynamic bytes parameters
        selector = "0x57ecfd28"
        # Offset for first bytes param (after two offset words)
        offset1 = 64
        # Offset for second bytes param
        msg_padded_len = ((len(message) + 31) // 32) * 32
        offset2 = offset1 + 32 + msg_padded_len

        result = selector
        result += hex(offset1)[2:].zfill(64)
        result += hex(offset2)[2:].zfill(64)
        # First bytes: length + data
        result += hex(len(message))[2:].zfill(64)
        result += message.hex().ljust(msg_padded_len * 2, '0')
        # Second bytes: length + data
        att_padded_len = ((len(attestation) + 31) // 32) * 32
        result += hex(len(attestation))[2:].zfill(64)
        result += attestation.hex().ljust(att_padded_len * 2, '0')

        return result

    @staticmethod
    def _extract_message_hash(tx_receipt: dict) -> str:
        """Extract message hash from depositForBurn transaction receipt."""
        # The MessageSent event log contains the message hash
        logs = tx_receipt.get("logs", [])
        for log in logs:
            # MessageSent event topic
            topics = log.get("topics", [])
            if topics:
                return topics[0]
        # Fallback: hash the transaction hash
        tx_hash = tx_receipt.get("tx_hash", "")
        return f"0x{hashlib.keccak_256(bytes.fromhex(tx_hash.removeprefix('0x'))).hexdigest()}" if tx_hash else ""


__all__ = [
    "BridgeStatus",
    "BridgeTransfer",
    "CCTPBridgeService",
]

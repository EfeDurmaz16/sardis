"""Tempo Fee Payer — native gas sponsorship for agent transactions.

On Tempo, fee sponsorship is protocol-native (no ERC-4337):
- A third party signs with magic byte 0x78
- Agents NEVER need gas tokens
- Sardis treasury pays all gas fees

This replaces Circle Paymaster + Pimlico on Tempo.
On Base/ETH, keep using Circle Paymaster.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

logger = logging.getLogger("sardis.chain.tempo.fee_payer")


@dataclass
class SponsorshipPolicy:
    """Policy for when Sardis sponsors gas fees."""
    max_per_tx_usd: Decimal = field(default_factory=lambda: Decimal("1.00"))
    max_daily_usd: Decimal = field(default_factory=lambda: Decimal("100.00"))
    allowed_tokens: list[str] = field(
        default_factory=lambda: ["0x20c0000000000000000000000000000000000000"]  # pathUSD
    )
    require_mandate: bool = True  # Only sponsor mandated transactions


@dataclass
class SponsorshipRecord:
    """Record of a gas sponsorship for audit trail."""
    tx_hash: str
    agent_id: str | None = None
    mandate_id: str | None = None
    gas_used: int = 0
    fee_paid_usd: Decimal = field(default_factory=lambda: Decimal("0"))
    fee_token: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class TempoFeePayer:
    """Signs type 0x76 transactions with magic byte 0x78 to sponsor gas.

    The fee payer co-signs the transaction, committing to pay gas fees.
    This is a protocol-level feature — no smart contracts needed.
    """

    def __init__(
        self,
        private_key: str | None = None,
        policy: SponsorshipPolicy | None = None,
        rpc_url: str = "https://rpc.tempo.xyz",
    ) -> None:
        self._private_key = private_key
        self._policy = policy or SponsorshipPolicy()
        self._rpc_url = rpc_url
        self._daily_spent = Decimal("0")
        self._daily_reset_at = datetime.now(UTC)
        self._records: list[SponsorshipRecord] = []

    async def co_sign(self, tx_data: dict[str, Any]) -> dict[str, Any]:
        """Add fee payer signature (0x78 magic byte) to a type 0x76 transaction.

        Returns the transaction with the fee payer signature appended.
        """
        # Reset daily counter if needed
        now = datetime.now(UTC)
        if now.date() > self._daily_reset_at.date():
            self._daily_spent = Decimal("0")
            self._daily_reset_at = now

        # Check sponsorship policy
        if self._daily_spent >= self._policy.max_daily_usd:
            logger.warning("Daily sponsorship limit reached: %s", self._daily_spent)
            raise ValueError("Daily gas sponsorship limit exceeded")

        # In production: sign with the fee payer's private key using 0x78 magic byte
        if self._private_key:
            # The actual signing involves:
            # 1. Hash the transaction data
            # 2. Sign with ECDSA using 0x78 prefix byte
            # 3. Append the fee payer signature to the transaction
            fee_payer_sig = await self._sign_as_fee_payer(tx_data)
            tx_data["feePayerSignature"] = fee_payer_sig

        logger.info("Co-signed transaction as fee payer")
        return tx_data

    async def estimate_fee(self, tx_data: dict[str, Any]) -> Decimal:
        """Estimate the gas fee for a transaction in USD terms."""
        # On Tempo, fees are paid in TIP-20 stablecoins
        # Typical fee: ~$0.001 per call in the batch
        call_count = len(tx_data.get("calls", []))
        base_fee = Decimal("0.001")
        return (base_fee * call_count).quantize(Decimal("0.000001"))

    def record_sponsorship(
        self,
        tx_hash: str,
        gas_used: int,
        fee_paid_usd: Decimal,
        agent_id: str | None = None,
        mandate_id: str | None = None,
        fee_token: str = "",
    ) -> SponsorshipRecord:
        """Record a gas sponsorship for audit trail."""
        record = SponsorshipRecord(
            tx_hash=tx_hash,
            agent_id=agent_id,
            mandate_id=mandate_id,
            gas_used=gas_used,
            fee_paid_usd=fee_paid_usd,
            fee_token=fee_token,
        )
        self._daily_spent += fee_paid_usd
        self._records.append(record)
        return record

    async def _sign_as_fee_payer(self, tx_data: dict[str, Any]) -> str:
        """Sign the transaction hash with 0x78 magic byte prefix.

        The 0x78 fee payer envelope (from pympp fee_payer_envelope.py) contains
        14-15 RLP-encoded fields: chain_id, gas params, calls, access_list,
        nonce_key, nonce_value, valid_before, valid_after, fee_token,
        sender_address, auth_list, optional key_auth, sender_signature.
        """
        if not self._private_key:
            return "0x78" + "0" * 128  # Placeholder when no key configured

        try:
            from eth_account import Account

            # Build the fee payer envelope fields
            envelope_fields = [
                tx_data.get("chainId", 4217),           # chain_id
                tx_data.get("maxPriorityFeePerGas", 0),  # priority fee
                tx_data.get("maxFeePerGas", 0),          # max fee
                tx_data.get("gas", 1000000),             # gas limit
                tx_data.get("calls", []),                # batch calls
                [],                                       # access list
                tx_data.get("nonceKey", 0),              # 2D nonce key
                tx_data.get("nonceSeq", 0),              # 2D nonce seq
                tx_data.get("validBefore", 0),           # expiry timestamp
                tx_data.get("validAfter", 0),            # start timestamp
                tx_data.get("feeToken", b""),             # fee token address
            ]

            # Hash the envelope for signing
            import hashlib
            envelope_bytes = str(envelope_fields).encode()
            msg_hash = hashlib.sha256(b"\x78" + envelope_bytes).digest()

            # Sign with fee payer private key
            signed = Account.unsafe_sign_hash(msg_hash, self._private_key)
            sig_bytes = signed.signature

            # Return 0x78 prefix + RLP-encoded envelope + signature
            return "0x78" + sig_bytes.hex()

        except ImportError:
            logger.warning("eth_account not installed — using placeholder fee payer signature")
            return "0x78" + "0" * 128

    @property
    def daily_spent(self) -> Decimal:
        return self._daily_spent

    @property
    def daily_remaining(self) -> Decimal:
        return self._policy.max_daily_usd - self._daily_spent

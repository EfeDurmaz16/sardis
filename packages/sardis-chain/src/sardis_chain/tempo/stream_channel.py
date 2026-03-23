"""Tempo Stream Channel — off-chain micropayment vouchers with batch settlement.

Stream channels enable pay-per-use agent payments:
1. Client deposits TIP-20 tokens into a channel
2. Service issues signed vouchers for each unit of work
3. Vouchers accumulate off-chain (no gas per micro-payment)
4. Either party can settle on-chain at any time
5. Unsettled vouchers expire with the channel

Use case: LLM inference billing — pay per output token.

Usage::

    channel = TempoStreamChannel(executor)
    session = await channel.open(
        client="0xagent...", service="0xllm...",
        deposit=Decimal("10.00"), token="USDC",
    )
    voucher = channel.issue_voucher(session.channel_id, Decimal("0.001"))
    # ... repeat for each token ...
    receipt = await channel.settle(session.channel_id)
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

logger = logging.getLogger("sardis.chain.tempo.stream_channel")


@dataclass
class StreamVoucher:
    """An off-chain micropayment voucher."""
    voucher_id: str = field(default_factory=lambda: f"sv_{uuid4().hex[:8]}")
    channel_id: str = ""
    sequence: int = 0
    cumulative_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    signature: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class StreamSession:
    """An open stream channel session."""
    channel_id: str = field(default_factory=lambda: f"sch_{uuid4().hex[:12]}")
    client_address: str = ""
    service_address: str = ""
    token_address: str = ""
    deposit_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    settled_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    voucher_count: int = 0
    latest_cumulative: Decimal = field(default_factory=lambda: Decimal("0"))
    status: str = "open"  # open, settling, settled, expired, disputed
    deposit_tx_hash: str | None = None
    settle_tx_hash: str | None = None
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(UTC) + timedelta(hours=24)
    )
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def remaining_deposit(self) -> Decimal:
        return self.deposit_amount - self.latest_cumulative

    @property
    def is_expired(self) -> bool:
        return datetime.now(UTC) > self.expires_at


class TempoStreamChannel:
    """Manages off-chain micropayment channels on Tempo.

    Combines TIP-20 deposit with off-chain voucher accumulation
    for gas-efficient streaming payments.
    """

    def __init__(self, executor=None) -> None:
        self._executor = executor
        self._sessions: dict[str, StreamSession] = {}
        self._vouchers: dict[str, list[StreamVoucher]] = {}

    async def open(
        self,
        client: str,
        service: str,
        deposit: Decimal,
        token: str = "USDC",
        token_address: str = "0x20c0000000000000000000000000000000000000",
        duration_hours: int = 24,
    ) -> StreamSession:
        """Open a stream channel with a TIP-20 deposit."""
        session = StreamSession(
            client_address=client,
            service_address=service,
            token_address=token_address,
            deposit_amount=deposit,
            expires_at=datetime.now(UTC) + timedelta(hours=duration_hours),
        )

        # On-chain deposit (type 0x76 batch: approve + deposit)
        if self._executor:
            amount_raw = int(deposit * Decimal("1000000"))
            receipt = await self._executor.execute_transfer(
                token_address=token_address,
                to=service,  # In production: to escrow contract
                amount=amount_raw,
                memo=session.channel_id.encode("utf-8")[:32],
            )
            session.deposit_tx_hash = receipt.tx_hash

        self._sessions[session.channel_id] = session
        self._vouchers[session.channel_id] = []

        logger.info(
            "Stream channel %s opened: %s %s deposit, %s→%s",
            session.channel_id, deposit, token, client, service,
        )
        return session

    def issue_voucher(
        self,
        channel_id: str,
        amount: Decimal,
    ) -> StreamVoucher:
        """Issue an off-chain voucher for a micro-payment.

        Vouchers are cumulative — each new voucher supersedes
        all previous ones. Only the latest voucher needs to be
        settled on-chain.
        """
        session = self._sessions.get(channel_id)
        if not session:
            raise ValueError(f"Channel {channel_id} not found")
        if session.status != "open":
            raise ValueError(f"Channel is {session.status}")
        if session.is_expired:
            raise ValueError("Channel has expired")

        new_cumulative = session.latest_cumulative + amount
        if new_cumulative > session.deposit_amount:
            raise ValueError(
                f"Cumulative {new_cumulative} exceeds deposit {session.deposit_amount}"
            )

        voucher = StreamVoucher(
            channel_id=channel_id,
            sequence=session.voucher_count + 1,
            cumulative_amount=new_cumulative,
            signature=self._sign_voucher(channel_id, new_cumulative),
        )

        session.latest_cumulative = new_cumulative
        session.voucher_count += 1
        self._vouchers[channel_id].append(voucher)

        return voucher

    async def settle(self, channel_id: str) -> StreamSession:
        """Settle the channel on-chain with the latest voucher."""
        session = self._sessions.get(channel_id)
        if not session:
            raise ValueError(f"Channel {channel_id} not found")
        if session.status != "open":
            raise ValueError(f"Channel is {session.status}")

        session.status = "settling"

        # Submit latest cumulative amount on-chain
        if self._executor and session.latest_cumulative > 0:
            amount_raw = int(session.latest_cumulative * Decimal("1000000"))
            receipt = await self._executor.execute_transfer(
                token_address=session.token_address,
                to=session.service_address,
                amount=amount_raw,
                memo=f"settle:{channel_id}".encode("utf-8")[:32],
            )
            session.settle_tx_hash = receipt.tx_hash

        session.settled_amount = session.latest_cumulative
        session.status = "settled"

        logger.info(
            "Stream channel %s settled: %s (from %d vouchers)",
            channel_id, session.settled_amount, session.voucher_count,
        )
        return session

    def get_session(self, channel_id: str) -> StreamSession | None:
        return self._sessions.get(channel_id)

    def get_vouchers(self, channel_id: str) -> list[StreamVoucher]:
        return self._vouchers.get(channel_id, [])

    @staticmethod
    def _sign_voucher(channel_id: str, cumulative: Decimal) -> str:
        """Sign a voucher (placeholder — production uses ECDSA)."""
        data = f"{channel_id}:{cumulative}".encode()
        return hashlib.sha256(data).hexdigest()[:64]

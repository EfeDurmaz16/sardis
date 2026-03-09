"""x402 upto scheme — streaming micropayment sessions.

The 'upto' scheme allows incremental consumption against a pre-authorized
maximum amount (Permit2 pattern). Useful for streaming API access.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal


@dataclass
class UptoConsumption:
    """Record of a single consumption within an upto session."""
    consumption_id: str
    amount: str
    cumulative: str
    remaining: str
    timestamp: int


@dataclass
class UptoSettlement:
    """Final settlement of an upto session."""
    session_id: str
    total_consumed: str
    max_amount: str
    finalized_at: int
    payment_id: str = ""


@dataclass
class UptoSession:
    """Manages a streaming micropayment session.

    The payer pre-authorizes a max_amount. The server incrementally
    consumes from this authorization until finalized.
    """
    session_id: str = field(default_factory=lambda: f"upto_{uuid.uuid4().hex[:16]}")
    payment_id: str = ""
    max_amount: Decimal = Decimal("0")
    consumed: Decimal = Decimal("0")
    wallet_address: str = ""
    network: str = "base"
    currency: str = "USDC"
    created_at: int = field(default_factory=lambda: int(time.time()))
    finalized: bool = False
    consumptions: list[UptoConsumption] = field(default_factory=list)

    async def consume(self, amount: str) -> UptoConsumption:
        """Consume an incremental amount from the session."""
        if self.finalized:
            raise ValueError("upto_session_finalized")

        amt = Decimal(amount)
        new_total = self.consumed + amt

        if new_total > self.max_amount:
            raise ValueError(
                f"upto_exceed_max: consuming {amount} would bring total to "
                f"{new_total} exceeding max {self.max_amount}"
            )

        self.consumed = new_total
        remaining = self.max_amount - self.consumed

        consumption = UptoConsumption(
            consumption_id=f"cons_{uuid.uuid4().hex[:12]}",
            amount=str(amt),
            cumulative=str(self.consumed),
            remaining=str(remaining),
            timestamp=int(time.time()),
        )
        self.consumptions.append(consumption)
        return consumption

    async def finalize(self) -> UptoSettlement:
        """Finalize the session and settle the consumed amount."""
        if self.finalized:
            raise ValueError("upto_session_already_finalized")

        self.finalized = True
        return UptoSettlement(
            session_id=self.session_id,
            total_consumed=str(self.consumed),
            max_amount=str(self.max_amount),
            finalized_at=int(time.time()),
            payment_id=self.payment_id,
        )

    def get_remaining(self) -> str:
        """Get remaining authorized amount."""
        return str(self.max_amount - self.consumed)


def build_permit2_typed_data(
    token: str,
    spender: str,
    amount: int,
    nonce: int,
    deadline: int,
) -> dict:
    """Build EIP-712 typed data for Permit2 approval.

    Used for the upto scheme where the payer pre-authorizes
    a maximum amount via Permit2.
    """
    return {
        "types": {
            "EIP712Domain": [
                {"name": "name", "type": "string"},
                {"name": "chainId", "type": "uint256"},
                {"name": "verifyingContract", "type": "address"},
            ],
            "PermitSingle": [
                {"name": "details", "type": "PermitDetails"},
                {"name": "spender", "type": "address"},
                {"name": "sigDeadline", "type": "uint256"},
            ],
            "PermitDetails": [
                {"name": "token", "type": "address"},
                {"name": "amount", "type": "uint160"},
                {"name": "expiration", "type": "uint48"},
                {"name": "nonce", "type": "uint48"},
            ],
        },
        "primaryType": "PermitSingle",
        "domain": {
            "name": "Permit2",
            "chainId": 8453,  # Base mainnet, override per chain
            "verifyingContract": "0x000000000022D473030F116dDEE9F6B43aC78BA3",
        },
        "message": {
            "details": {
                "token": token,
                "amount": str(amount),
                "expiration": str(deadline),
                "nonce": str(nonce),
            },
            "spender": spender,
            "sigDeadline": str(deadline),
        },
    }


__all__ = [
    "UptoSession",
    "UptoConsumption",
    "UptoSettlement",
    "build_permit2_typed_data",
]

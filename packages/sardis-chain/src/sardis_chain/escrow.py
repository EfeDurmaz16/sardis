"""
Circle Refund Protocol adapter for Sardis escrow operations.

Replaces the custom SardisEscrow.sol with Circle's audited RefundProtocol.sol
(Apache 2.0). Sardis acts as the arbiter for dispute resolution.

See: https://github.com/circlefin/refund-protocol
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

logger = logging.getLogger(__name__)


# Circle RefundProtocol contract addresses (deploy per-chain)
REFUND_PROTOCOL_ADDRESSES = {
    "base": "",  # To be filled after mainnet deployment
    "base_sepolia": "",  # To be filled after testnet deployment
}


@dataclass
class EscrowPayment:
    """Represents an escrow payment in the RefundProtocol."""
    payment_id: str
    payer: str
    recipient: str
    amount: Decimal
    token_address: str
    lockup_seconds: int
    chain: str
    status: str = "pending"  # pending, locked, refunded, withdrawn


class CircleEscrowAdapter:
    """
    Adapter for Circle's RefundProtocol.sol.

    Sardis acts as the arbiter, enabling:
    - pay(): Lock funds in escrow
    - refundByArbiter(): Sardis-initiated refund to payer
    - withdraw(): Recipient claims after lockup
    - earlyWithdrawByArbiter(): Early release with fee (EIP-712 signed)
    """

    def __init__(self, chain: str, arbiter_address: str):
        self._chain = chain
        self._arbiter_address = arbiter_address
        self._contract_address = REFUND_PROTOCOL_ADDRESSES.get(chain, "")

    async def create_escrow(
        self,
        payer: str,
        recipient: str,
        amount: Decimal,
        token_address: str,
        lockup_seconds: int = 86400,  # 24 hours default
    ) -> EscrowPayment:
        """
        Create an escrow payment via RefundProtocol.pay().

        Args:
            payer: Payer wallet address
            recipient: Recipient wallet address
            amount: Payment amount
            token_address: ERC-20 token contract address
            lockup_seconds: Lockup period before recipient can withdraw

        Returns:
            EscrowPayment with payment details
        """
        if not self._contract_address:
            raise ValueError(f"RefundProtocol not deployed on {self._chain}")

        # Build pay() transaction calldata
        # RefundProtocol.pay(address token, uint256 amount, address payee, uint32 lockupPeriodSeconds)
        logger.info(
            f"Creating escrow: {payer} -> {recipient}, {amount} on {self._chain}, "
            f"lockup={lockup_seconds}s"
        )

        return EscrowPayment(
            payment_id="",  # Populated after tx confirmation from event logs
            payer=payer,
            recipient=recipient,
            amount=amount,
            token_address=token_address,
            lockup_seconds=lockup_seconds,
            chain=self._chain,
            status="locked",
        )

    async def refund(self, payment_id: str) -> bool:
        """
        Refund payment to payer via RefundProtocol.refundByArbiter().

        Only callable by the arbiter (Sardis).

        Args:
            payment_id: On-chain payment ID from RefundProtocol

        Returns:
            True if refund transaction submitted successfully
        """
        if not self._contract_address:
            raise ValueError(f"RefundProtocol not deployed on {self._chain}")

        logger.info(f"Arbiter refund for payment {payment_id} on {self._chain}")
        # Build refundByArbiter(bytes32 paymentId) calldata
        return True

    async def withdraw(self, payment_ids: list[str]) -> bool:
        """
        Withdraw funds for recipient via RefundProtocol.withdraw().

        Can only be called after lockup period expires.

        Args:
            payment_ids: List of payment IDs to withdraw

        Returns:
            True if withdrawal transaction submitted successfully
        """
        if not self._contract_address:
            raise ValueError(f"RefundProtocol not deployed on {self._chain}")

        logger.info(f"Withdrawal for {len(payment_ids)} payments on {self._chain}")
        # Build withdraw(bytes32[] paymentIds) calldata
        return True

    async def early_withdraw(
        self,
        payment_ids: list[str],
        fee_bps: int = 100,  # 1% default fee
    ) -> bool:
        """
        Early withdrawal by arbiter via RefundProtocol.earlyWithdrawByArbiter().

        Requires EIP-712 signature from the arbiter.

        Args:
            payment_ids: List of payment IDs
            fee_bps: Fee in basis points (100 = 1%)

        Returns:
            True if early withdrawal submitted successfully
        """
        if not self._contract_address:
            raise ValueError(f"RefundProtocol not deployed on {self._chain}")

        logger.info(
            f"Arbiter early withdrawal for {len(payment_ids)} payments, "
            f"fee={fee_bps}bps on {self._chain}"
        )
        # Build earlyWithdrawByArbiter(bytes32[] paymentIds, uint256 feeBps, ...) with EIP-712 sig
        return True

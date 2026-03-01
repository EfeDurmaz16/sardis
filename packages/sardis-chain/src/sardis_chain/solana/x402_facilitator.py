"""x402 payment facilitator for Solana.

Implements the facilitator pattern for x402 HTTP payments on Solana,
enabling AI agents to pay for API access using SPL token transfers.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from .client import SolanaClient, SolanaConfig, get_solana_config, SOLANA_USDC_MINT
from .transfer import SolanaTransferParams, build_spl_transfer, execute_spl_transfer
from .gasless import build_gasless_transfer, KoraGaslessClient

logger = logging.getLogger(__name__)


@dataclass
class X402SolanaPayment:
    """Represents a verified x402 payment on Solana."""
    payment_id: str
    sender: str
    recipient: str
    mint: str
    amount: int
    signature: str | None = None
    settled: bool = False


class SolanaX402Facilitator:
    """Facilitates x402 payments on Solana.

    Verifies payment proofs and settles SPL token transfers
    for the x402 HTTP payment protocol.
    """

    def __init__(
        self,
        client: SolanaClient | None = None,
        kora_client: KoraGaslessClient | None = None,
        use_gasless: bool = True,
    ) -> None:
        self.client = client or SolanaClient(get_solana_config())
        self.kora_client = kora_client
        self.use_gasless = use_gasless

    async def verify_payment(
        self,
        payment_header: dict[str, Any],
    ) -> X402SolanaPayment:
        """Verify an x402 payment header for Solana.

        Checks that the payment references a valid Solana address
        and token mint with sufficient balance.
        """
        sender = payment_header.get("sender", "")
        recipient = payment_header.get("recipient", "")
        amount = int(payment_header.get("amount", 0))
        mint = payment_header.get("mint", SOLANA_USDC_MINT)
        payment_id = payment_header.get("payment_id", "")

        if not sender or not recipient:
            raise ValueError("x402: sender and recipient required")
        if amount <= 0:
            raise ValueError("x402: amount must be positive")

        # Verify sender has sufficient balance
        try:
            accounts = await self.client.get_token_accounts_by_owner(sender, mint)
            if not accounts:
                raise ValueError(f"x402: sender {sender} has no token account for {mint}")

            token_account = accounts[0]["pubkey"]
            balance = await self.client.get_token_balance(token_account)
            if balance < amount:
                raise ValueError(
                    f"x402: insufficient balance. Has {balance}, needs {amount}"
                )
        except ValueError:
            raise
        except Exception as e:
            raise ValueError(f"x402: failed to verify sender balance: {e}") from e

        return X402SolanaPayment(
            payment_id=payment_id,
            sender=sender,
            recipient=recipient,
            mint=mint,
            amount=amount,
        )

    async def settle_payment(
        self,
        payment: X402SolanaPayment,
        signed_tx_base64: str,
    ) -> X402SolanaPayment:
        """Settle an x402 payment by executing the signed SPL transfer."""
        params = SolanaTransferParams(
            sender=payment.sender,
            recipient=payment.recipient,
            mint=payment.mint,
            amount=payment.amount,
        )

        result = await execute_spl_transfer(self.client, signed_tx_base64, params)

        payment.signature = result.signature
        payment.settled = result.confirmed
        logger.info(
            "x402 Solana payment settled: id=%s sig=%s",
            payment.payment_id, result.signature,
        )
        return payment

    async def build_settlement_tx(
        self, payment: X402SolanaPayment,
    ) -> dict[str, Any]:
        """Build the settlement transaction for MPC signing."""
        params = SolanaTransferParams(
            sender=payment.sender,
            recipient=payment.recipient,
            mint=payment.mint,
            amount=payment.amount,
        )

        if self.use_gasless:
            return await build_gasless_transfer(
                self.client, params, self.kora_client
            )
        return await build_spl_transfer(self.client, params)

    async def close(self) -> None:
        """Clean up resources."""
        await self.client.close()
        if self.kora_client:
            await self.kora_client.close()

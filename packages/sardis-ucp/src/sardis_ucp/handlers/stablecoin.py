"""Stablecoin payment handler for UCP.

Handles payments in USDC, USDT, PYUSD, EURC on supported chains
using the Sardis ChainExecutor for MPC-signed transactions.

Handler name: sardis.stablecoin
"""

from __future__ import annotations

import hashlib
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Protocol

from ..models.mandates import UCPPaymentMandate
from .base import PaymentHandler, PaymentReceipt, PaymentStatus, PaymentExecutionError

logger = logging.getLogger(__name__)


# Supported tokens and chains
SUPPORTED_TOKENS = ["USDC", "USDT", "PYUSD", "EURC"]
SUPPORTED_CHAINS = ["base", "polygon", "ethereum", "arbitrum", "optimism"]


# ============ ChainExecutor Protocol ============


class ChainReceipt(Protocol):
    """Protocol for chain execution receipt."""

    tx_hash: str
    chain: str
    block_number: int | None
    gas_used: int | None
    audit_anchor: str


class ChainExecutorPort(Protocol):
    """Protocol for chain execution.

    This mirrors the ChainExecutor interface from sardis-chain.
    """

    async def dispatch_payment(self, mandate: Any) -> ChainReceipt:
        """Execute a payment mandate on-chain.

        Args:
            mandate: Payment mandate to execute

        Returns:
            ChainReceipt with transaction details
        """
        ...


class LedgerPort(Protocol):
    """Protocol for ledger operations.

    This mirrors the LedgerStore interface from sardis-ledger.
    """

    def append(self, payment_mandate: Any, chain_receipt: Any) -> Any:
        """Append a transaction to the ledger.

        Args:
            payment_mandate: The payment mandate
            chain_receipt: The chain execution receipt

        Returns:
            Transaction record
        """
        ...


# ============ Stablecoin Payment Handler ============


class StablecoinPaymentHandler:
    """
    Payment handler for stablecoin payments.

    Supports:
    - Tokens: USDC, USDT, PYUSD, EURC
    - Chains: Base, Polygon, Ethereum, Arbitrum, Optimism

    Uses the Sardis ChainExecutor for MPC-signed transactions,
    ensuring non-custodial execution with policy enforcement.
    """

    def __init__(
        self,
        chain_executor: ChainExecutorPort | None = None,
        ledger: LedgerPort | None = None,
    ) -> None:
        """
        Initialize the stablecoin payment handler.

        Args:
            chain_executor: Chain executor for on-chain transactions
            ledger: Ledger for transaction recording
        """
        self._chain_executor = chain_executor
        self._ledger = ledger

    @property
    def handler_name(self) -> str:
        """Unique identifier for this handler."""
        return "sardis.stablecoin"

    @property
    def supported_tokens(self) -> list[str]:
        """List of supported token symbols."""
        return list(SUPPORTED_TOKENS)

    @property
    def supported_chains(self) -> list[str]:
        """List of supported blockchain networks."""
        return list(SUPPORTED_CHAINS)

    def can_handle(self, mandate: UCPPaymentMandate) -> bool:
        """Check if this handler can process the given mandate."""
        return (
            mandate.token.upper() in SUPPORTED_TOKENS
            and mandate.chain.lower() in SUPPORTED_CHAINS
        )

    async def execute(self, mandate: UCPPaymentMandate) -> PaymentReceipt:
        """
        Execute a stablecoin payment mandate.

        This method:
        1. Validates the mandate can be handled
        2. Executes the payment via ChainExecutor
        3. Records the transaction in the ledger
        4. Returns a payment receipt

        Args:
            mandate: The payment mandate to execute

        Returns:
            PaymentReceipt with execution result

        Raises:
            PaymentExecutionError: If payment fails
        """
        # Validate mandate
        if not self.can_handle(mandate):
            raise PaymentExecutionError(
                f"Cannot handle mandate: token={mandate.token}, chain={mandate.chain}",
                code="unsupported_payment",
                mandate_id=mandate.mandate_id,
            )

        if self._chain_executor is None:
            raise PaymentExecutionError(
                "Chain executor not configured",
                code="executor_not_configured",
                mandate_id=mandate.mandate_id,
            )

        logger.info(
            f"Executing stablecoin payment: mandate_id={mandate.mandate_id}, "
            f"chain={mandate.chain}, token={mandate.token}, "
            f"amount={mandate.amount_minor}, destination={mandate.destination}"
        )

        # Convert UCP mandate to format expected by ChainExecutor
        # The ChainExecutor expects a PaymentMandate from sardis-core
        chain_mandate = self._convert_to_chain_mandate(mandate)

        try:
            # Execute on-chain
            receipt = await self._chain_executor.dispatch_payment(chain_mandate)

            # Record in ledger if available
            ledger_tx_id = None
            if self._ledger:
                try:
                    ledger_tx = self._ledger.append(chain_mandate, receipt)
                    ledger_tx_id = getattr(ledger_tx, "tx_id", None)
                except Exception as e:
                    logger.warning(
                        f"Ledger append failed for mandate {mandate.mandate_id}: {e}"
                    )
                    # Don't fail the payment - ledger reconciliation will handle this

            logger.info(
                f"Payment executed: mandate_id={mandate.mandate_id}, "
                f"tx_hash={receipt.tx_hash}, block={receipt.block_number}"
            )

            return PaymentReceipt(
                mandate_id=mandate.mandate_id,
                chain=mandate.chain,
                token=mandate.token,
                amount_minor=mandate.amount_minor,
                destination=mandate.destination,
                status=PaymentStatus.SUBMITTED,
                tx_hash=receipt.tx_hash,
                block_number=receipt.block_number,
                gas_used=receipt.gas_used,
                audit_anchor=receipt.audit_anchor,
                ledger_tx_id=ledger_tx_id,
            )

        except Exception as e:
            logger.error(
                f"Payment execution failed: mandate_id={mandate.mandate_id}, error={e}"
            )
            raise PaymentExecutionError(
                f"Payment execution failed: {e}",
                code="execution_failed",
                mandate_id=mandate.mandate_id,
                details={"error": str(e)},
            )

    async def get_status(self, tx_hash: str) -> PaymentStatus:
        """
        Get the current status of a transaction.

        Note: This is a simplified implementation. In production,
        this would query the chain for transaction confirmation status.

        Args:
            tx_hash: Transaction hash to check

        Returns:
            Current payment status
        """
        # For now, return SUBMITTED as we don't have chain querying
        # In production, this would check:
        # 1. Transaction existence on chain
        # 2. Confirmation count
        # 3. Success/failure status
        return PaymentStatus.SUBMITTED

    def _convert_to_chain_mandate(self, mandate: UCPPaymentMandate) -> Any:
        """
        Convert UCP payment mandate to format expected by ChainExecutor.

        The ChainExecutor expects a PaymentMandate dataclass from sardis-core.
        This creates a compatible object.
        """
        # Create a simple object that has the required attributes
        # The ChainExecutor uses duck typing, so we just need matching attributes

        class ChainPaymentMandate:
            """Adapter for UCP mandate to chain executor format."""

            def __init__(self, ucp_mandate: UCPPaymentMandate):
                self.mandate_id = ucp_mandate.mandate_id
                self.mandate_type = "payment"
                self.issuer = ucp_mandate.issuer
                self.subject = ucp_mandate.subject
                self.expires_at = ucp_mandate.expires_at
                self.nonce = ucp_mandate.nonce
                self.domain = "ucp.sardis.sh"
                self.purpose = "checkout"
                self.chain = ucp_mandate.chain
                self.token = ucp_mandate.token
                self.amount_minor = ucp_mandate.amount_minor
                self.destination = ucp_mandate.destination
                self.audit_hash = ucp_mandate.audit_hash

            def is_expired(self) -> bool:
                import time
                return self.expires_at <= int(time.time())

        return ChainPaymentMandate(mandate)


# ============ Factory ============


def create_stablecoin_handler(
    chain_executor: ChainExecutorPort | None = None,
    ledger: LedgerPort | None = None,
) -> StablecoinPaymentHandler:
    """
    Create a stablecoin payment handler.

    Args:
        chain_executor: Chain executor for on-chain transactions
        ledger: Ledger for transaction recording

    Returns:
        Configured StablecoinPaymentHandler
    """
    return StablecoinPaymentHandler(
        chain_executor=chain_executor,
        ledger=ledger,
    )


__all__ = [
    "SUPPORTED_TOKENS",
    "SUPPORTED_CHAINS",
    "ChainReceipt",
    "ChainExecutorPort",
    "LedgerPort",
    "StablecoinPaymentHandler",
    "create_stablecoin_handler",
]

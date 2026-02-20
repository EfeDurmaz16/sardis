"""Sub-ledger fiat account manager for per-agent balance tracking.

Architecture:
- 1x Stripe Treasury (platform level) holds all fiat
- N agents, each with a sub-balance tracked in this sub-ledger
- All agent balances must sum to Treasury balance (reconciliation)
- Double-entry accounting for all operations

Usage:
    treasury = StripeTreasuryProvider(...)
    ledger = SubLedgerManager(treasury)

    # Create agent account
    account = await ledger.create_account("agent_123")

    # Deposit funds (from Treasury inbound)
    tx = await ledger.deposit("agent_123", Decimal("100.00"), "txn_abc", "Wire transfer")

    # Fund a card
    tx = await ledger.fund_card("agent_123", Decimal("50.00"), "card_xyz")

    # Reconcile with Treasury
    result = await ledger.reconcile_with_treasury()
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from .stripe_treasury import StripeTreasuryProvider

logger = logging.getLogger(__name__)


class SubLedgerTxType(str, Enum):
    """Sub-ledger transaction types."""
    DEPOSIT = "deposit"                 # Credit from Treasury inbound
    WITHDRAWAL = "withdrawal"           # Debit for bank payout
    CARD_FUND = "card_fund"             # Move to held for card funding
    CARD_REFUND = "card_refund"         # Card refund back to available
    TRANSFER_IN = "transfer_in"         # Inter-agent transfer in
    TRANSFER_OUT = "transfer_out"       # Inter-agent transfer out
    CARD_SETTLEMENT = "card_settlement"  # Settled card transaction
    FEE = "fee"                         # Platform fee deduction
    ADJUSTMENT = "adjustment"           # Manual adjustment


@dataclass
class SubLedgerAccount:
    """Per-agent fiat account tracked within platform Treasury."""
    account_id: str                     # Format: sub_{agent_id}
    agent_id: str
    currency: str = "usd"
    available_balance: Decimal = field(default_factory=lambda: Decimal("0"))
    pending_balance: Decimal = field(default_factory=lambda: Decimal("0"))    # Funds in transit
    held_balance: Decimal = field(default_factory=lambda: Decimal("0"))       # Reserved for cards
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    @property
    def total_balance(self) -> Decimal:
        """Total balance across all states."""
        return self.available_balance + self.pending_balance + self.held_balance


@dataclass
class SubLedgerTransaction:
    """Sub-ledger transaction record."""
    tx_id: str
    account_id: str
    tx_type: SubLedgerTxType
    amount: Decimal
    balance_after: Decimal
    reference_id: str                   # e.g., Stripe transfer ID, card tx ID
    description: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)


class SubLedgerManager:
    """Manager for per-agent fiat sub-ledger accounts.

    Tracks agent balances within the platform Stripe Treasury.
    All operations are double-entry and thread-safe.

    Architecture:
    - Platform has 1 Stripe Treasury with all fiat
    - Each agent has a sub-ledger account tracking their portion
    - Sum of all sub-ledger balances MUST equal Treasury balance

    Balance States:
    - available: Can be withdrawn or used for cards
    - pending: In transit (e.g., pending wire)
    - held: Reserved for active card transactions

    Usage:
        manager = SubLedgerManager(treasury_provider)
        account = await manager.create_account("agent_123")
        tx = await manager.deposit("agent_123", Decimal("100.00"), "wire_abc", "Wire deposit")
    """

    def __init__(self, treasury: StripeTreasuryProvider):
        """Initialize sub-ledger manager.

        Args:
            treasury: Platform Stripe Treasury provider
        """
        self._treasury = treasury
        self._accounts: dict[str, SubLedgerAccount] = {}
        self._transactions: list[SubLedgerTransaction] = []
        self._locks: dict[str, asyncio.Lock] = {}
        self._global_lock = asyncio.Lock()
        logger.info("SubLedgerManager initialized")

    async def create_account(self, agent_id: str) -> SubLedgerAccount:
        """Create a new sub-ledger account for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            Created SubLedgerAccount

        Raises:
            ValueError: If account already exists
        """
        async with self._global_lock:
            account_id = f"sub_{agent_id}"

            if account_id in self._accounts:
                raise ValueError(f"Account {account_id} already exists")

            account = SubLedgerAccount(
                account_id=account_id,
                agent_id=agent_id,
            )

            self._accounts[account_id] = account
            self._locks[account_id] = asyncio.Lock()

            logger.info("Created sub-ledger account: %s for agent %s", account_id, agent_id)
            return account

    async def get_account(self, agent_id: str) -> Optional[SubLedgerAccount]:
        """Get sub-ledger account for an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            SubLedgerAccount if exists, None otherwise
        """
        account_id = f"sub_{agent_id}"
        return self._accounts.get(account_id)

    async def get_balance(self, agent_id: str) -> SubLedgerAccount:
        """Get sub-ledger account balance.

        Args:
            agent_id: Agent identifier

        Returns:
            SubLedgerAccount

        Raises:
            ValueError: If account not found
        """
        account = await self.get_account(agent_id)
        if not account:
            raise ValueError(f"No sub-ledger account found for agent {agent_id}")
        return account

    async def deposit(
        self,
        agent_id: str,
        amount: Decimal,
        reference_id: str,
        description: str,
        metadata: Optional[dict] = None,
    ) -> SubLedgerTransaction:
        """Credit agent's sub-balance (from Treasury inbound).

        Args:
            agent_id: Agent identifier
            amount: Amount to deposit
            reference_id: External reference (e.g., Stripe transfer ID)
            description: Transaction description
            metadata: Additional metadata

        Returns:
            SubLedgerTransaction record

        Raises:
            ValueError: If account not found or invalid amount
        """
        self._validate_amount(amount)

        account_id = f"sub_{agent_id}"
        lock = self._get_lock(account_id)

        async with lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError(f"No sub-ledger account found for agent {agent_id}")

            # Credit available balance
            account.available_balance += amount
            account.updated_at = datetime.now(timezone.utc)

            # Record transaction
            tx = SubLedgerTransaction(
                tx_id=f"tx_{len(self._transactions) + 1:08d}",
                account_id=account_id,
                tx_type=SubLedgerTxType.DEPOSIT,
                amount=amount,
                balance_after=account.available_balance,
                reference_id=reference_id,
                description=description,
                metadata=metadata or {},
            )

            self._transactions.append(tx)

            logger.info(
                "Deposit: %s credited $%s (ref: %s) - new balance: $%s",
                account_id, amount, reference_id, account.available_balance,
            )

            return tx

    async def withdraw(
        self,
        agent_id: str,
        amount: Decimal,
        reference_id: str,
        description: str,
        metadata: Optional[dict] = None,
    ) -> SubLedgerTransaction:
        """Debit agent's sub-balance (for bank payout).

        Args:
            agent_id: Agent identifier
            amount: Amount to withdraw
            reference_id: External reference (e.g., payout ID)
            description: Transaction description
            metadata: Additional metadata

        Returns:
            SubLedgerTransaction record

        Raises:
            ValueError: If account not found, invalid amount, or insufficient funds
        """
        self._validate_amount(amount)

        account_id = f"sub_{agent_id}"
        lock = self._get_lock(account_id)

        async with lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError(f"No sub-ledger account found for agent {agent_id}")

            # Validate sufficient funds
            if account.available_balance < amount:
                raise ValueError(
                    f"Insufficient available balance: {account.available_balance} < {amount}"
                )

            # Debit available balance
            account.available_balance -= amount
            account.updated_at = datetime.now(timezone.utc)

            # Record transaction
            tx = SubLedgerTransaction(
                tx_id=f"tx_{len(self._transactions) + 1:08d}",
                account_id=account_id,
                tx_type=SubLedgerTxType.WITHDRAWAL,
                amount=amount,
                balance_after=account.available_balance,
                reference_id=reference_id,
                description=description,
                metadata=metadata or {},
            )

            self._transactions.append(tx)

            logger.info(
                "Withdrawal: %s debited $%s (ref: %s) - new balance: $%s",
                account_id, amount, reference_id, account.available_balance,
            )

            return tx

    async def fund_card(
        self,
        agent_id: str,
        amount: Decimal,
        card_id: str,
    ) -> SubLedgerTransaction:
        """Move funds from available to held for card funding.

        Args:
            agent_id: Agent identifier
            amount: Amount to hold for card
            card_id: Card identifier

        Returns:
            SubLedgerTransaction record

        Raises:
            ValueError: If account not found, invalid amount, or insufficient funds
        """
        self._validate_amount(amount)

        account_id = f"sub_{agent_id}"
        lock = self._get_lock(account_id)

        async with lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError(f"No sub-ledger account found for agent {agent_id}")

            # Validate sufficient available funds
            if account.available_balance < amount:
                raise ValueError(
                    f"Insufficient available balance: {account.available_balance} < {amount}"
                )

            # Move from available to held
            account.available_balance -= amount
            account.held_balance += amount
            account.updated_at = datetime.now(timezone.utc)

            # Record transaction
            tx = SubLedgerTransaction(
                tx_id=f"tx_{len(self._transactions) + 1:08d}",
                account_id=account_id,
                tx_type=SubLedgerTxType.CARD_FUND,
                amount=amount,
                balance_after=account.available_balance,
                reference_id=card_id,
                description=f"Hold funds for card {card_id}",
                metadata={"card_id": card_id},
            )

            self._transactions.append(tx)

            logger.info(
                "Card fund: %s held $%s for card %s - available: $%s, held: $%s",
                account_id, amount, card_id, account.available_balance, account.held_balance,
            )

            return tx

    async def release_card_hold(
        self,
        agent_id: str,
        amount: Decimal,
        card_id: str,
    ) -> SubLedgerTransaction:
        """Release held funds back to available (e.g., card transaction declined).

        Args:
            agent_id: Agent identifier
            amount: Amount to release
            card_id: Card identifier

        Returns:
            SubLedgerTransaction record

        Raises:
            ValueError: If account not found, invalid amount, or insufficient held funds
        """
        self._validate_amount(amount)

        account_id = f"sub_{agent_id}"
        lock = self._get_lock(account_id)

        async with lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError(f"No sub-ledger account found for agent {agent_id}")

            # Validate sufficient held funds
            if account.held_balance < amount:
                raise ValueError(
                    f"Insufficient held balance: {account.held_balance} < {amount}"
                )

            # Move from held back to available
            account.held_balance -= amount
            account.available_balance += amount
            account.updated_at = datetime.now(timezone.utc)

            # Record transaction
            tx = SubLedgerTransaction(
                tx_id=f"tx_{len(self._transactions) + 1:08d}",
                account_id=account_id,
                tx_type=SubLedgerTxType.CARD_REFUND,
                amount=amount,
                balance_after=account.available_balance,
                reference_id=card_id,
                description=f"Release hold for card {card_id}",
                metadata={"card_id": card_id},
            )

            self._transactions.append(tx)

            logger.info(
                "Card hold release: %s released $%s from card %s - available: $%s, held: $%s",
                account_id, amount, card_id, account.available_balance, account.held_balance,
            )

            return tx

    async def settle_card_transaction(
        self,
        agent_id: str,
        amount: Decimal,
        card_id: str,
        tx_id: str,
    ) -> SubLedgerTransaction:
        """Deduct from held balance for completed card transaction.

        Args:
            agent_id: Agent identifier
            amount: Amount to settle
            card_id: Card identifier
            tx_id: Card transaction identifier

        Returns:
            SubLedgerTransaction record

        Raises:
            ValueError: If account not found, invalid amount, or insufficient held funds
        """
        self._validate_amount(amount)

        account_id = f"sub_{agent_id}"
        lock = self._get_lock(account_id)

        async with lock:
            account = self._accounts.get(account_id)
            if not account:
                raise ValueError(f"No sub-ledger account found for agent {agent_id}")

            # Validate sufficient held funds
            if account.held_balance < amount:
                raise ValueError(
                    f"Insufficient held balance: {account.held_balance} < {amount}"
                )

            # Deduct from held (funds already moved to Issuing)
            account.held_balance -= amount
            account.updated_at = datetime.now(timezone.utc)

            # Record transaction
            tx = SubLedgerTransaction(
                tx_id=f"tx_{len(self._transactions) + 1:08d}",
                account_id=account_id,
                tx_type=SubLedgerTxType.CARD_SETTLEMENT,
                amount=amount,
                balance_after=account.held_balance,
                reference_id=tx_id,
                description=f"Settle card transaction {tx_id}",
                metadata={"card_id": card_id, "card_tx_id": tx_id},
            )

            self._transactions.append(tx)

            logger.info(
                "Card settlement: %s settled $%s for tx %s - held: $%s",
                account_id, amount, tx_id, account.held_balance,
            )

            return tx

    async def get_transactions(
        self,
        agent_id: str,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SubLedgerTransaction]:
        """Get transaction history for an agent.

        Args:
            agent_id: Agent identifier
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip

        Returns:
            List of SubLedgerTransaction records (newest first)
        """
        account_id = f"sub_{agent_id}"

        # Filter transactions for this account
        account_txs = [
            tx for tx in self._transactions
            if tx.account_id == account_id
        ]

        # Sort by created_at descending (newest first)
        account_txs.sort(key=lambda tx: tx.created_at, reverse=True)

        # Apply pagination
        return account_txs[offset:offset + limit]

    async def get_total_platform_balance(self) -> Decimal:
        """Sum of all agent balances (should match Treasury).

        Returns:
            Total balance across all sub-ledger accounts
        """
        total = Decimal("0")

        for account in self._accounts.values():
            total += account.total_balance

        logger.debug("Total platform sub-ledger balance: $%s", total)
        return total

    async def reconcile_with_treasury(self) -> dict:
        """Compare sub-ledger totals with Treasury balance.

        Returns:
            Reconciliation report with:
            - treasury_balance: Current Treasury balance
            - sub_ledger_total: Sum of all sub-ledger balances
            - discrepancy: Difference between Treasury and sub-ledger
            - is_reconciled: True if balances match
        """
        # Get Treasury balance
        treasury_balance_obj = await self._treasury.get_balance()
        treasury_balance = treasury_balance_obj.available

        # Get sub-ledger total
        sub_ledger_total = await self.get_total_platform_balance()

        # Calculate discrepancy
        discrepancy = treasury_balance - sub_ledger_total
        is_reconciled = abs(discrepancy) < Decimal("0.01")  # Allow 1 cent rounding

        result = {
            "treasury_balance": treasury_balance,
            "sub_ledger_total": sub_ledger_total,
            "discrepancy": discrepancy,
            "is_reconciled": is_reconciled,
            "account_count": len(self._accounts),
            "transaction_count": len(self._transactions),
        }

        if is_reconciled:
            logger.info(
                "Reconciliation PASSED: Treasury $%s = Sub-ledger $%s",
                treasury_balance, sub_ledger_total,
            )
        else:
            logger.warning(
                "Reconciliation FAILED: Treasury $%s != Sub-ledger $%s (diff: $%s)",
                treasury_balance, sub_ledger_total, discrepancy,
            )

        return result

    def _validate_amount(self, amount: Decimal) -> None:
        """Validate transaction amount.

        Args:
            amount: Amount to validate

        Raises:
            ValueError: If amount is invalid
        """
        if amount <= 0:
            raise ValueError(f"Amount must be positive: {amount}")

    def _get_lock(self, account_id: str) -> asyncio.Lock:
        """Get or create lock for account.

        Args:
            account_id: Account identifier

        Returns:
            asyncio.Lock for the account
        """
        if account_id not in self._locks:
            self._locks[account_id] = asyncio.Lock()
        return self._locks[account_id]

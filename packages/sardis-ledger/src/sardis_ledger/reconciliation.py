"""
Blockchain reconciliation and currency conversion support.

This module provides:
- Enhanced reconciliation between ledger and blockchain state
- Currency conversion with rate caching
- Discrepancy detection and resolution
- Automated reconciliation jobs
"""
from __future__ import annotations

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Protocol, Tuple

from .models import (
    AuditAction,
    CurrencyRate,
    LedgerEntry,
    LedgerEntryStatus,
    ReconciliationRecord,
    ReconciliationStatus,
    to_ledger_decimal,
)

logger = logging.getLogger(__name__)


class DiscrepancyType(str, Enum):
    """Types of discrepancies found during reconciliation."""
    AMOUNT_MISMATCH = "amount_mismatch"
    MISSING_ON_CHAIN = "missing_on_chain"
    MISSING_IN_LEDGER = "missing_in_ledger"
    STATUS_MISMATCH = "status_mismatch"
    TIMING_DISCREPANCY = "timing_discrepancy"
    DUPLICATE_ENTRY = "duplicate_entry"
    CURRENCY_MISMATCH = "currency_mismatch"


class ResolutionStrategy(str, Enum):
    """Strategies for resolving discrepancies."""
    AUTO_CORRECT_LEDGER = "auto_correct_ledger"  # Trust blockchain
    AUTO_CORRECT_CHAIN = "auto_correct_chain"  # Trust ledger (rarely used)
    MANUAL_REVIEW = "manual_review"  # Requires human intervention
    CREATE_ADJUSTMENT = "create_adjustment"  # Create adjustment entry
    IGNORE = "ignore"  # Within acceptable tolerance


@dataclass
class ChainTransaction:
    """
    Representation of an on-chain transaction.

    This is the data we fetch from blockchain to reconcile.
    """
    tx_hash: str
    chain: str
    from_address: str
    to_address: str
    amount: Decimal
    currency: str
    block_number: int
    block_timestamp: datetime
    status: str  # "confirmed", "pending", "failed"
    gas_used: Optional[int] = None
    gas_price: Optional[Decimal] = None

    # Token-specific fields
    token_address: Optional[str] = None
    token_decimals: int = 18

    # Raw data for debugging
    raw_data: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        self.amount = to_ledger_decimal(self.amount)
        if self.gas_price:
            self.gas_price = to_ledger_decimal(self.gas_price)


@dataclass
class Discrepancy:
    """
    A detected discrepancy between ledger and chain.
    """
    discrepancy_id: str
    discrepancy_type: DiscrepancyType

    # References
    ledger_entry_id: Optional[str] = None
    chain_tx_hash: Optional[str] = None
    chain: Optional[str] = None

    # Details
    ledger_amount: Optional[Decimal] = None
    chain_amount: Optional[Decimal] = None
    difference: Optional[Decimal] = None

    # Context
    description: str = ""
    severity: str = "medium"  # "low", "medium", "high", "critical"

    # Resolution
    resolution_strategy: Optional[ResolutionStrategy] = None
    is_resolved: bool = False
    resolution_notes: Optional[str] = None
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None

    # Timing
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "discrepancy_id": self.discrepancy_id,
            "discrepancy_type": self.discrepancy_type.value,
            "ledger_entry_id": self.ledger_entry_id,
            "chain_tx_hash": self.chain_tx_hash,
            "chain": self.chain,
            "ledger_amount": str(self.ledger_amount) if self.ledger_amount else None,
            "chain_amount": str(self.chain_amount) if self.chain_amount else None,
            "difference": str(self.difference) if self.difference else None,
            "description": self.description,
            "severity": self.severity,
            "resolution_strategy": self.resolution_strategy.value if self.resolution_strategy else None,
            "is_resolved": self.is_resolved,
            "detected_at": self.detected_at.isoformat(),
        }


class ChainProvider(Protocol):
    """Protocol for blockchain data providers."""

    async def get_transaction(self, tx_hash: str, chain: str) -> Optional[ChainTransaction]:
        """Fetch a single transaction from chain."""
        ...

    async def get_transactions(
        self,
        address: str,
        chain: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> List[ChainTransaction]:
        """Fetch transactions for an address."""
        ...

    async def get_current_block(self, chain: str) -> int:
        """Get current block number."""
        ...


class MockChainProvider:
    """Mock chain provider for testing."""

    def __init__(self):
        self._transactions: Dict[str, ChainTransaction] = {}

    def add_transaction(self, tx: ChainTransaction) -> None:
        self._transactions[f"{tx.chain}:{tx.tx_hash}"] = tx

    async def get_transaction(self, tx_hash: str, chain: str) -> Optional[ChainTransaction]:
        return self._transactions.get(f"{chain}:{tx_hash}")

    async def get_transactions(
        self,
        address: str,
        chain: str,
        from_block: Optional[int] = None,
        to_block: Optional[int] = None,
    ) -> List[ChainTransaction]:
        results = []
        for tx in self._transactions.values():
            if tx.chain != chain:
                continue
            if tx.from_address != address and tx.to_address != address:
                continue
            if from_block and tx.block_number < from_block:
                continue
            if to_block and tx.block_number > to_block:
                continue
            results.append(tx)
        return sorted(results, key=lambda t: t.block_number)

    async def get_current_block(self, chain: str) -> int:
        max_block = 0
        for tx in self._transactions.values():
            if tx.chain == chain and tx.block_number > max_block:
                max_block = tx.block_number
        return max_block


class ReconciliationEngine:
    """
    Engine for reconciling ledger entries with blockchain state.

    Features:
    - Batch reconciliation of entries
    - Discrepancy detection and categorization
    - Configurable tolerance levels
    - Automatic resolution for minor discrepancies
    - Audit trail for all reconciliation actions
    """

    def __init__(
        self,
        chain_provider: ChainProvider,
        amount_tolerance: Decimal = Decimal("0.0001"),  # 0.01% tolerance
        time_tolerance: timedelta = timedelta(minutes=5),
        auto_resolve_threshold: Decimal = Decimal("0.01"),  # Auto-resolve under $0.01
    ):
        self.chain_provider = chain_provider
        self.amount_tolerance = amount_tolerance
        self.time_tolerance = time_tolerance
        self.auto_resolve_threshold = auto_resolve_threshold

        # Storage
        self._records: Dict[str, ReconciliationRecord] = {}
        self._discrepancies: Dict[str, Discrepancy] = {}

        # Statistics
        self._stats = {
            "total_reconciled": 0,
            "matched": 0,
            "discrepancies_found": 0,
            "auto_resolved": 0,
        }

        logger.info(
            f"ReconciliationEngine initialized: tolerance={amount_tolerance}, "
            f"auto_resolve_threshold={auto_resolve_threshold}"
        )

    async def reconcile_entry(
        self,
        entry: LedgerEntry,
        actor_id: Optional[str] = None,
    ) -> ReconciliationRecord:
        """
        Reconcile a single ledger entry with blockchain.

        Args:
            entry: The ledger entry to reconcile
            actor_id: ID of actor performing reconciliation

        Returns:
            ReconciliationRecord with results
        """
        if not entry.chain_tx_hash or not entry.chain:
            raise ValueError(f"Entry {entry.entry_id} has no chain reference")

        # Fetch chain transaction
        chain_tx = await self.chain_provider.get_transaction(
            entry.chain_tx_hash, entry.chain
        )

        record = ReconciliationRecord(
            ledger_entry_id=entry.entry_id,
            ledger_amount=entry.amount,
            ledger_currency=entry.currency,
            chain=entry.chain,
            chain_tx_hash=entry.chain_tx_hash,
        )

        if not chain_tx:
            # Transaction not found on chain
            record.status = ReconciliationStatus.UNMATCHED
            record.discrepancy_reason = "Transaction not found on chain"

            self._create_discrepancy(
                discrepancy_type=DiscrepancyType.MISSING_ON_CHAIN,
                ledger_entry_id=entry.entry_id,
                chain_tx_hash=entry.chain_tx_hash,
                chain=entry.chain,
                ledger_amount=entry.amount,
                description=f"Ledger entry {entry.entry_id} has no matching chain transaction",
                severity="high",
            )

            self._stats["discrepancies_found"] += 1
        else:
            # Found on chain, compare details
            record.chain_amount = chain_tx.amount
            record.chain_block_number = chain_tx.block_number
            record.chain_timestamp = chain_tx.block_timestamp

            # Calculate discrepancy
            record.calculate_discrepancy()

            if record.discrepancy_amount == 0:
                # Perfect match
                record.status = ReconciliationStatus.MATCHED
                self._stats["matched"] += 1
            elif record.discrepancy_amount <= self.amount_tolerance * entry.amount:
                # Within tolerance
                record.status = ReconciliationStatus.MATCHED
                record.discrepancy_reason = f"Amount within tolerance ({record.discrepancy_amount})"
                self._stats["matched"] += 1
            else:
                # Significant discrepancy
                record.status = ReconciliationStatus.UNMATCHED
                record.discrepancy_reason = f"Amount mismatch: ledger={entry.amount}, chain={chain_tx.amount}"

                discrepancy = self._create_discrepancy(
                    discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                    ledger_entry_id=entry.entry_id,
                    chain_tx_hash=entry.chain_tx_hash,
                    chain=entry.chain,
                    ledger_amount=entry.amount,
                    chain_amount=chain_tx.amount,
                    difference=record.discrepancy_amount,
                    description=f"Amount mismatch of {record.discrepancy_amount}",
                    severity=self._determine_severity(record.discrepancy_amount),
                )

                # Try auto-resolution for small discrepancies
                if record.discrepancy_amount <= self.auto_resolve_threshold:
                    discrepancy.resolution_strategy = ResolutionStrategy.IGNORE
                    discrepancy.is_resolved = True
                    discrepancy.resolution_notes = "Auto-resolved: below threshold"
                    discrepancy.resolved_at = datetime.now(timezone.utc)
                    record.status = ReconciliationStatus.RESOLVED
                    self._stats["auto_resolved"] += 1
                else:
                    discrepancy.resolution_strategy = ResolutionStrategy.MANUAL_REVIEW
                    self._stats["discrepancies_found"] += 1

        record.reconciled_at = datetime.now(timezone.utc)
        self._records[record.reconciliation_id] = record
        self._stats["total_reconciled"] += 1

        logger.info(
            f"Reconciled entry {entry.entry_id}: status={record.status.value}, "
            f"discrepancy={record.discrepancy_amount}"
        )

        return record

    async def reconcile_batch(
        self,
        entries: List[LedgerEntry],
        actor_id: Optional[str] = None,
        concurrency: int = 10,
    ) -> List[ReconciliationRecord]:
        """
        Reconcile multiple entries concurrently.

        Args:
            entries: List of entries to reconcile
            actor_id: ID of actor performing reconciliation
            concurrency: Maximum concurrent reconciliations

        Returns:
            List of ReconciliationRecord results
        """
        semaphore = asyncio.Semaphore(concurrency)

        async def reconcile_with_limit(entry: LedgerEntry) -> ReconciliationRecord:
            async with semaphore:
                try:
                    return await self.reconcile_entry(entry, actor_id)
                except Exception as e:
                    logger.error(f"Error reconciling {entry.entry_id}: {e}")
                    # Return a failed record
                    record = ReconciliationRecord(
                        ledger_entry_id=entry.entry_id,
                        ledger_amount=entry.amount,
                        ledger_currency=entry.currency,
                        chain=entry.chain or "",
                        chain_tx_hash=entry.chain_tx_hash or "",
                        status=ReconciliationStatus.UNMATCHED,
                        discrepancy_reason=f"Reconciliation error: {e}",
                    )
                    return record

        tasks = [reconcile_with_limit(entry) for entry in entries]
        results = await asyncio.gather(*tasks)

        logger.info(
            f"Batch reconciliation complete: {len(results)} entries, "
            f"matched={sum(1 for r in results if r.status == ReconciliationStatus.MATCHED)}"
        )

        return list(results)

    def _create_discrepancy(
        self,
        discrepancy_type: DiscrepancyType,
        ledger_entry_id: Optional[str] = None,
        chain_tx_hash: Optional[str] = None,
        chain: Optional[str] = None,
        ledger_amount: Optional[Decimal] = None,
        chain_amount: Optional[Decimal] = None,
        difference: Optional[Decimal] = None,
        description: str = "",
        severity: str = "medium",
    ) -> Discrepancy:
        """Create and store a discrepancy record."""
        import uuid

        discrepancy = Discrepancy(
            discrepancy_id=f"disc_{uuid.uuid4().hex[:16]}",
            discrepancy_type=discrepancy_type,
            ledger_entry_id=ledger_entry_id,
            chain_tx_hash=chain_tx_hash,
            chain=chain,
            ledger_amount=ledger_amount,
            chain_amount=chain_amount,
            difference=difference,
            description=description,
            severity=severity,
        )

        self._discrepancies[discrepancy.discrepancy_id] = discrepancy

        logger.warning(
            f"Discrepancy detected: {discrepancy_type.value}, "
            f"entry={ledger_entry_id}, severity={severity}"
        )

        return discrepancy

    def _determine_severity(self, amount: Decimal) -> str:
        """Determine severity based on discrepancy amount."""
        if amount < Decimal("1"):
            return "low"
        elif amount < Decimal("100"):
            return "medium"
        elif amount < Decimal("10000"):
            return "high"
        else:
            return "critical"

    def resolve_discrepancy(
        self,
        discrepancy_id: str,
        strategy: ResolutionStrategy,
        notes: str,
        resolved_by: str,
    ) -> Discrepancy:
        """
        Resolve a discrepancy.

        Args:
            discrepancy_id: ID of discrepancy to resolve
            strategy: Resolution strategy used
            notes: Resolution notes
            resolved_by: ID of person/system resolving

        Returns:
            Updated Discrepancy
        """
        discrepancy = self._discrepancies.get(discrepancy_id)
        if not discrepancy:
            raise ValueError(f"Discrepancy not found: {discrepancy_id}")

        discrepancy.resolution_strategy = strategy
        discrepancy.is_resolved = True
        discrepancy.resolution_notes = notes
        discrepancy.resolved_at = datetime.now(timezone.utc)
        discrepancy.resolved_by = resolved_by

        logger.info(
            f"Resolved discrepancy {discrepancy_id}: strategy={strategy.value}, "
            f"resolved_by={resolved_by}"
        )

        return discrepancy

    def get_discrepancies(
        self,
        include_resolved: bool = False,
        severity: Optional[str] = None,
        discrepancy_type: Optional[DiscrepancyType] = None,
    ) -> List[Discrepancy]:
        """Get discrepancies with filtering."""
        results = []
        for d in self._discrepancies.values():
            if not include_resolved and d.is_resolved:
                continue
            if severity and d.severity != severity:
                continue
            if discrepancy_type and d.discrepancy_type != discrepancy_type:
                continue
            results.append(d)

        return sorted(results, key=lambda d: d.detected_at, reverse=True)

    def get_statistics(self) -> Dict[str, Any]:
        """Get reconciliation statistics."""
        return {
            **self._stats,
            "pending_discrepancies": len([d for d in self._discrepancies.values() if not d.is_resolved]),
            "records_count": len(self._records),
        }


class CurrencyConverter:
    """
    Currency conversion with rate caching and history.

    Features:
    - Rate caching with TTL
    - Multiple rate sources support
    - Bid/ask spread handling
    - Conversion history tracking
    """

    def __init__(
        self,
        default_source: str = "internal",
        cache_ttl: timedelta = timedelta(minutes=5),
    ):
        self.default_source = default_source
        self.cache_ttl = cache_ttl

        # Rate storage
        self._rates: Dict[str, CurrencyRate] = {}
        self._rate_history: List[CurrencyRate] = []

        # Conversion history
        self._conversions: List[Dict[str, Any]] = []

        # Initialize with common stablecoin rates
        self._initialize_default_rates()

        logger.info(f"CurrencyConverter initialized: cache_ttl={cache_ttl}")

    def _initialize_default_rates(self) -> None:
        """Set up default rates for common pairs."""
        default_pairs = [
            ("USD", "USDC", Decimal("1")),
            ("USD", "USDT", Decimal("1")),
            ("USDC", "USDT", Decimal("1")),
            ("USD", "DAI", Decimal("1")),
            ("ETH", "USD", Decimal("2500")),  # Example rate
            ("BTC", "USD", Decimal("45000")),  # Example rate
        ]

        for from_curr, to_curr, rate in default_pairs:
            self.set_rate(from_curr, to_curr, rate, source="default")

    def _make_key(self, from_currency: str, to_currency: str) -> str:
        """Create cache key for currency pair."""
        return f"{from_currency.upper()}:{to_currency.upper()}"

    def set_rate(
        self,
        from_currency: str,
        to_currency: str,
        rate: Decimal,
        source: Optional[str] = None,
        bid: Optional[Decimal] = None,
        ask: Optional[Decimal] = None,
        valid_until: Optional[datetime] = None,
    ) -> CurrencyRate:
        """
        Set exchange rate for a currency pair.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            rate: Exchange rate (how many to_currency per from_currency)
            source: Rate source identifier
            bid: Bid price (buy price)
            ask: Ask price (sell price)
            valid_until: When rate expires

        Returns:
            Created CurrencyRate
        """
        rate = to_ledger_decimal(rate)
        inverse_rate = to_ledger_decimal(Decimal("1") / rate) if rate != 0 else Decimal("0")

        currency_rate = CurrencyRate(
            from_currency=from_currency.upper(),
            to_currency=to_currency.upper(),
            rate=rate,
            inverse_rate=inverse_rate,
            source=source or self.default_source,
            valid_until=valid_until or datetime.now(timezone.utc) + self.cache_ttl,
            bid=to_ledger_decimal(bid) if bid else None,
            ask=to_ledger_decimal(ask) if ask else None,
        )

        if bid and ask:
            currency_rate.spread = to_ledger_decimal(ask - bid)

        # Store forward and reverse rates
        key = self._make_key(from_currency, to_currency)
        reverse_key = self._make_key(to_currency, from_currency)

        self._rates[key] = currency_rate

        # Create inverse rate
        inverse_currency_rate = CurrencyRate(
            from_currency=to_currency.upper(),
            to_currency=from_currency.upper(),
            rate=inverse_rate,
            inverse_rate=rate,
            source=source or self.default_source,
            valid_until=valid_until or datetime.now(timezone.utc) + self.cache_ttl,
        )
        self._rates[reverse_key] = inverse_currency_rate

        # Add to history
        self._rate_history.append(currency_rate)

        logger.debug(f"Set rate: {from_currency}/{to_currency} = {rate}")

        return currency_rate

    def get_rate(
        self,
        from_currency: str,
        to_currency: str,
        at_time: Optional[datetime] = None,
    ) -> Optional[CurrencyRate]:
        """
        Get exchange rate for currency pair.

        Args:
            from_currency: Source currency code
            to_currency: Target currency code
            at_time: Get rate valid at this time (None = current)

        Returns:
            CurrencyRate if found and valid, None otherwise
        """
        if from_currency.upper() == to_currency.upper():
            # Same currency, rate is 1
            return CurrencyRate(
                from_currency=from_currency.upper(),
                to_currency=to_currency.upper(),
                rate=Decimal("1"),
                inverse_rate=Decimal("1"),
            )

        key = self._make_key(from_currency, to_currency)
        rate = self._rates.get(key)

        if rate and rate.is_valid(at_time):
            return rate

        return None

    def convert(
        self,
        amount: Decimal,
        from_currency: str,
        to_currency: str,
        at_time: Optional[datetime] = None,
        record_conversion: bool = True,
    ) -> Tuple[Decimal, CurrencyRate]:
        """
        Convert amount between currencies.

        Args:
            amount: Amount to convert
            from_currency: Source currency code
            to_currency: Target currency code
            at_time: Use rate valid at this time
            record_conversion: Whether to log the conversion

        Returns:
            Tuple of (converted_amount, rate_used)

        Raises:
            ValueError: If no valid rate available
        """
        amount = to_ledger_decimal(amount)

        rate = self.get_rate(from_currency, to_currency, at_time)
        if not rate:
            raise ValueError(f"No valid rate for {from_currency}/{to_currency}")

        converted = rate.convert(amount)

        if record_conversion:
            self._conversions.append({
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "from_currency": from_currency,
                "to_currency": to_currency,
                "from_amount": str(amount),
                "to_amount": str(converted),
                "rate": str(rate.rate),
                "rate_source": rate.source,
            })

        logger.debug(f"Converted {amount} {from_currency} -> {converted} {to_currency}")

        return converted, rate

    def get_conversion_history(
        self,
        from_currency: Optional[str] = None,
        to_currency: Optional[str] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Get conversion history with optional filtering."""
        results = []
        for conv in reversed(self._conversions):
            if from_currency and conv["from_currency"] != from_currency.upper():
                continue
            if to_currency and conv["to_currency"] != to_currency.upper():
                continue
            results.append(conv)
            if len(results) >= limit:
                break
        return results

    def get_rate_history(
        self,
        from_currency: str,
        to_currency: str,
        from_time: Optional[datetime] = None,
        to_time: Optional[datetime] = None,
    ) -> List[CurrencyRate]:
        """Get historical rates for a currency pair."""
        from_curr = from_currency.upper()
        to_curr = to_currency.upper()

        results = []
        for rate in self._rate_history:
            if rate.from_currency != from_curr or rate.to_currency != to_curr:
                continue
            if from_time and rate.valid_from < from_time:
                continue
            if to_time and rate.valid_from > to_time:
                continue
            results.append(rate)

        return sorted(results, key=lambda r: r.valid_from)

    def clear_expired_rates(self) -> int:
        """Remove expired rates from cache. Returns count of removed rates."""
        now = datetime.now(timezone.utc)
        expired_keys = [
            key for key, rate in self._rates.items()
            if not rate.is_valid(now)
        ]

        for key in expired_keys:
            del self._rates[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired rates")

        return len(expired_keys)


class ReconciliationScheduler:
    """
    Scheduler for automated reconciliation jobs.

    Runs periodic reconciliation and cleanup tasks.
    """

    def __init__(
        self,
        reconciliation_engine: ReconciliationEngine,
        currency_converter: CurrencyConverter,
        reconciliation_interval: timedelta = timedelta(minutes=15),
        rate_refresh_interval: timedelta = timedelta(minutes=5),
    ):
        self.reconciliation_engine = reconciliation_engine
        self.currency_converter = currency_converter
        self.reconciliation_interval = reconciliation_interval
        self.rate_refresh_interval = rate_refresh_interval

        self._running = False
        self._tasks: List[asyncio.Task] = []

        # Callbacks for fetching data
        self._entry_fetcher: Optional[Callable[[], List[LedgerEntry]]] = None
        self._rate_fetcher: Optional[Callable[[], List[Tuple[str, str, Decimal]]]] = None

    def set_entry_fetcher(self, fetcher: Callable[[], List[LedgerEntry]]) -> None:
        """Set callback to fetch entries needing reconciliation."""
        self._entry_fetcher = fetcher

    def set_rate_fetcher(self, fetcher: Callable[[], List[Tuple[str, str, Decimal]]]) -> None:
        """Set callback to fetch current exchange rates."""
        self._rate_fetcher = fetcher

    async def start(self) -> None:
        """Start the scheduler."""
        if self._running:
            return

        self._running = True

        self._tasks = [
            asyncio.create_task(self._reconciliation_loop()),
            asyncio.create_task(self._rate_refresh_loop()),
        ]

        logger.info("ReconciliationScheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

        for task in self._tasks:
            task.cancel()

        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self._tasks = []
        logger.info("ReconciliationScheduler stopped")

    async def _reconciliation_loop(self) -> None:
        """Background loop for reconciliation."""
        while self._running:
            try:
                if self._entry_fetcher:
                    entries = self._entry_fetcher()
                    if entries:
                        await self.reconciliation_engine.reconcile_batch(entries)
            except Exception as e:
                logger.error(f"Reconciliation loop error: {e}")

            await asyncio.sleep(self.reconciliation_interval.total_seconds())

    async def _rate_refresh_loop(self) -> None:
        """Background loop for rate refresh."""
        while self._running:
            try:
                # Clear expired rates
                self.currency_converter.clear_expired_rates()

                # Fetch new rates
                if self._rate_fetcher:
                    rates = self._rate_fetcher()
                    for from_curr, to_curr, rate in rates:
                        self.currency_converter.set_rate(from_curr, to_curr, rate)
            except Exception as e:
                logger.error(f"Rate refresh loop error: {e}")

            await asyncio.sleep(self.rate_refresh_interval.total_seconds())


__all__ = [
    # Types
    "DiscrepancyType",
    "ResolutionStrategy",
    "ChainTransaction",
    "Discrepancy",
    # Protocols
    "ChainProvider",
    "MockChainProvider",
    # Engines
    "ReconciliationEngine",
    "CurrencyConverter",
    "ReconciliationScheduler",
]

"""
Ledger reconciliation for verifying balance integrity.

Provides tools to:
- Reconcile internal ledger against blockchain state
- Verify double-entry bookkeeping invariants
- Detect and report discrepancies
- Generate reconciliation reports
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
import uuid

from .ledger_service import LedgerService
from .models import LedgerCheckpoint, BalanceProof


@dataclass
class ReconciliationResult:
    """Result of a reconciliation check."""
    
    reconciliation_id: str = field(default_factory=lambda: f"rec_{uuid.uuid4().hex[:16]}")
    
    # Overall status
    is_reconciled: bool = True
    
    # Discrepancies found
    discrepancies: list[dict] = field(default_factory=list)
    
    # Statistics
    wallets_checked: int = 0
    entries_verified: int = 0
    total_volume_checked: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    def add_discrepancy(
        self,
        wallet_id: str,
        currency: str,
        expected: Decimal,
        actual: Decimal,
        source: str,
        details: Optional[str] = None
    ):
        """Add a discrepancy to the result."""
        self.discrepancies.append({
            "wallet_id": wallet_id,
            "currency": currency,
            "expected": str(expected),
            "actual": str(actual),
            "difference": str(actual - expected),
            "source": source,
            "details": details,
            "detected_at": datetime.now(timezone.utc).isoformat(),
        })
        self.is_reconciled = False
    
    def complete(self):
        """Mark reconciliation as complete."""
        self.completed_at = datetime.now(timezone.utc)


class ReconciliationService:
    """
    Service for reconciling ledger balances.
    
    Performs various integrity checks:
    1. Internal consistency (double-entry balances)
    2. Checkpoint verification
    3. On-chain reconciliation (when blockchain integration is available)
    """
    
    def __init__(self, ledger_service: LedgerService):
        """
        Initialize the reconciliation service.
        
        Args:
            ledger_service: The ledger service to reconcile
        """
        self._ledger = ledger_service
    
    def reconcile_all(self) -> ReconciliationResult:
        """
        Perform full reconciliation of all wallets.
        
        Checks:
        1. Hash chain integrity
        2. Balance recalculation from entries
        3. Double-entry balance (sum of all entries = 0)
        """
        result = ReconciliationResult()
        
        # Check hash chain integrity
        is_valid, error = self._ledger.verify_integrity()
        if not is_valid:
            result.add_discrepancy(
                wallet_id="*",
                currency="*",
                expected=Decimal("0"),
                actual=Decimal("0"),
                source="hash_chain",
                details=error,
            )
        
        # Get all wallets from balances
        all_wallets = set(self._ledger._balances.keys())
        
        for wallet_id in all_wallets:
            for currency, cached_balance in self._ledger._balances[wallet_id].items():
                # Recalculate balance from entries
                proof = self._ledger.get_balance_proof(wallet_id, currency)
                
                if proof.balance != cached_balance:
                    result.add_discrepancy(
                        wallet_id=wallet_id,
                        currency=currency,
                        expected=proof.balance,
                        actual=cached_balance,
                        source="balance_cache",
                        details=f"Cached balance doesn't match entry sum. "
                                f"Entries: {len(proof.contributing_entries)}",
                    )
                
                result.wallets_checked += 1
        
        # Verify global double-entry balance
        # Sum of all entries should be zero (debits = credits)
        entries = self._ledger._entries
        total_sum = sum(e.signed_amount() for e in entries)
        
        if total_sum != Decimal("0"):
            result.add_discrepancy(
                wallet_id="*",
                currency="*",
                expected=Decimal("0"),
                actual=total_sum,
                source="double_entry",
                details="Sum of all entries is not zero - double-entry violation",
            )
        
        result.entries_verified = len(entries)
        result.total_volume_checked = sum(e.amount for e in entries if e.is_credit())
        result.complete()
        
        return result
    
    def reconcile_wallet(self, wallet_id: str) -> ReconciliationResult:
        """Reconcile a single wallet's balances."""
        result = ReconciliationResult()
        
        balances = self._ledger.get_all_balances(wallet_id)
        
        for currency, cached_balance in balances.items():
            proof = self._ledger.get_balance_proof(wallet_id, currency)
            
            if proof.balance != cached_balance:
                result.add_discrepancy(
                    wallet_id=wallet_id,
                    currency=currency,
                    expected=proof.balance,
                    actual=cached_balance,
                    source="balance_cache",
                )
            
            result.wallets_checked += 1
            result.entries_verified += len(proof.contributing_entries)
        
        result.complete()
        return result
    
    def reconcile_checkpoint(self, checkpoint: LedgerCheckpoint) -> ReconciliationResult:
        """
        Verify balances against a checkpoint.
        
        Useful for periodic verification that balances haven't drifted.
        """
        result = ReconciliationResult()
        
        # Verify checkpoint checksum
        computed_checksum = checkpoint.compute_checksum()
        if computed_checksum != checkpoint.checksum:
            result.add_discrepancy(
                wallet_id="*",
                currency="*",
                expected=Decimal("0"),
                actual=Decimal("0"),
                source="checkpoint_integrity",
                details=f"Checkpoint checksum mismatch: expected {checkpoint.checksum}, "
                       f"got {computed_checksum}",
            )
        
        # Verify each wallet balance
        for wallet_id, currencies in checkpoint.wallet_balances.items():
            for currency, checkpoint_balance in currencies.items():
                current_balance = self._ledger.get_balance(wallet_id, currency)
                
                # Only flag if current is LESS than checkpoint (funds shouldn't disappear)
                # More funds is OK (new deposits)
                if current_balance < checkpoint_balance:
                    result.add_discrepancy(
                        wallet_id=wallet_id,
                        currency=currency,
                        expected=checkpoint_balance,
                        actual=current_balance,
                        source="checkpoint_comparison",
                        details="Balance decreased unexpectedly since checkpoint",
                    )
                
                result.wallets_checked += 1
        
        result.entries_verified = checkpoint.entries_count
        result.complete()
        return result
    
    def reconcile_against_chain(
        self,
        wallet_id: str,
        chain: str,
        on_chain_balance: Decimal,
        currency: str = "USDC"
    ) -> ReconciliationResult:
        """
        Reconcile internal balance against on-chain balance.
        
        This is called when we have access to blockchain state
        to verify our internal ledger matches reality.
        
        Args:
            wallet_id: Internal wallet ID
            chain: Blockchain name
            on_chain_balance: Balance reported by blockchain
            currency: Token currency
        """
        result = ReconciliationResult()
        
        internal_balance = self._ledger.get_balance(wallet_id, currency)
        
        # Allow small difference due to pending transactions
        tolerance = Decimal("0.01")
        difference = abs(internal_balance - on_chain_balance)
        
        if difference > tolerance:
            result.add_discrepancy(
                wallet_id=wallet_id,
                currency=currency,
                expected=on_chain_balance,
                actual=internal_balance,
                source=f"on_chain_{chain}",
                details=f"Internal balance differs from {chain} by {difference}",
            )
        
        result.wallets_checked = 1
        result.complete()
        return result
    
    def generate_daily_report(self) -> dict:
        """
        Generate a daily reconciliation report.
        
        Returns a summary suitable for logging or alerting.
        """
        full_reconciliation = self.reconcile_all()
        checkpoint = self._ledger.get_latest_checkpoint()
        
        report = {
            "report_date": datetime.now(timezone.utc).isoformat(),
            "status": "OK" if full_reconciliation.is_reconciled else "DISCREPANCIES_FOUND",
            "wallets_checked": full_reconciliation.wallets_checked,
            "entries_verified": full_reconciliation.entries_verified,
            "total_volume": str(full_reconciliation.total_volume_checked),
            "discrepancies_count": len(full_reconciliation.discrepancies),
            "discrepancies": full_reconciliation.discrepancies,
            "latest_checkpoint": {
                "id": checkpoint.checkpoint_id if checkpoint else None,
                "date": checkpoint.checkpoint_date.isoformat() if checkpoint else None,
                "sequence": checkpoint.last_sequence_number if checkpoint else 0,
            },
            "integrity_check": {
                "hash_chain_valid": self._ledger.verify_integrity()[0],
            },
        }
        
        return report


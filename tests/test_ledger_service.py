"""Tests for the LedgerService with double-entry bookkeeping."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone

from sardis_core.ledger.ledger_service import LedgerService, TransferResult
from sardis_core.ledger.models import EntryType, EntryStatus


class TestLedgerService:
    """Test suite for LedgerService."""
    
    @pytest.fixture
    def ledger(self):
        """Create a fresh ledger for each test."""
        return LedgerService()
    
    @pytest.fixture
    def funded_ledger(self, ledger):
        """Create a ledger with pre-funded wallets."""
        ledger.set_balance("wallet_a", "USDC", Decimal("1000.00"))
        ledger.set_balance("wallet_b", "USDC", Decimal("500.00"))
        ledger.set_balance("fee_wallet", "USDC", Decimal("0.00"))
        return ledger
    
    # ==================== Basic Transfer Tests ====================
    
    def test_transfer_success(self, funded_ledger):
        """Test successful transfer between wallets."""
        result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="wallet_b",
            amount=Decimal("100.00"),
            currency="USDC"
        )
        
        assert result.success is True
        assert result.ledger_transaction is not None
        assert result.ledger_transaction.is_balanced()
        
        # Check balances updated
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("900.00")
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("600.00")
    
    def test_transfer_with_fee(self, funded_ledger):
        """Test transfer with fee collection."""
        # Fee transfers are handled separately in the current implementation
        # First do the main transfer
        result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="wallet_b",
            amount=Decimal("100.00"),
            currency="USDC"
        )
        
        assert result.success is True
        
        # Then do the fee transfer
        fee_result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="fee_wallet",
            amount=Decimal("1.00"),
            currency="USDC"
        )
        
        assert fee_result.success is True
        
        # Sender pays amount + fee
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("899.00")
        # Recipient gets amount
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("600.00")
        # Fee wallet gets fee
        assert funded_ledger.get_balance("fee_wallet", "USDC") == Decimal("1.00")
    
    def test_transfer_insufficient_balance(self, funded_ledger):
        """Test transfer fails with insufficient balance."""
        result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="wallet_b",
            amount=Decimal("2000.00"),  # More than wallet_a has
            currency="USDC"
        )
        
        assert result.success is False
        assert "Insufficient" in result.error
        
        # Balances unchanged
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("1000.00")
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("500.00")
    
    def test_transfer_zero_amount(self, funded_ledger):
        """Test transfer with zero amount fails."""
        result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="wallet_b",
            amount=Decimal("0.00"),
            currency="USDC"
        )
        
        assert result.success is False
        assert "positive" in result.error.lower()
    
    def test_transfer_negative_amount(self, funded_ledger):
        """Test transfer with negative amount fails."""
        result = funded_ledger.transfer(
            from_wallet_id="wallet_a",
            to_wallet_id="wallet_b",
            amount=Decimal("-50.00"),
            currency="USDC"
        )
        
        assert result.success is False
    
    # ==================== Double-Entry Verification ====================
    
    def test_double_entry_balance(self, funded_ledger):
        """Verify double-entry bookkeeping - debits equal credits."""
        # Perform several transfers
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("50.00"))
        funded_ledger.transfer("wallet_b", "wallet_a", Decimal("25.00"))
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("10.00"), fee=Decimal("0.50"), fee_wallet_id="fee_wallet")
        
        # Get all entries and verify balance
        entries = funded_ledger._entries
        
        total_debits = sum(e.amount for e in entries if e.is_debit())
        total_credits = sum(e.amount for e in entries if e.is_credit())
        
        assert total_debits == total_credits, "Double-entry: debits must equal credits"
    
    def test_entry_checksums(self, funded_ledger):
        """Verify entry checksums form a valid chain."""
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("50.00"))
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("25.00"))
        
        is_valid, error = funded_ledger.verify_integrity()
        
        assert is_valid is True
        assert error is None
    
    def test_entries_are_append_only(self, funded_ledger):
        """Verify entries cannot be modified after creation."""
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("50.00"))
        
        initial_count = len(funded_ledger._entries)
        initial_checksums = [e.checksum for e in funded_ledger._entries]
        
        # More transfers
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("25.00"))
        
        # Original entries should be unchanged
        for i, checksum in enumerate(initial_checksums):
            assert funded_ledger._entries[i].checksum == checksum
        
        # New entries added
        assert len(funded_ledger._entries) > initial_count
    
    # ==================== Refund Tests ====================
    
    def test_refund_full(self, funded_ledger):
        """Test full refund of a transaction."""
        # Original transfer
        result = funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        tx_id = result.ledger_transaction.transaction_id
        
        # Refund
        refund_result = funded_ledger.refund(tx_id)
        
        assert refund_result.success is True
        
        # Balances restored
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("1000.00")
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("500.00")
    
    def test_refund_partial(self, funded_ledger):
        """Test partial refund of a transaction."""
        result = funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        tx_id = result.ledger_transaction.transaction_id
        
        refund_result = funded_ledger.refund(tx_id, amount=Decimal("40.00"))
        
        assert refund_result.success is True
        
        # Partial refund
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("940.00")
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("560.00")
    
    def test_refund_exceeds_original(self, funded_ledger):
        """Test refund fails if amount exceeds original."""
        result = funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        tx_id = result.ledger_transaction.transaction_id
        
        refund_result = funded_ledger.refund(tx_id, amount=Decimal("200.00"))
        
        assert refund_result.success is False
        assert "exceeds" in refund_result.error.lower()
    
    def test_refund_nonexistent_transaction(self, funded_ledger):
        """Test refund of non-existent transaction fails."""
        refund_result = funded_ledger.refund("nonexistent_tx_123")
        
        assert refund_result.success is False
        assert "not found" in refund_result.error.lower()
    
    # ==================== Hold Tests ====================
    
    def test_create_hold(self, funded_ledger):
        """Test creating a hold on funds."""
        result = funded_ledger.create_hold(
            wallet_id="wallet_a",
            amount=Decimal("200.00"),
            currency="USDC"
        )
        
        assert result.success is True
        
        # Balance unchanged but available reduced
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("1000.00")
        assert funded_ledger.get_held_amount("wallet_a", "USDC") == Decimal("200.00")
        assert funded_ledger.get_available_balance("wallet_a", "USDC") == Decimal("800.00")
    
    def test_capture_hold(self, funded_ledger):
        """Test capturing a hold."""
        # Create hold
        hold_result = funded_ledger.create_hold("wallet_a", Decimal("200.00"))
        hold_tx_id = hold_result.ledger_transaction.transaction_id
        
        # Capture hold
        capture_result = funded_ledger.capture_hold(
            hold_tx_id=hold_tx_id,
            to_wallet_id="wallet_b",
            amount=Decimal("200.00")
        )
        
        assert capture_result.success is True
        
        # Balances updated
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("800.00")
        assert funded_ledger.get_balance("wallet_b", "USDC") == Decimal("700.00")
        assert funded_ledger.get_held_amount("wallet_a", "USDC") == Decimal("0.00")
    
    def test_capture_partial_hold(self, funded_ledger):
        """Test capturing less than the full hold."""
        hold_result = funded_ledger.create_hold("wallet_a", Decimal("200.00"))
        hold_tx_id = hold_result.ledger_transaction.transaction_id
        
        # Capture only part
        capture_result = funded_ledger.capture_hold(
            hold_tx_id=hold_tx_id,
            to_wallet_id="wallet_b",
            amount=Decimal("150.00")
        )
        
        assert capture_result.success is True
        
        # Remaining 50 should be released (no longer held)
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("850.00")
        assert funded_ledger.get_held_amount("wallet_a", "USDC") == Decimal("0.00")
    
    def test_void_hold(self, funded_ledger):
        """Test voiding a hold."""
        hold_result = funded_ledger.create_hold("wallet_a", Decimal("200.00"))
        hold_tx_id = hold_result.ledger_transaction.transaction_id
        
        void_result = funded_ledger.void_hold(hold_tx_id)
        
        assert void_result.success is True
        
        # Funds released
        assert funded_ledger.get_balance("wallet_a", "USDC") == Decimal("1000.00")
        assert funded_ledger.get_held_amount("wallet_a", "USDC") == Decimal("0.00")
        assert funded_ledger.get_available_balance("wallet_a", "USDC") == Decimal("1000.00")
    
    def test_hold_insufficient_balance(self, funded_ledger):
        """Test hold fails with insufficient balance."""
        result = funded_ledger.create_hold("wallet_a", Decimal("2000.00"))
        
        assert result.success is False
        assert "Insufficient" in result.error
    
    # ==================== Checkpoint Tests ====================
    
    def test_create_checkpoint(self, funded_ledger):
        """Test creating a checkpoint."""
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        
        checkpoint = funded_ledger.create_checkpoint()
        
        assert checkpoint is not None
        assert checkpoint.last_sequence_number > 0
        assert checkpoint.entries_count > 0
        assert "wallet_a" in checkpoint.wallet_balances
        assert "wallet_b" in checkpoint.wallet_balances
    
    def test_checkpoint_verification(self, funded_ledger):
        """Test checkpoint can be used for verification."""
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        checkpoint = funded_ledger.create_checkpoint()
        
        # Verify checkpoint checksum
        computed = checkpoint.compute_checksum()
        assert computed == checkpoint.checksum
    
    # ==================== Balance Proof Tests ====================
    
    def test_balance_proof(self, funded_ledger):
        """Test generating balance proof for audit."""
        funded_ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"))
        funded_ledger.transfer("wallet_b", "wallet_a", Decimal("25.00"))
        
        proof = funded_ledger.get_balance_proof("wallet_a", "USDC")
        
        assert proof.wallet_id == "wallet_a"
        # Balance is tracked in the ledger
        assert proof.balance == funded_ledger.get_balance("wallet_a", "USDC")
        assert len(proof.contributing_entries) > 0
    
    # ==================== Multi-Currency Tests ====================
    
    def test_multi_currency(self, ledger):
        """Test handling multiple currencies."""
        ledger.set_balance("wallet_a", "USDC", Decimal("1000.00"))
        ledger.set_balance("wallet_a", "USDT", Decimal("500.00"))
        ledger.set_balance("wallet_b", "USDC", Decimal("0.00"))
        ledger.set_balance("wallet_b", "USDT", Decimal("0.00"))
        
        ledger.transfer("wallet_a", "wallet_b", Decimal("100.00"), currency="USDC")
        ledger.transfer("wallet_a", "wallet_b", Decimal("50.00"), currency="USDT")
        
        assert ledger.get_balance("wallet_a", "USDC") == Decimal("900.00")
        assert ledger.get_balance("wallet_a", "USDT") == Decimal("450.00")
        assert ledger.get_balance("wallet_b", "USDC") == Decimal("100.00")
        assert ledger.get_balance("wallet_b", "USDT") == Decimal("50.00")
    
    def test_get_all_balances(self, ledger):
        """Test getting all currency balances for a wallet."""
        ledger.set_balance("wallet_a", "USDC", Decimal("1000.00"))
        ledger.set_balance("wallet_a", "USDT", Decimal("500.00"))
        ledger.set_balance("wallet_a", "EURC", Decimal("250.00"))
        
        balances = ledger.get_all_balances("wallet_a")
        
        assert len(balances) == 3
        assert balances["USDC"] == Decimal("1000.00")
        assert balances["USDT"] == Decimal("500.00")
        assert balances["EURC"] == Decimal("250.00")


class TestLedgerConcurrency:
    """Test thread safety of ledger operations."""
    
    def test_concurrent_transfers(self):
        """Test concurrent transfers maintain consistency."""
        import threading
        
        ledger = LedgerService()
        ledger.set_balance("wallet_a", "USDC", Decimal("1000.00"))
        ledger.set_balance("wallet_b", "USDC", Decimal("1000.00"))
        
        errors = []
        
        def transfer_a_to_b():
            for _ in range(10):
                result = ledger.transfer("wallet_a", "wallet_b", Decimal("1.00"))
                if not result.success:
                    errors.append(result.error)
        
        def transfer_b_to_a():
            for _ in range(10):
                result = ledger.transfer("wallet_b", "wallet_a", Decimal("1.00"))
                if not result.success:
                    errors.append(result.error)
        
        threads = [
            threading.Thread(target=transfer_a_to_b),
            threading.Thread(target=transfer_b_to_a),
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Both wallets should still have 1000 total (net transfers = 0)
        total = ledger.get_balance("wallet_a", "USDC") + ledger.get_balance("wallet_b", "USDC")
        assert total == Decimal("2000.00")
        
        # Verify integrity
        is_valid, error = ledger.verify_integrity()
        assert is_valid is True


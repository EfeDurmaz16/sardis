"""Tests for the in-memory ledger."""

import pytest
from decimal import Decimal

from sardis_core.ledger import InMemoryLedger
from sardis_core.models import Wallet, TransactionStatus
from sardis_core.config import settings


@pytest.fixture
def ledger():
    """Create a fresh ledger for each test."""
    return InMemoryLedger()


@pytest.fixture
def test_wallet(ledger):
    """Create a test wallet with funds."""
    wallet = Wallet(
        wallet_id="test_wallet_001",
        agent_id="test_agent",
        balance=Decimal("0.00"),
        currency="USDC",
        limit_per_tx=Decimal("50.00"),
        limit_total=Decimal("100.00")
    )
    ledger.create_wallet(wallet)
    # Fund the wallet
    ledger.fund_wallet("test_wallet_001", Decimal("100.00"))
    return ledger.get_wallet("test_wallet_001")


@pytest.fixture
def merchant_wallet(ledger):
    """Create a merchant wallet."""
    wallet = Wallet(
        wallet_id="merchant_wallet_001",
        agent_id="merchant",
        balance=Decimal("0.00"),
        currency="USDC",
        limit_per_tx=Decimal("999999.00"),
        limit_total=Decimal("999999.00")
    )
    ledger.create_wallet(wallet)
    return wallet


class TestLedgerWallet:
    """Tests for wallet operations on the ledger."""
    
    def test_create_wallet(self, ledger):
        """Test wallet creation."""
        wallet = Wallet(
            wallet_id="new_wallet",
            agent_id="agent_1",
            balance=Decimal("0.00"),
            currency="USDC"
        )
        
        result = ledger.create_wallet(wallet)
        
        assert result.wallet_id == "new_wallet"
        assert ledger.get_wallet("new_wallet") is not None
    
    def test_create_duplicate_wallet_fails(self, ledger):
        """Test that creating a duplicate wallet fails."""
        wallet = Wallet(
            wallet_id="dup_wallet",
            agent_id="agent_1",
            balance=Decimal("0.00"),
            currency="USDC"
        )
        
        ledger.create_wallet(wallet)
        
        with pytest.raises(ValueError, match="already exists"):
            ledger.create_wallet(wallet)
    
    def test_get_nonexistent_wallet(self, ledger):
        """Test getting a wallet that doesn't exist."""
        result = ledger.get_wallet("nonexistent")
        assert result is None
    
    def test_fund_wallet(self, ledger, test_wallet):
        """Test funding a wallet."""
        initial_balance = test_wallet.balance
        
        ledger.fund_wallet("test_wallet_001", Decimal("50.00"))
        
        updated_wallet = ledger.get_wallet("test_wallet_001")
        assert updated_wallet.balance == initial_balance + Decimal("50.00")
    
    def test_get_balance(self, ledger, test_wallet):
        """Test getting wallet balance."""
        balance = ledger.get_balance("test_wallet_001")
        assert balance == Decimal("100.00")
    
    def test_get_balance_nonexistent_wallet(self, ledger):
        """Test getting balance of nonexistent wallet fails."""
        with pytest.raises(ValueError, match="not found"):
            ledger.get_balance("nonexistent")


class TestLedgerTransfer:
    """Tests for transfer operations on the ledger."""
    
    def test_successful_transfer(self, ledger, test_wallet, merchant_wallet):
        """Test a successful transfer."""
        tx = ledger.transfer(
            from_wallet_id="test_wallet_001",
            to_wallet_id="merchant_wallet_001",
            amount=Decimal("10.00"),
            fee=Decimal("0.10"),
            currency="USDC",
            purpose="Test purchase"
        )
        
        assert tx.status == TransactionStatus.COMPLETED
        assert tx.amount == Decimal("10.00")
        assert tx.fee == Decimal("0.10")
        
        # Check balances
        from_wallet = ledger.get_wallet("test_wallet_001")
        to_wallet = ledger.get_wallet("merchant_wallet_001")
        
        assert from_wallet.balance == Decimal("100.00") - Decimal("10.10")  # amount + fee
        assert to_wallet.balance == Decimal("10.00")
    
    def test_transfer_insufficient_balance(self, ledger, test_wallet, merchant_wallet):
        """Test transfer with insufficient balance fails."""
        with pytest.raises(ValueError, match="Insufficient balance"):
            ledger.transfer(
                from_wallet_id="test_wallet_001",
                to_wallet_id="merchant_wallet_001",
                amount=Decimal("150.00"),
                fee=Decimal("0.10"),
                currency="USDC"
            )
    
    def test_transfer_updates_spent_total(self, ledger, test_wallet, merchant_wallet):
        """Test that transfer updates spent_total."""
        initial_spent = test_wallet.spent_total
        
        ledger.transfer(
            from_wallet_id="test_wallet_001",
            to_wallet_id="merchant_wallet_001",
            amount=Decimal("10.00"),
            fee=Decimal("0.10"),
            currency="USDC"
        )
        
        updated_wallet = ledger.get_wallet("test_wallet_001")
        assert updated_wallet.spent_total == initial_spent + Decimal("10.00")
    
    def test_transfer_fee_goes_to_fee_pool(self, ledger, test_wallet, merchant_wallet):
        """Test that fees are collected in the fee pool."""
        fee_pool_initial = ledger.get_balance(settings.fee_pool_wallet_id)
        
        ledger.transfer(
            from_wallet_id="test_wallet_001",
            to_wallet_id="merchant_wallet_001",
            amount=Decimal("10.00"),
            fee=Decimal("0.10"),
            currency="USDC"
        )
        
        fee_pool_after = ledger.get_balance(settings.fee_pool_wallet_id)
        assert fee_pool_after == fee_pool_initial + Decimal("0.10")
    
    def test_transfer_from_nonexistent_wallet(self, ledger, merchant_wallet):
        """Test transfer from nonexistent wallet fails."""
        with pytest.raises(ValueError, match="Source wallet.*not found"):
            ledger.transfer(
                from_wallet_id="nonexistent",
                to_wallet_id="merchant_wallet_001",
                amount=Decimal("10.00"),
                fee=Decimal("0.10"),
                currency="USDC"
            )
    
    def test_transfer_to_nonexistent_wallet(self, ledger, test_wallet):
        """Test transfer to nonexistent wallet fails."""
        with pytest.raises(ValueError, match="Destination wallet.*not found"):
            ledger.transfer(
                from_wallet_id="test_wallet_001",
                to_wallet_id="nonexistent",
                amount=Decimal("10.00"),
                fee=Decimal("0.10"),
                currency="USDC"
            )


class TestLedgerTransactions:
    """Tests for transaction listing."""
    
    def test_get_transaction(self, ledger, test_wallet, merchant_wallet):
        """Test retrieving a transaction by ID."""
        tx = ledger.transfer(
            from_wallet_id="test_wallet_001",
            to_wallet_id="merchant_wallet_001",
            amount=Decimal("10.00"),
            fee=Decimal("0.10"),
            currency="USDC"
        )
        
        retrieved = ledger.get_transaction(tx.tx_id)
        
        assert retrieved is not None
        assert retrieved.tx_id == tx.tx_id
        assert retrieved.amount == tx.amount
    
    def test_list_transactions(self, ledger, test_wallet, merchant_wallet):
        """Test listing transactions for a wallet."""
        # Create multiple transactions
        for i in range(3):
            ledger.transfer(
                from_wallet_id="test_wallet_001",
                to_wallet_id="merchant_wallet_001",
                amount=Decimal("5.00"),
                fee=Decimal("0.10"),
                currency="USDC"
            )
        
        transactions = ledger.list_transactions("test_wallet_001")
        
        assert len(transactions) >= 3  # May include funding transaction
    
    def test_list_transactions_pagination(self, ledger, test_wallet, merchant_wallet):
        """Test transaction listing with pagination."""
        # Create multiple transactions
        for i in range(5):
            ledger.transfer(
                from_wallet_id="test_wallet_001",
                to_wallet_id="merchant_wallet_001",
                amount=Decimal("2.00"),
                fee=Decimal("0.10"),
                currency="USDC"
            )
        
        # Get first page
        page1 = ledger.list_transactions("test_wallet_001", limit=2, offset=0)
        # Get second page
        page2 = ledger.list_transactions("test_wallet_001", limit=2, offset=2)
        
        assert len(page1) == 2
        assert len(page2) == 2
        assert page1[0].tx_id != page2[0].tx_id


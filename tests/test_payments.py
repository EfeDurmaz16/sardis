"""Tests for payment service."""

import pytest
from decimal import Decimal

from sardis_core.ledger import InMemoryLedger
from sardis_core.services import WalletService, PaymentService, FeeService
from sardis_core.models import TransactionStatus


@pytest.fixture
def ledger():
    """Create a fresh ledger."""
    return InMemoryLedger()


@pytest.fixture
def wallet_service(ledger):
    """Create wallet service."""
    return WalletService(ledger)


@pytest.fixture
def fee_service():
    """Create fee service."""
    return FeeService()


@pytest.fixture
def payment_service(ledger, wallet_service, fee_service):
    """Create payment service."""
    return PaymentService(ledger, wallet_service, fee_service)


@pytest.fixture
def registered_agent(wallet_service):
    """Create a registered agent with wallet."""
    agent, wallet = wallet_service.register_agent(
        name="Test Agent",
        owner_id="test_owner",
        initial_balance=Decimal("100.00"),
        limit_per_tx=Decimal("50.00"),
        limit_total=Decimal("200.00")
    )
    return agent, wallet


@pytest.fixture
def registered_merchant(wallet_service):
    """Create a registered merchant."""
    merchant, wallet = wallet_service.register_merchant(
        name="Test Merchant",
        description="Test merchant for testing",
        category="test"
    )
    return merchant, wallet


class TestPaymentService:
    """Tests for payment operations."""
    
    def test_successful_payment_to_merchant(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test successful payment to a merchant."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("10.00"),
            purpose="Test purchase"
        )
        
        assert result.success is True
        assert result.transaction is not None
        assert result.transaction.amount == Decimal("10.00")
        assert result.transaction.status == TransactionStatus.COMPLETED
    
    def test_payment_includes_fee(
        self,
        payment_service,
        wallet_service,
        registered_agent,
        registered_merchant
    ):
        """Test that payment includes transaction fee."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        initial_balance = wallet_service.get_agent_wallet(agent.agent_id).balance
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("10.00")
        )
        
        final_balance = wallet_service.get_agent_wallet(agent.agent_id).balance
        
        # Should have deducted 10.00 + 0.10 fee = 10.10
        assert result.transaction.fee == Decimal("0.10")
        assert final_balance == initial_balance - Decimal("10.10")
    
    def test_payment_rejected_insufficient_balance(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test payment is rejected when balance is insufficient."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("150.00")  # More than 100 balance
        )
        
        assert result.success is False
        assert "Insufficient balance" in result.error
    
    def test_payment_rejected_exceeds_per_tx_limit(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test payment is rejected when it exceeds per-tx limit."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("60.00")  # Limit is 50
        )
        
        assert result.success is False
        assert "per-transaction limit" in result.error
    
    def test_payment_rejected_negative_amount(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test payment is rejected for negative amounts."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("-10.00")
        )
        
        assert result.success is False
        assert "positive" in result.error.lower()
    
    def test_payment_rejected_zero_amount(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test payment is rejected for zero amount."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id=merchant.merchant_id,
            amount=Decimal("0.00")
        )
        
        assert result.success is False
    
    def test_payment_to_unknown_merchant_fails(
        self,
        payment_service,
        registered_agent
    ):
        """Test payment to unknown merchant fails."""
        agent, _ = registered_agent
        
        result = payment_service.pay_merchant(
            agent_id=agent.agent_id,
            merchant_id="nonexistent_merchant",
            amount=Decimal("10.00")
        )
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_payment_from_unknown_agent_fails(
        self,
        payment_service,
        registered_merchant
    ):
        """Test payment from unknown agent fails."""
        merchant, _ = registered_merchant
        
        result = payment_service.pay_merchant(
            agent_id="nonexistent_agent",
            merchant_id=merchant.merchant_id,
            amount=Decimal("10.00")
        )
        
        assert result.success is False
        assert "not found" in result.error.lower()
    
    def test_direct_wallet_payment(
        self,
        payment_service,
        wallet_service,
        registered_agent
    ):
        """Test direct payment to a wallet ID."""
        agent, _ = registered_agent
        
        # Create a recipient wallet
        recipient_agent, recipient_wallet = wallet_service.register_agent(
            name="Recipient",
            owner_id="other_owner",
            initial_balance=Decimal("0.00")
        )
        
        result = payment_service.pay(
            agent_id=agent.agent_id,
            amount=Decimal("10.00"),
            recipient_wallet_id=recipient_wallet.wallet_id,
            purpose="Direct transfer"
        )
        
        assert result.success is True
        
        # Check recipient received funds
        updated_recipient = wallet_service.get_wallet(recipient_wallet.wallet_id)
        assert updated_recipient.balance == Decimal("10.00")


class TestPaymentEstimate:
    """Tests for payment estimation."""
    
    def test_estimate_includes_fee(self, payment_service):
        """Test that estimate includes the fee."""
        estimate = payment_service.estimate_payment(Decimal("10.00"))
        
        assert estimate["amount"] == "10.00"
        assert estimate["fee"] == "0.10"
        assert estimate["total"] == "10.10"


class TestTransactionListing:
    """Tests for transaction listing."""
    
    def test_list_agent_transactions(
        self,
        payment_service,
        registered_agent,
        registered_merchant
    ):
        """Test listing transactions for an agent."""
        agent, _ = registered_agent
        merchant, _ = registered_merchant
        
        # Make some payments
        for i in range(3):
            payment_service.pay_merchant(
                agent_id=agent.agent_id,
                merchant_id=merchant.merchant_id,
                amount=Decimal("5.00"),
                purpose=f"Purchase {i+1}"
            )
        
        transactions = payment_service.list_agent_transactions(agent.agent_id)
        
        # Should have at least 3 transactions (plus initial funding)
        assert len(transactions) >= 3
    
    def test_list_transactions_unknown_agent(self, payment_service):
        """Test listing transactions for unknown agent returns empty list."""
        transactions = payment_service.list_agent_transactions("nonexistent")
        assert transactions == []


class TestFeeService:
    """Tests for fee calculation."""
    
    def test_default_fee(self, fee_service):
        """Test default fee is applied."""
        fee = fee_service.calculate_fee(Decimal("100.00"))
        assert fee == Decimal("0.10")
    
    def test_fee_independent_of_amount(self, fee_service):
        """Test fee is flat (not percentage) in MVP."""
        fee_small = fee_service.calculate_fee(Decimal("1.00"))
        fee_large = fee_service.calculate_fee(Decimal("1000.00"))
        
        assert fee_small == fee_large == Decimal("0.10")
    
    def test_calculate_total_cost(self, fee_service):
        """Test total cost calculation."""
        fee, total = fee_service.calculate_total_cost(Decimal("10.00"))
        
        assert fee == Decimal("0.10")
        assert total == Decimal("10.10")


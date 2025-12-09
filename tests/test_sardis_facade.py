"""Tests for the Sardis facade package."""
import pytest
from decimal import Decimal


class TestWallet:
    """Tests for the Wallet class."""
    
    def test_create_wallet_default(self):
        """Test creating a wallet with defaults."""
        from sardis import Wallet
        
        wallet = Wallet()
        assert wallet.balance == Decimal("0.00")
        assert wallet.currency == "USDC"
        assert wallet.is_active is True
    
    def test_create_wallet_with_balance(self):
        """Test creating a wallet with initial balance."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=100)
        assert wallet.balance == Decimal("100")
    
    def test_can_spend_sufficient_funds(self):
        """Test can_spend with sufficient funds."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=100)
        assert wallet.can_spend(50) is True
    
    def test_can_spend_insufficient_funds(self):
        """Test can_spend with insufficient funds."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=10)
        assert wallet.can_spend(50) is False
    
    def test_can_spend_exceeds_per_tx_limit(self):
        """Test can_spend exceeds per-transaction limit."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=500, limit_per_tx=100)
        assert wallet.can_spend(150) is False
    
    def test_spend_deducts_balance(self):
        """Test that spend deducts from balance."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=100)
        result = wallet.spend(25)
        
        assert result is True
        assert wallet.balance == Decimal("75")
        assert wallet.spent_total == Decimal("25")
    
    def test_spend_fails_insufficient_funds(self):
        """Test that spend fails with insufficient funds."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=10)
        result = wallet.spend(50)
        
        assert result is False
        assert wallet.balance == Decimal("10")
    
    def test_deposit_adds_balance(self):
        """Test that deposit adds to balance."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=50)
        wallet.deposit(25)
        
        assert wallet.balance == Decimal("75")
    
    def test_remaining_limit(self):
        """Test remaining_limit calculation."""
        from sardis import Wallet
        
        wallet = Wallet(initial_balance=100, limit_total=200)
        wallet.spend(50)
        
        assert wallet.remaining_limit() == Decimal("150")


class TestTransaction:
    """Tests for the Transaction class."""
    
    def test_execute_successful(self):
        """Test successful transaction execution."""
        from sardis import Wallet, Transaction
        
        wallet = Wallet(initial_balance=100)
        tx = Transaction(from_wallet=wallet, to="merchant:test", amount=25)
        
        result = tx.execute()
        
        assert result.success is True
        assert result.amount == Decimal("25")
        assert wallet.balance == Decimal("75")
    
    def test_execute_insufficient_funds(self):
        """Test transaction fails with insufficient funds."""
        from sardis import Wallet, Transaction
        
        wallet = Wallet(initial_balance=10)
        tx = Transaction(from_wallet=wallet, to="merchant:test", amount=50)
        
        result = tx.execute()
        
        assert result.success is False
        assert wallet.balance == Decimal("10")
    
    def test_execute_has_tx_hash(self):
        """Test that successful transaction has tx_hash."""
        from sardis import Wallet, Transaction
        
        wallet = Wallet(initial_balance=100)
        tx = Transaction(from_wallet=wallet, to="merchant:test", amount=10)
        
        result = tx.execute()
        
        assert result.tx_hash is not None
        assert result.tx_hash.startswith("0x")


class TestPolicy:
    """Tests for the Policy class."""
    
    def test_check_within_limits(self):
        """Test policy check within limits."""
        from sardis import Policy
        
        policy = Policy(max_per_tx=100)
        result = policy.check(amount=50)
        
        assert result.approved is True
    
    def test_check_exceeds_limit(self):
        """Test policy check exceeds limit."""
        from sardis import Policy
        
        policy = Policy(max_per_tx=50)
        result = policy.check(amount=100)
        
        assert result.approved is False
    
    def test_check_blocked_destination(self):
        """Test policy check with blocked destination."""
        from sardis import Policy
        
        policy = Policy(blocked_destinations={"blocked:merchant"})
        result = policy.check(amount=10, destination="blocked:merchant")
        
        assert result.approved is False
    
    def test_check_allowed_destination_pattern(self):
        """Test policy check with destination pattern."""
        from sardis import Policy
        
        policy = Policy(allowed_destinations={"openai:*"})
        result = policy.check(amount=10, destination="openai:gpt4")
        
        assert result.approved is True
    
    def test_check_token_not_allowed(self):
        """Test policy check with disallowed token."""
        from sardis import Policy
        
        policy = Policy(allowed_tokens={"USDC"})
        result = policy.check(amount=10, token="BTC")
        
        assert result.approved is False


class TestAgent:
    """Tests for the Agent class."""
    
    def test_create_agent(self):
        """Test creating an agent."""
        from sardis import Agent
        
        agent = Agent(name="Test Agent")
        
        assert agent.name == "Test Agent"
        assert agent.is_active is True
        assert len(agent.wallets) == 0
    
    def test_create_wallet(self):
        """Test creating a wallet for an agent."""
        from sardis import Agent
        
        agent = Agent(name="Test Agent")
        wallet = agent.create_wallet(initial_balance=100)
        
        assert len(agent.wallets) == 1
        assert agent.primary_wallet == wallet
        assert agent.total_balance == 100
    
    def test_pay_successful(self):
        """Test successful payment from agent."""
        from sardis import Agent
        
        agent = Agent(name="Test Agent")
        agent.create_wallet(initial_balance=100)
        
        result = agent.pay(to="merchant:test", amount=25)
        
        assert result.success is True
        assert agent.total_balance == 75
    
    def test_pay_no_wallet(self):
        """Test payment fails without wallet."""
        from sardis import Agent
        
        agent = Agent(name="Test Agent")
        
        result = agent.pay(to="merchant:test", amount=25)
        
        assert result.success is False
    
    def test_pay_with_policy(self):
        """Test payment with policy enforcement."""
        from sardis import Agent, Policy
        
        policy = Policy(max_per_tx=50)
        agent = Agent(name="Test Agent", policy=policy)
        agent.create_wallet(initial_balance=100)
        
        # Within limit
        result1 = agent.pay(to="merchant:test", amount=30)
        assert result1.success is True
        
        # Exceeds limit
        result2 = agent.pay(to="merchant:test", amount=60)
        assert result2.success is False

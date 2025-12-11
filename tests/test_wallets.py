"""Unit tests for wallet models and operations."""
from __future__ import annotations

from decimal import Decimal
import pytest

from sardis_v2_core.wallets import Wallet, TokenBalance, WalletSnapshot
from sardis_v2_core.tokens import TokenType


class TestTokenBalance:
    """Tests for TokenBalance model."""

    def test_token_balance_creation(self):
        """Test creating a TokenBalance."""
        balance = TokenBalance(
            token=TokenType.USDC,
            balance=Decimal("100.00"),
        )
        
        assert balance.token == TokenType.USDC
        assert balance.balance == Decimal("100.00")
        assert balance.spent_total == Decimal("0.00")

    def test_token_balance_remaining_limit(self):
        """Test remaining limit calculation."""
        balance = TokenBalance(
            token=TokenType.USDC,
            balance=Decimal("500.00"),
            limit_total=Decimal("1000.00"),
            spent_total=Decimal("300.00"),
        )
        
        # Uses own limit
        remaining = balance.remaining_limit(Decimal("2000.00"))
        assert remaining == Decimal("700.00")  # 1000 - 300

    def test_token_balance_uses_wallet_limit_when_none(self):
        """Test remaining limit falls back to wallet limit when token limit is None."""
        balance = TokenBalance(
            token=TokenType.USDT,
            balance=Decimal("500.00"),
            limit_total=None,
            spent_total=Decimal("200.00"),
        )
        
        # Falls back to wallet limit
        remaining = balance.remaining_limit(Decimal("1000.00"))
        assert remaining == Decimal("800.00")  # 1000 - 200


class TestWallet:
    """Tests for Wallet model."""

    def test_wallet_creation(self):
        """Test creating a Wallet."""
        wallet = Wallet(
            wallet_id="wallet_test001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
        )
        
        assert wallet.wallet_id == "wallet_test001"
        assert wallet.agent_id == "agent_001"
        assert wallet.balance == Decimal("1000.00")
        assert wallet.is_active is True

    def test_wallet_new_factory(self):
        """Test Wallet.new() factory method."""
        wallet = Wallet.new("agent_123", currency="USDT")
        
        assert wallet.agent_id == "agent_123"
        assert wallet.wallet_id.startswith("wallet_")
        assert wallet.currency == "USDT"
        assert wallet.balance == Decimal("0.00")

    def test_get_token_balance_default_currency(self):
        """Test getting balance for default currency."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
        )
        
        balance = wallet.get_token_balance(TokenType.USDC)
        assert balance == Decimal("500.00")

    def test_get_token_balance_other_token(self):
        """Test getting balance for non-default token."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
            token_balances={
                "USDT": TokenBalance(token=TokenType.USDT, balance=Decimal("250.00")),
            },
        )
        
        usdt_balance = wallet.get_token_balance(TokenType.USDT)
        assert usdt_balance == Decimal("250.00")

    def test_get_token_balance_missing_token(self):
        """Test getting balance for token not in wallet."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
        )
        
        pyusd_balance = wallet.get_token_balance(TokenType.PYUSD)
        assert pyusd_balance == Decimal("0.00")

    def test_set_token_balance_default_currency(self):
        """Test setting balance for default currency."""
        wallet = Wallet.new("agent_001")
        wallet.set_token_balance(TokenType.USDC, Decimal("1000.00"))
        
        assert wallet.balance == Decimal("1000.00")

    def test_set_token_balance_other_token(self):
        """Test setting balance for non-default token."""
        wallet = Wallet.new("agent_001")
        wallet.set_token_balance(TokenType.USDT, Decimal("750.00"))
        
        assert "USDT" in wallet.token_balances
        assert wallet.token_balances["USDT"].balance == Decimal("750.00")

    def test_add_token_balance(self):
        """Test adding to token balance."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
        )
        
        wallet.add_token_balance(TokenType.USDC, Decimal("250.00"))
        assert wallet.balance == Decimal("750.00")

    def test_subtract_token_balance_success(self):
        """Test subtracting from token balance (sufficient funds)."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
        )
        
        result = wallet.subtract_token_balance(TokenType.USDC, Decimal("200.00"))
        
        assert result is True
        assert wallet.balance == Decimal("300.00")

    def test_subtract_token_balance_insufficient(self):
        """Test subtracting from token balance (insufficient funds)."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("100.00"),
            currency="USDC",
        )
        
        result = wallet.subtract_token_balance(TokenType.USDC, Decimal("200.00"))
        
        assert result is False
        assert wallet.balance == Decimal("100.00")


class TestWalletCanSpend:
    """Tests for wallet spending validation."""

    def test_can_spend_success(self):
        """Test can_spend returns True for valid transaction."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("5000.00"),
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is True
        assert reason == "OK"

    def test_can_spend_with_fee(self):
        """Test can_spend accounts for fees."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("100.00"),
            currency="USDC",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("5000.00"),
        )
        
        # 90 + 15 = 105 > 100 balance
        can_spend, reason = wallet.can_spend(
            Decimal("90.00"),
            fee=Decimal("15.00"),
        )
        
        assert can_spend is False
        assert reason == "insufficient_balance"

    def test_can_spend_inactive_wallet(self):
        """Test can_spend fails for inactive wallet."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
            is_active=False,
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is False
        assert reason == "wallet_inactive"

    def test_can_spend_insufficient_balance(self):
        """Test can_spend fails for insufficient balance."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("50.00"),
            currency="USDC",
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is False
        assert reason == "insufficient_balance"

    def test_can_spend_per_transaction_limit(self):
        """Test can_spend fails when exceeding per-transaction limit."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
            limit_per_tx=Decimal("50.00"),
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is False
        assert reason == "per_transaction_limit"

    def test_can_spend_total_limit_exceeded(self):
        """Test can_spend fails when exceeding total limit."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
            limit_per_tx=Decimal("500.00"),
            limit_total=Decimal("200.00"),
            spent_total=Decimal("150.00"),
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is False
        assert reason == "total_limit_exceeded"

    def test_can_spend_exact_limit(self):
        """Test can_spend succeeds at exact per-tx limit."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
            limit_per_tx=Decimal("100.00"),
            limit_total=Decimal("1000.00"),
        )
        
        can_spend, reason = wallet.can_spend(Decimal("100.00"))
        
        assert can_spend is True
        assert reason == "OK"


class TestWalletRecordSpend:
    """Tests for recording wallet spending."""

    def test_record_spend_default_currency(self):
        """Test recording spend for default currency."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
        )
        
        wallet.record_spend(Decimal("100.00"))
        
        assert wallet.spent_total == Decimal("100.00")

    def test_record_spend_multiple(self):
        """Test recording multiple spends."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
        )
        
        wallet.record_spend(Decimal("50.00"))
        wallet.record_spend(Decimal("75.00"))
        wallet.record_spend(Decimal("25.00"))
        
        assert wallet.spent_total == Decimal("150.00")

    def test_record_spend_other_token(self):
        """Test recording spend for non-default token."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            currency="USDC",
            token_balances={
                "USDT": TokenBalance(token=TokenType.USDT, balance=Decimal("500.00")),
            },
        )
        
        wallet.record_spend(Decimal("100.00"), TokenType.USDT)
        
        assert wallet.spent_total == Decimal("0.00")  # USDC unchanged
        assert wallet.token_balances["USDT"].spent_total == Decimal("100.00")


class TestWalletHelpers:
    """Tests for wallet helper methods."""

    def test_remaining_limit(self):
        """Test remaining_limit calculation."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            limit_total=Decimal("500.00"),
            spent_total=Decimal("200.00"),
        )
        
        remaining = wallet.remaining_limit()
        assert remaining == Decimal("300.00")

    def test_get_limit_per_tx_default(self):
        """Test get_limit_per_tx returns wallet default."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            limit_per_tx=Decimal("100.00"),
        )
        
        limit = wallet.get_limit_per_tx()
        assert limit == Decimal("100.00")

    def test_get_limit_per_tx_token_override(self):
        """Test get_limit_per_tx uses token-specific limit when set."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("1000.00"),
            limit_per_tx=Decimal("100.00"),
            token_balances={
                "USDT": TokenBalance(
                    token=TokenType.USDT,
                    balance=Decimal("500.00"),
                    limit_per_tx=Decimal("50.00"),
                ),
            },
        )
        
        limit = wallet.get_limit_per_tx(TokenType.USDT)
        assert limit == Decimal("50.00")

    def test_total_balance_usd(self):
        """Test total_balance_usd sums all balances."""
        wallet = Wallet(
            wallet_id="wallet_001",
            agent_id="agent_001",
            balance=Decimal("500.00"),
            currency="USDC",
            token_balances={
                "USDT": TokenBalance(token=TokenType.USDT, balance=Decimal("300.00")),
                "PYUSD": TokenBalance(token=TokenType.PYUSD, balance=Decimal("200.00")),
            },
        )
        
        total = wallet.total_balance_usd()
        assert total == Decimal("1000.00")


class TestWalletSnapshot:
    """Tests for WalletSnapshot model."""

    def test_wallet_snapshot_creation(self):
        """Test creating a WalletSnapshot."""
        snapshot = WalletSnapshot(
            wallet_id="wallet_001",
            balances={"USDC": Decimal("100.00"), "USDT": Decimal("50.00")},
        )
        
        assert snapshot.wallet_id == "wallet_001"
        assert snapshot.balances["USDC"] == Decimal("100.00")
        assert snapshot.balances["USDT"] == Decimal("50.00")
        assert snapshot.captured_at is not None





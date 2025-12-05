"""Tests for spending limit enforcement."""

import pytest
from decimal import Decimal

from sardis_core.models import Wallet


class TestWalletLimits:
    """Tests for wallet limit checking."""
    
    @pytest.fixture
    def wallet(self):
        """Create a test wallet."""
        return Wallet(
            wallet_id="test_wallet",
            agent_id="test_agent",
            balance=Decimal("100.00"),
            currency="USDC",
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("200.00"),
            spent_total=Decimal("0.00")
        )
    
    def test_can_spend_within_limits(self, wallet):
        """Test spending within all limits is allowed."""
        can_spend, reason = wallet.can_spend(Decimal("30.00"), Decimal("0.10"))
        
        assert can_spend is True
        assert reason == "OK"
    
    def test_cannot_spend_exceeds_balance(self, wallet):
        """Test spending more than balance is rejected."""
        can_spend, reason = wallet.can_spend(Decimal("150.00"), Decimal("0.10"))
        
        assert can_spend is False
        assert "Insufficient balance" in reason
    
    def test_cannot_spend_exceeds_per_tx_limit(self, wallet):
        """Test spending above per-transaction limit is rejected."""
        can_spend, reason = wallet.can_spend(Decimal("60.00"))  # Limit is 50
        
        assert can_spend is False
        assert "per-transaction limit" in reason
    
    def test_cannot_spend_exceeds_total_limit(self, wallet):
        """Test spending above total limit is rejected."""
        # Set spent_total close to limit
        wallet.spent_total = Decimal("180.00")
        
        can_spend, reason = wallet.can_spend(Decimal("30.00"))  # Would push over 200
        
        assert can_spend is False
        assert "remaining spending limit" in reason
    
    def test_cannot_spend_when_inactive(self, wallet):
        """Test spending from inactive wallet is rejected."""
        wallet.is_active = False
        
        can_spend, reason = wallet.can_spend(Decimal("10.00"))
        
        assert can_spend is False
        assert "inactive" in reason.lower()
    
    def test_fee_included_in_balance_check(self, wallet):
        """Test that fee is included in balance check."""
        # Balance is 100, try to spend 99.95 + 0.10 fee = 100.05
        wallet.balance = Decimal("100.00")
        
        can_spend, reason = wallet.can_spend(Decimal("99.95"), Decimal("0.10"))
        
        assert can_spend is False
        assert "Insufficient balance" in reason
    
    def test_remaining_limit_calculation(self, wallet):
        """Test remaining limit is calculated correctly."""
        wallet.limit_total = Decimal("100.00")
        wallet.spent_total = Decimal("30.00")
        
        assert wallet.remaining_limit() == Decimal("70.00")
    
    def test_remaining_limit_never_negative(self, wallet):
        """Test remaining limit never goes below zero."""
        wallet.limit_total = Decimal("100.00")
        wallet.spent_total = Decimal("150.00")  # Over limit
        
        assert wallet.remaining_limit() == Decimal("0.00")
    
    def test_exact_balance_spend_with_fee(self, wallet):
        """Test spending exactly the balance including fee works."""
        wallet.balance = Decimal("100.00")
        wallet.limit_per_tx = Decimal("100.00")
        wallet.limit_total = Decimal("100.00")
        
        # Should be able to spend 99.90 + 0.10 fee = 100.00 exactly
        can_spend, reason = wallet.can_spend(Decimal("99.90"), Decimal("0.10"))
        
        assert can_spend is True
    
    def test_exact_limit_spend(self, wallet):
        """Test spending exactly the per-tx limit works."""
        wallet.limit_per_tx = Decimal("50.00")
        
        can_spend, reason = wallet.can_spend(Decimal("50.00"))
        
        assert can_spend is True


class TestWalletLimitEdgeCases:
    """Edge case tests for wallet limits."""
    
    def test_zero_amount_spend(self):
        """Test zero amount spend is technically allowed by limits."""
        wallet = Wallet(
            wallet_id="test",
            agent_id="agent",
            balance=Decimal("100.00"),
            currency="USDC",
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("100.00")
        )
        
        can_spend, reason = wallet.can_spend(Decimal("0.00"))
        assert can_spend is True
    
    def test_zero_balance_cannot_spend(self):
        """Test cannot spend with zero balance."""
        wallet = Wallet(
            wallet_id="test",
            agent_id="agent",
            balance=Decimal("0.00"),
            currency="USDC",
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("100.00")
        )
        
        can_spend, reason = wallet.can_spend(Decimal("10.00"))
        assert can_spend is False
    
    def test_very_small_amount(self):
        """Test very small amounts work correctly."""
        wallet = Wallet(
            wallet_id="test",
            agent_id="agent",
            balance=Decimal("0.01"),
            currency="USDC",
            limit_per_tx=Decimal("50.00"),
            limit_total=Decimal("100.00")
        )
        
        can_spend, reason = wallet.can_spend(Decimal("0.01"))
        assert can_spend is True


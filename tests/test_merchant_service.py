"""Tests for the MerchantService with invoices and payouts."""

import pytest
from decimal import Decimal
from datetime import datetime, timezone, timedelta

from sardis_core.services.merchant_service import (
    MerchantService,
    Invoice,
    InvoiceStatus,
    Payout,
    PayoutStatus,
    get_merchant_service,
)


class TestInvoice:
    """Test suite for Invoice model."""
    
    def test_create_invoice(self):
        """Test creating an invoice."""
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            currency="USDC",
            description="Test invoice"
        )
        
        assert invoice.invoice_id.startswith("inv_")
        assert invoice.merchant_id == "merchant_1"
        assert invoice.amount == Decimal("100.00")
        assert invoice.status == InvoiceStatus.PENDING
    
    def test_invoice_amount_remaining(self):
        """Test calculating remaining amount."""
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            amount_paid=Decimal("30.00")
        )
        
        assert invoice.amount_remaining() == Decimal("70.00")
    
    def test_invoice_is_expired(self):
        """Test checking if invoice is expired."""
        # Not expired
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24)
        )
        assert invoice.is_expired() is False
        
        # Expired
        invoice_expired = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert invoice_expired.is_expired() is True
    
    def test_invoice_record_payment(self):
        """Test recording a payment on invoice."""
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00")
        )
        
        invoice.record_payment(Decimal("100.00"), "tx_123")
        
        assert invoice.amount_paid == Decimal("100.00")
        assert invoice.status == InvoiceStatus.PAID
        assert "tx_123" in invoice.payment_tx_ids
        assert invoice.paid_at is not None
    
    def test_invoice_record_partial_payment(self):
        """Test recording a partial payment."""
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            allow_partial=True
        )
        
        invoice.record_payment(Decimal("50.00"), "tx_123")
        
        assert invoice.amount_paid == Decimal("50.00")
        assert invoice.status == InvoiceStatus.PARTIALLY_PAID
    
    def test_invoice_to_dict(self):
        """Test converting invoice to dictionary."""
        invoice = Invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            description="Test invoice"
        )
        
        data = invoice.to_dict()
        
        assert data["invoice_id"] == invoice.invoice_id
        assert data["amount"] == "100.00"
        assert data["status"] == "pending"


class TestMerchantService:
    """Test suite for MerchantService."""
    
    @pytest.fixture
    def merchant_service(self):
        """Create a fresh merchant service."""
        return MerchantService()
    
    # ==================== Invoice Tests ====================
    
    def test_create_invoice(self, merchant_service):
        """Test creating an invoice."""
        invoice = merchant_service.create_invoice(
            merchant_id="merchant_1",
            amount=Decimal("50.00"),
            description="Test service"
        )
        
        assert invoice is not None
        assert invoice.merchant_id == "merchant_1"
        assert invoice.amount == Decimal("50.00")
        assert invoice.expires_at is not None
    
    def test_create_invoice_with_expiry(self, merchant_service):
        """Test creating invoice with custom expiry."""
        invoice = merchant_service.create_invoice(
            merchant_id="merchant_1",
            amount=Decimal("50.00"),
            expires_in_hours=1
        )
        
        # Should expire in about 1 hour
        time_until_expiry = invoice.expires_at - datetime.now(timezone.utc)
        assert time_until_expiry < timedelta(hours=2)
        assert time_until_expiry > timedelta(minutes=30)
    
    def test_create_invoice_for_specific_agent(self, merchant_service):
        """Test creating invoice for a specific agent."""
        invoice = merchant_service.create_invoice(
            merchant_id="merchant_1",
            amount=Decimal("50.00"),
            requested_from_agent_id="agent_123"
        )
        
        assert invoice.requested_from_agent_id == "agent_123"
    
    def test_get_invoice(self, merchant_service):
        """Test retrieving an invoice."""
        created = merchant_service.create_invoice(
            merchant_id="merchant_1",
            amount=Decimal("50.00")
        )
        
        retrieved = merchant_service.get_invoice(created.invoice_id)
        
        assert retrieved is not None
        assert retrieved.invoice_id == created.invoice_id
    
    def test_get_nonexistent_invoice(self, merchant_service):
        """Test retrieving non-existent invoice returns None."""
        result = merchant_service.get_invoice("nonexistent_123")
        assert result is None
    
    def test_list_merchant_invoices(self, merchant_service):
        """Test listing invoices for a merchant."""
        merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        merchant_service.create_invoice("merchant_1", Decimal("75.00"))
        merchant_service.create_invoice("merchant_2", Decimal("100.00"))
        
        invoices = merchant_service.list_merchant_invoices("merchant_1")
        
        assert len(invoices) == 2
        assert all(inv.merchant_id == "merchant_1" for inv in invoices)
    
    def test_list_invoices_by_status(self, merchant_service):
        """Test filtering invoices by status."""
        inv1 = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        inv2 = merchant_service.create_invoice("merchant_1", Decimal("75.00"))
        
        # Mark one as paid
        inv1.status = InvoiceStatus.PAID
        
        pending = merchant_service.list_merchant_invoices(
            "merchant_1", 
            status=InvoiceStatus.PENDING
        )
        
        assert len(pending) == 1
        assert pending[0].invoice_id == inv2.invoice_id
    
    def test_pay_invoice_success(self, merchant_service):
        """Test paying an invoice."""
        invoice = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        
        success, message = merchant_service.pay_invoice(
            invoice_id=invoice.invoice_id,
            amount=Decimal("50.00"),
            payer_wallet_id="wallet_123",
            tx_id="tx_abc"
        )
        
        assert success is True
        
        updated = merchant_service.get_invoice(invoice.invoice_id)
        assert updated.status == InvoiceStatus.PAID
    
    def test_pay_invoice_already_paid(self, merchant_service):
        """Test paying an already paid invoice fails."""
        invoice = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        invoice.status = InvoiceStatus.PAID
        
        success, message = merchant_service.pay_invoice(
            invoice.invoice_id,
            Decimal("50.00"),
            "wallet_123",
            "tx_abc"
        )
        
        assert success is False
        assert "already paid" in message.lower()
    
    def test_pay_invoice_partial_not_allowed(self, merchant_service):
        """Test partial payment fails when not allowed."""
        invoice = merchant_service.create_invoice(
            "merchant_1", 
            Decimal("100.00"),
        )
        # allow_partial defaults to False
        
        success, message = merchant_service.pay_invoice(
            invoice.invoice_id,
            Decimal("50.00"),
            "wallet_123",
            "tx_abc"
        )
        
        assert success is False
        assert "partial" in message.lower()
    
    def test_pay_invoice_partial_allowed(self, merchant_service):
        """Test partial payment succeeds when allowed."""
        invoice = merchant_service.create_invoice(
            "merchant_1",
            Decimal("100.00"),
            allow_partial=True
        )
        
        success, _ = merchant_service.pay_invoice(
            invoice.invoice_id,
            Decimal("50.00"),
            "wallet_123",
            "tx_abc"
        )
        
        assert success is True
        
        updated = merchant_service.get_invoice(invoice.invoice_id)
        assert updated.status == InvoiceStatus.PARTIALLY_PAID
        assert updated.amount_paid == Decimal("50.00")
    
    def test_pay_invoice_exceeds_amount(self, merchant_service):
        """Test payment exceeding invoice amount fails."""
        invoice = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        
        success, message = merchant_service.pay_invoice(
            invoice.invoice_id,
            Decimal("100.00"),
            "wallet_123",
            "tx_abc"
        )
        
        assert success is False
        assert "exceeds" in message.lower()
    
    def test_pay_expired_invoice(self, merchant_service):
        """Test paying an expired invoice fails."""
        invoice = merchant_service.create_invoice(
            "merchant_1",
            Decimal("50.00"),
            expires_in_hours=0  # Immediately expire (practically)
        )
        # Force expiry
        invoice.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        success, message = merchant_service.pay_invoice(
            invoice.invoice_id,
            Decimal("50.00"),
            "wallet_123",
            "tx_abc"
        )
        
        assert success is False
        assert "expired" in message.lower()
    
    def test_cancel_invoice(self, merchant_service):
        """Test cancelling an invoice."""
        invoice = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        
        result = merchant_service.cancel_invoice(invoice.invoice_id, reason="Changed mind")
        
        assert result is True
        
        updated = merchant_service.get_invoice(invoice.invoice_id)
        assert updated.status == InvoiceStatus.CANCELLED
    
    def test_cancel_paid_invoice_fails(self, merchant_service):
        """Test cancelling a paid invoice fails."""
        invoice = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        invoice.status = InvoiceStatus.PAID
        
        result = merchant_service.cancel_invoice(invoice.invoice_id)
        
        assert result is False
    
    # ==================== Payout Tests ====================
    
    def test_request_payout(self, merchant_service):
        """Test requesting a payout."""
        payout, error = merchant_service.request_payout(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            destination_address="0x1234567890abcdef",
            destination_chain="base"
        )
        
        assert error is None
        assert payout is not None
        assert payout.merchant_id == "merchant_1"
        assert payout.amount == Decimal("100.00")
        assert payout.net_amount == Decimal("99.00")  # Minus 1.00 fee
    
    def test_request_payout_amount_below_fee(self, merchant_service):
        """Test payout fails if amount doesn't cover fee."""
        payout, error = merchant_service.request_payout(
            merchant_id="merchant_1",
            amount=Decimal("0.50"),  # Less than 1.00 fee
            destination_address="0x1234",
            destination_chain="base"
        )
        
        assert payout is None
        assert error is not None
        assert "fee" in error.lower()
    
    def test_get_payout(self, merchant_service):
        """Test retrieving a payout."""
        created, _ = merchant_service.request_payout(
            "merchant_1",
            Decimal("100.00"),
            "0x1234",
            "base"
        )
        
        retrieved = merchant_service.get_payout(created.payout_id)
        
        assert retrieved is not None
        assert retrieved.payout_id == created.payout_id
    
    def test_list_merchant_payouts(self, merchant_service):
        """Test listing payouts for a merchant."""
        merchant_service.request_payout("merchant_1", Decimal("100.00"), "0x1", "base")
        merchant_service.request_payout("merchant_1", Decimal("200.00"), "0x2", "base")
        merchant_service.request_payout("merchant_2", Decimal("150.00"), "0x3", "base")
        
        payouts = merchant_service.list_merchant_payouts("merchant_1")
        
        assert len(payouts) == 2
        assert all(p.merchant_id == "merchant_1" for p in payouts)
    
    # ==================== Settlement Report Tests ====================
    
    def test_generate_settlement_report(self, merchant_service):
        """Test generating a settlement report."""
        # Create and pay some invoices
        inv1 = merchant_service.create_invoice("merchant_1", Decimal("100.00"))
        merchant_service.pay_invoice(inv1.invoice_id, Decimal("100.00"), "w1", "tx1")
        
        inv2 = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        merchant_service.pay_invoice(inv2.invoice_id, Decimal("50.00"), "w2", "tx2")
        
        report = merchant_service.generate_settlement_report(
            merchant_id="merchant_1",
            period_start=datetime.now(timezone.utc) - timedelta(days=1),
            period_end=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        
        assert report is not None
        assert report.merchant_id == "merchant_1"
        assert report.total_transactions == 2
        assert report.total_volume == Decimal("150.00")
    
    # ==================== Balance & Stats Tests ====================
    
    def test_get_merchant_balance(self, merchant_service):
        """Test getting merchant balance."""
        balance = merchant_service.get_merchant_balance("merchant_1")
        
        assert balance is not None
        assert "available" in balance
        assert "pending" in balance
        assert balance["currency"] == "USDC"
    
    def test_get_merchant_stats(self, merchant_service):
        """Test getting merchant statistics."""
        # Create some invoices
        inv1 = merchant_service.create_invoice("merchant_1", Decimal("100.00"))
        inv2 = merchant_service.create_invoice("merchant_1", Decimal("50.00"))
        merchant_service.pay_invoice(inv1.invoice_id, Decimal("100.00"), "w1", "tx1")
        
        stats = merchant_service.get_merchant_stats("merchant_1")
        
        assert stats["total_invoices"] == 2
        assert stats["paid_invoices"] == 1
        assert stats["pending_invoices"] == 1
        assert stats["total_received"] == "100.00"


class TestInvoiceWithItems:
    """Test invoices with line items."""
    
    def test_create_invoice_with_items(self):
        """Test creating invoice with line items."""
        service = MerchantService()
        
        items = [
            {"name": "Widget", "quantity": 2, "price": "25.00"},
            {"name": "Gadget", "quantity": 1, "price": "50.00"}
        ]
        
        invoice = service.create_invoice(
            merchant_id="merchant_1",
            amount=Decimal("100.00"),
            items=items,
            reference="ORDER-123"
        )
        
        assert len(invoice.items) == 2
        assert invoice.reference == "ORDER-123"


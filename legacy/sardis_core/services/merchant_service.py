"""
Merchant service for managing merchant operations.

Provides:
- Invoice/payment request creation
- Merchant payouts
- Settlement reports
- Merchant-specific webhook events
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional
import threading
import uuid

from sardis_core.models.merchant import Merchant


class InvoiceStatus(str, Enum):
    """Status of a payment invoice."""
    DRAFT = "draft"
    PENDING = "pending"
    PAID = "paid"
    PARTIALLY_PAID = "partially_paid"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class PayoutStatus(str, Enum):
    """Status of a merchant payout."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Invoice:
    """
    A payment request from a merchant.
    
    Merchants can create invoices to request payments from agents.
    """
    
    invoice_id: str = field(default_factory=lambda: f"inv_{uuid.uuid4().hex[:16]}")
    
    # Parties
    merchant_id: str = ""
    merchant_name: str = ""
    
    # Optional: specific agent to request from
    requested_from_agent_id: Optional[str] = None
    
    # Amount
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    
    # Partial payments
    amount_paid: Decimal = field(default_factory=lambda: Decimal("0"))
    allow_partial: bool = False
    
    # Details
    description: Optional[str] = None
    reference: Optional[str] = None  # Merchant's internal reference
    items: list[dict] = field(default_factory=list)
    
    # Status
    status: InvoiceStatus = InvoiceStatus.PENDING
    
    # Payment tracking
    payment_tx_ids: list[str] = field(default_factory=list)
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    due_date: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    
    # Webhooks
    callback_url: Optional[str] = None
    
    def is_expired(self) -> bool:
        """Check if invoice has expired."""
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return True
        return False
    
    def amount_remaining(self) -> Decimal:
        """Get remaining amount to be paid."""
        return max(Decimal("0"), self.amount - self.amount_paid)
    
    def record_payment(self, amount: Decimal, tx_id: str):
        """Record a payment against this invoice."""
        self.amount_paid += amount
        self.payment_tx_ids.append(tx_id)
        
        if self.amount_paid >= self.amount:
            self.status = InvoiceStatus.PAID
            self.paid_at = datetime.now(timezone.utc)
        elif self.amount_paid > Decimal("0"):
            self.status = InvoiceStatus.PARTIALLY_PAID
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "invoice_id": self.invoice_id,
            "merchant_id": self.merchant_id,
            "merchant_name": self.merchant_name,
            "amount": str(self.amount),
            "currency": self.currency,
            "amount_paid": str(self.amount_paid),
            "amount_remaining": str(self.amount_remaining()),
            "description": self.description,
            "reference": self.reference,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }


@dataclass
class Payout:
    """
    A payout from merchant balance to external wallet.
    """
    
    payout_id: str = field(default_factory=lambda: f"pay_{uuid.uuid4().hex[:16]}")
    
    # Merchant
    merchant_id: str = ""
    
    # Amount
    amount: Decimal = field(default_factory=lambda: Decimal("0"))
    fee: Decimal = field(default_factory=lambda: Decimal("0"))
    net_amount: Decimal = field(default_factory=lambda: Decimal("0"))
    currency: str = "USDC"
    
    # Destination
    destination_address: str = ""
    destination_chain: str = "base"
    
    # Status
    status: PayoutStatus = PayoutStatus.PENDING
    
    # On-chain details
    tx_hash: Optional[str] = None
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Error tracking
    error: Optional[str] = None


@dataclass
class SettlementReport:
    """
    Settlement report for a merchant over a period.
    """
    
    report_id: str = field(default_factory=lambda: f"rpt_{uuid.uuid4().hex[:12]}")
    
    merchant_id: str = ""
    
    # Period
    period_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    period_end: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Summary
    total_transactions: int = 0
    total_volume: Decimal = field(default_factory=lambda: Decimal("0"))
    total_fees: Decimal = field(default_factory=lambda: Decimal("0"))
    total_refunds: Decimal = field(default_factory=lambda: Decimal("0"))
    net_revenue: Decimal = field(default_factory=lambda: Decimal("0"))
    
    # Breakdown
    transactions: list[dict] = field(default_factory=list)
    
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MerchantService:
    """
    Service for merchant operations.
    
    Provides:
    - Invoice creation and management
    - Payout processing
    - Settlement reporting
    - Merchant webhooks
    """
    
    # Default invoice expiry (24 hours)
    DEFAULT_INVOICE_EXPIRY_HOURS = 24
    
    # Payout fee (flat rate)
    PAYOUT_FEE = Decimal("1.00")
    
    def __init__(self, ledger=None, webhook_manager=None):
        """Initialize the merchant service."""
        self._ledger = ledger
        self._webhook_manager = webhook_manager
        self._lock = threading.RLock()
        
        # Storage
        self._invoices: dict[str, Invoice] = {}
        self._payouts: dict[str, Payout] = {}
        self._merchant_invoices: dict[str, list[str]] = {}  # merchant_id -> invoice_ids
        self._merchant_payouts: dict[str, list[str]] = {}
    
    # ==================== Invoice Operations ====================
    
    def create_invoice(
        self,
        merchant_id: str,
        amount: Decimal,
        currency: str = "USDC",
        description: Optional[str] = None,
        reference: Optional[str] = None,
        items: Optional[list[dict]] = None,
        due_date: Optional[datetime] = None,
        expires_in_hours: Optional[int] = None,
        requested_from_agent_id: Optional[str] = None,
        allow_partial: bool = False,
        callback_url: Optional[str] = None
    ) -> Invoice:
        """
        Create a payment invoice.
        
        Args:
            merchant_id: Merchant creating the invoice
            amount: Total amount to be paid
            currency: Currency code
            description: Invoice description
            reference: Merchant's internal reference
            items: List of line items
            due_date: Payment due date
            expires_in_hours: Hours until invoice expires
            requested_from_agent_id: Specific agent to request from
            allow_partial: Whether to allow partial payments
            callback_url: URL to notify when paid
            
        Returns:
            Created Invoice
        """
        expiry_hours = expires_in_hours or self.DEFAULT_INVOICE_EXPIRY_HOURS
        expires_at = datetime.now(timezone.utc) + timedelta(hours=expiry_hours)
        
        invoice = Invoice(
            merchant_id=merchant_id,
            amount=amount,
            currency=currency,
            description=description,
            reference=reference,
            items=items or [],
            due_date=due_date,
            expires_at=expires_at,
            requested_from_agent_id=requested_from_agent_id,
            allow_partial=allow_partial,
            callback_url=callback_url,
        )
        
        with self._lock:
            self._invoices[invoice.invoice_id] = invoice
            
            if merchant_id not in self._merchant_invoices:
                self._merchant_invoices[merchant_id] = []
            self._merchant_invoices[merchant_id].append(invoice.invoice_id)
        
        self._emit_event("invoice.created", invoice=invoice.to_dict())
        
        return invoice
    
    def get_invoice(self, invoice_id: str) -> Optional[Invoice]:
        """Get an invoice by ID."""
        return self._invoices.get(invoice_id)
    
    def list_merchant_invoices(
        self,
        merchant_id: str,
        status: Optional[InvoiceStatus] = None,
        limit: int = 50
    ) -> list[Invoice]:
        """List invoices for a merchant."""
        invoice_ids = self._merchant_invoices.get(merchant_id, [])
        invoices = [self._invoices[iid] for iid in invoice_ids if iid in self._invoices]
        
        if status:
            invoices = [inv for inv in invoices if inv.status == status]
        
        # Sort by created_at descending
        invoices.sort(key=lambda i: i.created_at, reverse=True)
        
        return invoices[:limit]
    
    def pay_invoice(
        self,
        invoice_id: str,
        amount: Decimal,
        payer_wallet_id: str,
        tx_id: str
    ) -> tuple[bool, str]:
        """
        Record a payment against an invoice.
        
        Returns (success, message).
        """
        with self._lock:
            invoice = self._invoices.get(invoice_id)
            if not invoice:
                return False, "Invoice not found"
            
            if invoice.status == InvoiceStatus.PAID:
                return False, "Invoice already paid"
            
            if invoice.status == InvoiceStatus.CANCELLED:
                return False, "Invoice was cancelled"
            
            if invoice.is_expired():
                invoice.status = InvoiceStatus.EXPIRED
                return False, "Invoice has expired"
            
            remaining = invoice.amount_remaining()
            
            if amount > remaining:
                return False, f"Payment amount {amount} exceeds remaining {remaining}"
            
            if amount < remaining and not invoice.allow_partial:
                return False, f"Partial payments not allowed. Required: {remaining}"
            
            invoice.record_payment(amount, tx_id)
            
            self._emit_event(
                "invoice.paid" if invoice.status == InvoiceStatus.PAID else "invoice.payment_received",
                invoice=invoice.to_dict(),
                payment_amount=str(amount),
                tx_id=tx_id,
            )
            
            return True, "Payment recorded"
    
    def cancel_invoice(self, invoice_id: str, reason: Optional[str] = None) -> bool:
        """Cancel an invoice."""
        with self._lock:
            invoice = self._invoices.get(invoice_id)
            if not invoice:
                return False
            
            if invoice.status == InvoiceStatus.PAID:
                return False  # Can't cancel paid invoice
            
            invoice.status = InvoiceStatus.CANCELLED
            
            self._emit_event("invoice.cancelled", invoice_id=invoice_id, reason=reason)
            
            return True
    
    # ==================== Payout Operations ====================
    
    def request_payout(
        self,
        merchant_id: str,
        amount: Decimal,
        destination_address: str,
        destination_chain: str = "base",
        currency: str = "USDC"
    ) -> tuple[Optional[Payout], Optional[str]]:
        """
        Request a payout to an external wallet.
        
        Args:
            merchant_id: Merchant requesting payout
            amount: Amount to withdraw
            destination_address: External wallet address
            destination_chain: Blockchain to send on
            currency: Currency to withdraw
            
        Returns:
            (Payout, None) on success, (None, error) on failure
        """
        fee = self.PAYOUT_FEE
        net_amount = amount - fee
        
        if net_amount <= Decimal("0"):
            return None, f"Amount must exceed fee of {fee}"
        
        # In production, would verify merchant balance here
        
        payout = Payout(
            merchant_id=merchant_id,
            amount=amount,
            fee=fee,
            net_amount=net_amount,
            currency=currency,
            destination_address=destination_address,
            destination_chain=destination_chain,
        )
        
        with self._lock:
            self._payouts[payout.payout_id] = payout
            
            if merchant_id not in self._merchant_payouts:
                self._merchant_payouts[merchant_id] = []
            self._merchant_payouts[merchant_id].append(payout.payout_id)
        
        self._emit_event("merchant.payout_requested", payout_id=payout.payout_id)
        
        # In production, would queue for processing
        # For demo, simulate immediate processing
        self._process_payout(payout.payout_id)
        
        return payout, None
    
    def _process_payout(self, payout_id: str):
        """Process a payout (simulated for demo)."""
        payout = self._payouts.get(payout_id)
        if not payout:
            return
        
        payout.status = PayoutStatus.PROCESSING
        payout.processed_at = datetime.now(timezone.utc)
        
        # Simulate on-chain submission
        import uuid
        payout.tx_hash = f"0x{uuid.uuid4().hex}"
        payout.status = PayoutStatus.COMPLETED
        payout.completed_at = datetime.now(timezone.utc)
        
        self._emit_event(
            "merchant.payout_completed",
            payout_id=payout_id,
            tx_hash=payout.tx_hash,
        )
    
    def get_payout(self, payout_id: str) -> Optional[Payout]:
        """Get a payout by ID."""
        return self._payouts.get(payout_id)
    
    def list_merchant_payouts(
        self,
        merchant_id: str,
        status: Optional[PayoutStatus] = None,
        limit: int = 50
    ) -> list[Payout]:
        """List payouts for a merchant."""
        payout_ids = self._merchant_payouts.get(merchant_id, [])
        payouts = [self._payouts[pid] for pid in payout_ids if pid in self._payouts]
        
        if status:
            payouts = [p for p in payouts if p.status == status]
        
        payouts.sort(key=lambda p: p.created_at, reverse=True)
        
        return payouts[:limit]
    
    # ==================== Settlement Reporting ====================
    
    def generate_settlement_report(
        self,
        merchant_id: str,
        period_start: datetime,
        period_end: datetime
    ) -> SettlementReport:
        """
        Generate a settlement report for a period.
        
        Args:
            merchant_id: Merchant to generate report for
            period_start: Start of reporting period
            period_end: End of reporting period
            
        Returns:
            SettlementReport with summary and transactions
        """
        # In production, this would query the ledger
        report = SettlementReport(
            merchant_id=merchant_id,
            period_start=period_start,
            period_end=period_end,
        )
        
        # Get paid invoices in period
        invoices = self.list_merchant_invoices(merchant_id, status=InvoiceStatus.PAID)
        
        for invoice in invoices:
            if invoice.paid_at and period_start <= invoice.paid_at <= period_end:
                report.total_transactions += 1
                report.total_volume += invoice.amount_paid
                
                report.transactions.append({
                    "invoice_id": invoice.invoice_id,
                    "amount": str(invoice.amount_paid),
                    "paid_at": invoice.paid_at.isoformat(),
                })
        
        # Calculate fees (example: 1% of volume)
        report.total_fees = (report.total_volume * Decimal("0.01")).quantize(Decimal("0.01"))
        report.net_revenue = report.total_volume - report.total_fees - report.total_refunds
        
        return report
    
    # ==================== Balance & Stats ====================
    
    def get_merchant_balance(self, merchant_id: str) -> dict:
        """Get merchant's current balance."""
        # In production, would query ledger
        # For demo, return mock data
        return {
            "merchant_id": merchant_id,
            "available": "1000.00",
            "pending": "150.00",
            "total": "1150.00",
            "currency": "USDC",
        }
    
    def get_merchant_stats(self, merchant_id: str) -> dict:
        """Get merchant statistics."""
        invoices = self.list_merchant_invoices(merchant_id)
        payouts = self.list_merchant_payouts(merchant_id)
        
        paid_invoices = [i for i in invoices if i.status == InvoiceStatus.PAID]
        total_received = sum(i.amount_paid for i in paid_invoices)
        total_withdrawn = sum(p.net_amount for p in payouts if p.status == PayoutStatus.COMPLETED)
        
        return {
            "merchant_id": merchant_id,
            "total_invoices": len(invoices),
            "paid_invoices": len(paid_invoices),
            "pending_invoices": len([i for i in invoices if i.status == InvoiceStatus.PENDING]),
            "total_received": str(total_received),
            "total_withdrawn": str(total_withdrawn),
            "total_payouts": len(payouts),
        }
    
    # ==================== Webhook Helpers ====================
    
    def _emit_event(self, event_type: str, **data):
        """Emit a webhook event."""
        if not self._webhook_manager:
            return
        
        try:
            from sardis_core.webhooks.events import WebhookEvent, EventType
            
            event_map = {
                "invoice.created": EventType.INVOICE_CREATED,
                "invoice.paid": EventType.INVOICE_PAID,
                "invoice.payment_received": EventType.INVOICE_PAID,
                "invoice.cancelled": EventType.INVOICE_PAID,
                "merchant.payout_requested": EventType.MERCHANT_PAYOUT,
                "merchant.payout_completed": EventType.MERCHANT_PAYOUT,
            }
            
            event_enum = event_map.get(event_type)
            if event_enum:
                event = WebhookEvent(event_type=event_enum, data=data)
                # Emit asynchronously
                import asyncio
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self._webhook_manager.emit(event))
                except RuntimeError:
                    pass
        except Exception:
            pass  # Don't let webhook errors affect operations


# Global merchant service instance
_merchant_service: Optional[MerchantService] = None


def get_merchant_service() -> MerchantService:
    """Get the global merchant service instance."""
    global _merchant_service
    if _merchant_service is None:
        _merchant_service = MerchantService()
    return _merchant_service


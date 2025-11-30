"""Agent-to-Agent Payment Protocol.

Defines the protocol for service requests, responses, escrow,
and agent-to-agent payments.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Optional, Dict, Any, List
import secrets


class EscrowStatus(str, Enum):
    """Status of an escrow payment."""
    CREATED = "created"
    FUNDED = "funded"
    RELEASED = "released"
    REFUNDED = "refunded"
    DISPUTED = "disputed"
    EXPIRED = "expired"


class RequestStatus(str, Enum):
    """Status of a service request."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    DISPUTED = "disputed"


@dataclass
class PaymentTerms:
    """Payment terms for a service request."""
    total_amount: Decimal
    currency: str = "USDC"
    
    # Payment structure
    upfront_percentage: Decimal = Decimal("0")  # % paid upfront
    completion_percentage: Decimal = Decimal("100")  # % paid on completion
    
    # Escrow settings
    use_escrow: bool = True
    escrow_timeout_hours: int = 72  # Auto-release/refund after this time
    
    # Dispute resolution
    dispute_window_hours: int = 24  # Time to dispute after delivery
    
    # Calculated amounts
    @property
    def upfront_amount(self) -> Decimal:
        return self.total_amount * (self.upfront_percentage / 100)
    
    @property
    def completion_amount(self) -> Decimal:
        return self.total_amount * (self.completion_percentage / 100)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_amount": str(self.total_amount),
            "currency": self.currency,
            "upfront_percentage": str(self.upfront_percentage),
            "completion_percentage": str(self.completion_percentage),
            "upfront_amount": str(self.upfront_amount),
            "completion_amount": str(self.completion_amount),
            "use_escrow": self.use_escrow,
            "escrow_timeout_hours": self.escrow_timeout_hours,
            "dispute_window_hours": self.dispute_window_hours,
        }


@dataclass
class Escrow:
    """Escrow for a service payment."""
    escrow_id: str = field(default_factory=lambda: f"esc_{secrets.token_hex(8)}")
    request_id: str = ""
    
    # Parties
    payer_agent_id: str = ""
    payer_wallet_id: str = ""
    payee_agent_id: str = ""
    payee_wallet_id: str = ""
    
    # Amount
    amount: Decimal = Decimal("0")
    currency: str = "USDC"
    
    # Status
    status: EscrowStatus = EscrowStatus.CREATED
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    funded_at: Optional[datetime] = None
    released_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    
    # Transaction IDs
    funding_tx_id: Optional[str] = None
    release_tx_id: Optional[str] = None
    refund_tx_id: Optional[str] = None
    
    # Dispute
    dispute_reason: Optional[str] = None
    dispute_resolution: Optional[str] = None
    
    def fund(self, tx_id: str, timeout_hours: int = 72):
        """Mark escrow as funded."""
        self.status = EscrowStatus.FUNDED
        self.funded_at = datetime.now(timezone.utc)
        self.funding_tx_id = tx_id
        self.expires_at = self.funded_at + timedelta(hours=timeout_hours)
    
    def release(self, tx_id: str):
        """Release funds to payee."""
        self.status = EscrowStatus.RELEASED
        self.released_at = datetime.now(timezone.utc)
        self.release_tx_id = tx_id
    
    def refund(self, tx_id: str):
        """Refund funds to payer."""
        self.status = EscrowStatus.REFUNDED
        self.released_at = datetime.now(timezone.utc)
        self.refund_tx_id = tx_id
    
    def dispute(self, reason: str):
        """Mark as disputed."""
        self.status = EscrowStatus.DISPUTED
        self.dispute_reason = reason
    
    @property
    def is_expired(self) -> bool:
        """Check if escrow has expired."""
        if not self.expires_at:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "escrow_id": self.escrow_id,
            "request_id": self.request_id,
            "payer_agent_id": self.payer_agent_id,
            "payee_agent_id": self.payee_agent_id,
            "amount": str(self.amount),
            "currency": self.currency,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "funded_at": self.funded_at.isoformat() if self.funded_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "is_expired": self.is_expired,
        }


@dataclass
class ServiceRequest:
    """A request from one agent to another for a service."""
    request_id: str = field(default_factory=lambda: f"req_{secrets.token_hex(8)}")
    
    # Parties
    requester_agent_id: str = ""
    requester_wallet_id: str = ""
    provider_agent_id: str = ""
    provider_wallet_id: str = ""
    
    # Service
    service_id: str = ""
    service_name: str = ""
    
    # Request details
    input_data: Dict[str, Any] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Payment
    payment_terms: Optional[PaymentTerms] = None
    escrow: Optional[Escrow] = None
    
    # Status
    status: RequestStatus = RequestStatus.PENDING
    
    # Timing
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accepted_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Deadline
    deadline: Optional[datetime] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def accept(self):
        """Provider accepts the request."""
        self.status = RequestStatus.ACCEPTED
        self.accepted_at = datetime.now(timezone.utc)
    
    def start(self):
        """Provider starts working on the request."""
        self.status = RequestStatus.IN_PROGRESS
        self.started_at = datetime.now(timezone.utc)
    
    def complete(self):
        """Mark request as completed."""
        self.status = RequestStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc)
    
    def fail(self, reason: str = ""):
        """Mark request as failed."""
        self.status = RequestStatus.FAILED
        self.completed_at = datetime.now(timezone.utc)
        self.metadata["failure_reason"] = reason
    
    def cancel(self, reason: str = ""):
        """Cancel the request."""
        self.status = RequestStatus.CANCELLED
        self.completed_at = datetime.now(timezone.utc)
        self.metadata["cancel_reason"] = reason
    
    @property
    def is_past_deadline(self) -> bool:
        """Check if request is past deadline."""
        if not self.deadline:
            return False
        return datetime.now(timezone.utc) > self.deadline
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "requester_agent_id": self.requester_agent_id,
            "provider_agent_id": self.provider_agent_id,
            "service_id": self.service_id,
            "service_name": self.service_name,
            "input_data": self.input_data,
            "parameters": self.parameters,
            "payment_terms": self.payment_terms.to_dict() if self.payment_terms else None,
            "escrow": self.escrow.to_dict() if self.escrow else None,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "accepted_at": self.accepted_at.isoformat() if self.accepted_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "is_past_deadline": self.is_past_deadline,
        }


@dataclass
class ServiceResponse:
    """Response from a service provider."""
    response_id: str = field(default_factory=lambda: f"res_{secrets.token_hex(8)}")
    request_id: str = ""
    
    # Result
    success: bool = False
    output_data: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    
    # Metrics
    processing_time_ms: int = 0
    units_consumed: int = 0
    
    # Timestamp
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "response_id": self.response_id,
            "request_id": self.request_id,
            "success": self.success,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "processing_time_ms": self.processing_time_ms,
            "units_consumed": self.units_consumed,
            "created_at": self.created_at.isoformat(),
        }


class MarketplaceProtocol:
    """
    Protocol handler for agent-to-agent payments.
    
    Manages the lifecycle of service requests, escrow, and payments.
    """
    
    def __init__(self, payment_service=None):
        self._requests: Dict[str, ServiceRequest] = {}
        self._escrows: Dict[str, Escrow] = {}
        self._responses: Dict[str, List[ServiceResponse]] = {}
        self._payment_service = payment_service
    
    def create_request(
        self,
        requester_agent_id: str,
        requester_wallet_id: str,
        provider_agent_id: str,
        provider_wallet_id: str,
        service_id: str,
        service_name: str,
        payment_terms: PaymentTerms,
        input_data: Optional[Dict[str, Any]] = None,
        parameters: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
    ) -> ServiceRequest:
        """
        Create a new service request.
        
        Args:
            requester_agent_id: Agent requesting service
            requester_wallet_id: Wallet for payment
            provider_agent_id: Agent providing service
            provider_wallet_id: Wallet to receive payment
            service_id: Service being requested
            service_name: Name of service
            payment_terms: Payment configuration
            input_data: Input for the service
            parameters: Additional parameters
            deadline: Optional deadline
            
        Returns:
            Created ServiceRequest
        """
        request = ServiceRequest(
            requester_agent_id=requester_agent_id,
            requester_wallet_id=requester_wallet_id,
            provider_agent_id=provider_agent_id,
            provider_wallet_id=provider_wallet_id,
            service_id=service_id,
            service_name=service_name,
            payment_terms=payment_terms,
            input_data=input_data or {},
            parameters=parameters or {},
            deadline=deadline,
        )
        
        # Create escrow if needed
        if payment_terms.use_escrow:
            escrow = Escrow(
                request_id=request.request_id,
                payer_agent_id=requester_agent_id,
                payer_wallet_id=requester_wallet_id,
                payee_agent_id=provider_agent_id,
                payee_wallet_id=provider_wallet_id,
                amount=payment_terms.total_amount,
                currency=payment_terms.currency,
            )
            request.escrow = escrow
            self._escrows[escrow.escrow_id] = escrow
        
        self._requests[request.request_id] = request
        self._responses[request.request_id] = []
        
        return request
    
    def get_request(self, request_id: str) -> Optional[ServiceRequest]:
        """Get a request by ID."""
        return self._requests.get(request_id)
    
    def fund_escrow(self, request_id: str, tx_id: str) -> Optional[Escrow]:
        """
        Fund the escrow for a request.
        
        In production, this would verify the actual payment occurred.
        """
        request = self._requests.get(request_id)
        if not request or not request.escrow:
            return None
        
        escrow = request.escrow
        timeout = request.payment_terms.escrow_timeout_hours if request.payment_terms else 72
        escrow.fund(tx_id, timeout)
        
        return escrow
    
    def accept_request(self, request_id: str) -> Optional[ServiceRequest]:
        """Provider accepts a request."""
        request = self._requests.get(request_id)
        if not request:
            return None
        
        if request.status != RequestStatus.PENDING:
            return None
        
        request.accept()
        return request
    
    def start_request(self, request_id: str) -> Optional[ServiceRequest]:
        """Provider starts working on request."""
        request = self._requests.get(request_id)
        if not request:
            return None
        
        if request.status != RequestStatus.ACCEPTED:
            return None
        
        request.start()
        return request
    
    def complete_request(
        self,
        request_id: str,
        output_data: Dict[str, Any],
        processing_time_ms: int = 0,
        units_consumed: int = 0,
    ) -> Optional[ServiceResponse]:
        """
        Complete a request and create response.
        
        This will also trigger escrow release.
        """
        request = self._requests.get(request_id)
        if not request:
            return None
        
        if request.status != RequestStatus.IN_PROGRESS:
            return None
        
        # Create response
        response = ServiceResponse(
            request_id=request_id,
            success=True,
            output_data=output_data,
            processing_time_ms=processing_time_ms,
            units_consumed=units_consumed,
        )
        
        self._responses[request_id].append(response)
        request.complete()
        
        # Release escrow (in production, would create actual transaction)
        if request.escrow and request.escrow.status == EscrowStatus.FUNDED:
            release_tx = f"tx_release_{secrets.token_hex(8)}"
            request.escrow.release(release_tx)
        
        return response
    
    def fail_request(
        self,
        request_id: str,
        error_message: str
    ) -> Optional[ServiceResponse]:
        """
        Fail a request and potentially refund escrow.
        """
        request = self._requests.get(request_id)
        if not request:
            return None
        
        # Create failure response
        response = ServiceResponse(
            request_id=request_id,
            success=False,
            error_message=error_message,
        )
        
        self._responses[request_id].append(response)
        request.fail(error_message)
        
        # Refund escrow if funded
        if request.escrow and request.escrow.status == EscrowStatus.FUNDED:
            refund_tx = f"tx_refund_{secrets.token_hex(8)}"
            request.escrow.refund(refund_tx)
        
        return response
    
    def dispute_request(
        self,
        request_id: str,
        reason: str,
        disputer_agent_id: str
    ) -> Optional[ServiceRequest]:
        """
        Dispute a completed request.
        
        Opens a dispute window for resolution.
        """
        request = self._requests.get(request_id)
        if not request:
            return None
        
        # Can only dispute completed requests within window
        if request.status != RequestStatus.COMPLETED:
            return None
        
        if not request.completed_at or not request.payment_terms:
            return None
        
        # Check if still within dispute window
        dispute_deadline = request.completed_at + timedelta(
            hours=request.payment_terms.dispute_window_hours
        )
        if datetime.now(timezone.utc) > dispute_deadline:
            return None
        
        request.status = RequestStatus.DISPUTED
        
        if request.escrow:
            request.escrow.dispute(reason)
        
        request.metadata["dispute"] = {
            "reason": reason,
            "disputer": disputer_agent_id,
            "disputed_at": datetime.now(timezone.utc).isoformat(),
        }
        
        return request
    
    def list_requests(
        self,
        agent_id: Optional[str] = None,
        status: Optional[RequestStatus] = None,
        as_requester: bool = True,
        as_provider: bool = True,
        limit: int = 50,
    ) -> List[ServiceRequest]:
        """List requests with filters."""
        requests = list(self._requests.values())
        
        if agent_id:
            filtered = []
            for req in requests:
                if as_requester and req.requester_agent_id == agent_id:
                    filtered.append(req)
                elif as_provider and req.provider_agent_id == agent_id:
                    filtered.append(req)
            requests = filtered
        
        if status:
            requests = [r for r in requests if r.status == status]
        
        # Sort by created_at descending
        requests.sort(key=lambda r: r.created_at, reverse=True)
        
        return requests[:limit]
    
    def get_responses(self, request_id: str) -> List[ServiceResponse]:
        """Get all responses for a request."""
        return self._responses.get(request_id, [])


# Singleton instance
_protocol: Optional[MarketplaceProtocol] = None


def get_marketplace_protocol() -> MarketplaceProtocol:
    """Get or create the marketplace protocol singleton."""
    global _protocol
    if _protocol is None:
        _protocol = MarketplaceProtocol()
    return _protocol


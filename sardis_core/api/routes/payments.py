"""Payment API routes."""

from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
import uuid

from sardis_core.services import PaymentService
from sardis_core.api.dependencies import get_payment_service, get_wallet_service
from sardis_core.services.wallet_service import WalletService
from sardis_core.api.schemas import (
    PaymentRequest,
    PaymentResponse,
    TransactionResponse,
    EstimateResponse,
)

router = APIRouter(prefix="/payments", tags=["payments"])


# ========== Additional Schemas ==========

class HoldCreateRequest(BaseModel):
    """Request to create a hold on funds."""
    agent_id: str = Field(..., description="Agent whose funds to hold")
    merchant_id: Optional[str] = Field(None, description="Merchant for the hold")
    amount: Decimal = Field(..., gt=0, description="Amount to hold")
    currency: str = Field(default="USDC")
    purpose: Optional[str] = Field(None, max_length=500)
    expires_in_minutes: int = Field(default=30, ge=5, le=1440)  # 5 min to 24 hours


class HoldResponse(BaseModel):
    """Response for hold operations."""
    success: bool
    hold_id: Optional[str] = None
    amount: Optional[str] = None
    currency: str = "USDC"
    expires_at: Optional[datetime] = None
    error: Optional[str] = None


class HoldCaptureRequest(BaseModel):
    """Request to capture a hold."""
    amount: Optional[Decimal] = Field(None, gt=0, description="Amount to capture (defaults to full hold)")


class RefundRequest(BaseModel):
    """Request to refund a transaction."""
    amount: Optional[Decimal] = Field(None, gt=0, description="Amount to refund (defaults to full)")
    reason: Optional[str] = Field(None, max_length=500)


class RefundResponse(BaseModel):
    """Response for refund operation."""
    success: bool
    refund_id: Optional[str] = None
    original_tx_id: str
    amount: Optional[str] = None
    error: Optional[str] = None


class PaymentRequestCreate(BaseModel):
    """Request to create a payment request (invoice)."""
    requester_agent_id: str = Field(..., description="Agent requesting the payment")
    payer_agent_id: str = Field(..., description="Agent expected to pay")
    amount: Decimal = Field(..., gt=0)
    currency: str = Field(default="USDC")
    description: Optional[str] = Field(None, max_length=500)
    expires_in_hours: int = Field(default=24, ge=1, le=168)  # 1 hour to 1 week


class PaymentRequestResponse(BaseModel):
    """Response for a payment request."""
    request_id: str
    requester_agent_id: str
    payer_agent_id: str
    amount: str
    currency: str
    description: Optional[str]
    status: str  # pending, paid, expired, cancelled
    created_at: datetime
    expires_at: datetime
    paid_at: Optional[datetime] = None
    transaction_id: Optional[str] = None


# In-memory storage for payment requests and holds (in production, use database)
_payment_requests: dict[str, dict] = {}
_holds: dict[str, dict] = {}


def transaction_to_response(tx) -> TransactionResponse:
    """Convert transaction model to response schema."""
    return TransactionResponse(
        tx_id=tx.tx_id,
        from_wallet=tx.from_wallet,
        to_wallet=tx.to_wallet,
        amount=str(tx.amount),
        fee=str(tx.fee),
        total_cost=str(tx.total_cost()),
        currency=tx.currency,
        purpose=tx.purpose,
        status=tx.status.value,
        error_message=tx.error_message,
        created_at=tx.created_at,
        completed_at=tx.completed_at
    )


@router.post(
    "",
    response_model=PaymentResponse,
    summary="Process a payment",
    description="Execute a payment from an agent to a merchant or recipient wallet."
)
async def create_payment(
    request: PaymentRequest,
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """Process a payment from an agent."""
    
    # Must specify either recipient_wallet_id or merchant_id
    if not request.recipient_wallet_id and not request.merchant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either recipient_wallet_id or merchant_id"
        )
    
    # Process payment
    if request.merchant_id:
        result = payment_service.pay_merchant(
            agent_id=request.agent_id,
            merchant_id=request.merchant_id,
            amount=request.amount,
            currency=request.currency,
            purpose=request.purpose
        )
    else:
        result = payment_service.pay(
            agent_id=request.agent_id,
            amount=request.amount,
            recipient_wallet_id=request.recipient_wallet_id,
            currency=request.currency,
            purpose=request.purpose
        )
    
    # Build response
    tx_response = None
    if result.transaction:
        tx_response = transaction_to_response(result.transaction)
    
    return PaymentResponse(
        success=result.success,
        transaction=tx_response,
        error=result.error
    )


@router.post(
    "/request",
    response_model=PaymentRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment request",
    description="Create a payment request (invoice) that another agent can pay."
)
async def create_payment_request(
    request: PaymentRequestCreate,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> PaymentRequestResponse:
    """Create a payment request for another agent to pay."""
    
    # Verify requester exists
    requester = wallet_service.get_agent(request.requester_agent_id)
    if not requester:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Requester agent {request.requester_agent_id} not found"
        )
    
    # Verify payer exists
    payer = wallet_service.get_agent(request.payer_agent_id)
    if not payer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payer agent {request.payer_agent_id} not found"
        )
    
    # Create payment request
    now = datetime.now(timezone.utc)
    from datetime import timedelta
    
    request_id = f"preq_{uuid.uuid4().hex[:16]}"
    payment_req = {
        "request_id": request_id,
        "requester_agent_id": request.requester_agent_id,
        "requester_wallet_id": requester.wallet_id,
        "payer_agent_id": request.payer_agent_id,
        "amount": request.amount,
        "currency": request.currency,
        "description": request.description,
        "status": "pending",
        "created_at": now,
        "expires_at": now + timedelta(hours=request.expires_in_hours),
        "paid_at": None,
        "transaction_id": None,
    }
    
    _payment_requests[request_id] = payment_req
    
    return PaymentRequestResponse(
        request_id=request_id,
        requester_agent_id=payment_req["requester_agent_id"],
        payer_agent_id=payment_req["payer_agent_id"],
        amount=str(payment_req["amount"]),
        currency=payment_req["currency"],
        description=payment_req["description"],
        status=payment_req["status"],
        created_at=payment_req["created_at"],
        expires_at=payment_req["expires_at"]
    )


@router.get(
    "/request/{request_id}",
    response_model=PaymentRequestResponse,
    summary="Get payment request",
    description="Get details of a payment request."
)
async def get_payment_request(request_id: str) -> PaymentRequestResponse:
    """Get a payment request by ID."""
    
    payment_req = _payment_requests.get(request_id)
    if not payment_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment request {request_id} not found"
        )
    
    # Check if expired
    if payment_req["status"] == "pending" and datetime.now(timezone.utc) > payment_req["expires_at"]:
        payment_req["status"] = "expired"
    
    return PaymentRequestResponse(
        request_id=payment_req["request_id"],
        requester_agent_id=payment_req["requester_agent_id"],
        payer_agent_id=payment_req["payer_agent_id"],
        amount=str(payment_req["amount"]),
        currency=payment_req["currency"],
        description=payment_req["description"],
        status=payment_req["status"],
        created_at=payment_req["created_at"],
        expires_at=payment_req["expires_at"],
        paid_at=payment_req["paid_at"],
        transaction_id=payment_req["transaction_id"]
    )


@router.post(
    "/request/{request_id}/pay",
    response_model=PaymentResponse,
    summary="Pay a payment request",
    description="Pay a pending payment request."
)
async def pay_payment_request(
    request_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """Pay a payment request."""
    
    payment_req = _payment_requests.get(request_id)
    if not payment_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment request {request_id} not found"
        )
    
    # Check status
    if payment_req["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment request is {payment_req['status']}, cannot pay"
        )
    
    # Check expiry
    if datetime.now(timezone.utc) > payment_req["expires_at"]:
        payment_req["status"] = "expired"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment request has expired"
        )
    
    # Process payment
    result = payment_service.pay(
        agent_id=payment_req["payer_agent_id"],
        amount=payment_req["amount"],
        recipient_wallet_id=payment_req["requester_wallet_id"],
        currency=payment_req["currency"],
        purpose=payment_req["description"] or f"Payment for request {request_id}"
    )
    
    if result.success:
        payment_req["status"] = "paid"
        payment_req["paid_at"] = datetime.now(timezone.utc)
        payment_req["transaction_id"] = result.transaction.tx_id
    
    tx_response = None
    if result.transaction:
        tx_response = transaction_to_response(result.transaction)
    
    return PaymentResponse(
        success=result.success,
        transaction=tx_response,
        error=result.error
    )


@router.delete(
    "/request/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel payment request",
    description="Cancel a pending payment request."
)
async def cancel_payment_request(request_id: str):
    """Cancel a payment request."""
    
    payment_req = _payment_requests.get(request_id)
    if not payment_req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment request {request_id} not found"
        )
    
    if payment_req["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel request with status {payment_req['status']}"
        )
    
    payment_req["status"] = "cancelled"


# ========== Hold Endpoints (Pre-Authorization) ==========


@router.post(
    "/holds",
    response_model=HoldResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create payment hold",
    description="Create a hold (pre-authorization) on agent funds."
)
async def create_hold(
    request: HoldCreateRequest,
    payment_service: PaymentService = Depends(get_payment_service),
    wallet_service: WalletService = Depends(get_wallet_service)
) -> HoldResponse:
    """Create a hold on funds for later capture."""
    
    # Verify agent exists
    agent = wallet_service.get_agent(request.agent_id)
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {request.agent_id} not found"
        )
    
    # Check balance
    wallet = wallet_service.get_wallet(agent.wallet_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent wallet not found"
        )
    
    # Access wallet balance (Wallet is a Pydantic model)
    available = getattr(wallet, 'available_balance', wallet.balance)
    if available < request.amount:
        return HoldResponse(
            success=False,
            error=f"Insufficient funds. Available: {available}, Required: {request.amount}"
        )
    
    # Create hold
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    hold_id = f"hold_{uuid.uuid4().hex[:16]}"
    
    hold = {
        "hold_id": hold_id,
        "agent_id": request.agent_id,
        "wallet_id": agent.wallet_id,
        "merchant_id": request.merchant_id,
        "amount": request.amount,
        "currency": request.currency,
        "purpose": request.purpose,
        "status": "active",
        "created_at": now,
        "expires_at": now + timedelta(minutes=request.expires_in_minutes),
        "captured_amount": Decimal("0"),
        "captured_at": None,
        "voided_at": None,
    }
    
    _holds[hold_id] = hold
    
    # Update wallet available balance (in a real system, this would be in the ledger)
    # For demo purposes, we track holds separately
    
    return HoldResponse(
        success=True,
        hold_id=hold_id,
        amount=str(request.amount),
        currency=request.currency,
        expires_at=hold["expires_at"]
    )


@router.get(
    "/holds/{hold_id}",
    response_model=HoldResponse,
    summary="Get hold details",
    description="Get details of a specific hold."
)
async def get_hold(hold_id: str) -> HoldResponse:
    """Get hold details."""
    
    hold = _holds.get(hold_id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hold {hold_id} not found"
        )
    
    # Check if expired
    if hold["status"] == "active" and datetime.now(timezone.utc) > hold["expires_at"]:
        hold["status"] = "expired"
    
    return HoldResponse(
        success=True,
        hold_id=hold["hold_id"],
        amount=str(hold["amount"]),
        currency=hold["currency"],
        expires_at=hold["expires_at"]
    )


@router.post(
    "/holds/{hold_id}/capture",
    response_model=PaymentResponse,
    summary="Capture hold",
    description="Capture (finalize) a payment hold."
)
async def capture_hold(
    hold_id: str,
    request: Optional[HoldCaptureRequest] = None,
    payment_service: PaymentService = Depends(get_payment_service)
) -> PaymentResponse:
    """Capture a hold to complete the payment."""
    
    hold = _holds.get(hold_id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hold {hold_id} not found"
        )
    
    if hold["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hold is {hold['status']}, cannot capture"
        )
    
    # Check expiry
    if datetime.now(timezone.utc) > hold["expires_at"]:
        hold["status"] = "expired"
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Hold has expired"
        )
    
    # Determine capture amount
    capture_amount = request.amount if request and request.amount else hold["amount"]
    
    if capture_amount > hold["amount"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot capture {capture_amount}, hold is only for {hold['amount']}"
        )
    
    # Process payment
    result = payment_service.pay_merchant(
        agent_id=hold["agent_id"],
        merchant_id=hold["merchant_id"] or "system",
        amount=capture_amount,
        currency=hold["currency"],
        purpose=hold["purpose"] or f"Capture of hold {hold_id}"
    )
    
    if result.success:
        hold["status"] = "captured"
        hold["captured_amount"] = capture_amount
        hold["captured_at"] = datetime.now(timezone.utc)
    
    tx_response = None
    if result.transaction:
        tx_response = transaction_to_response(result.transaction)
    
    return PaymentResponse(
        success=result.success,
        transaction=tx_response,
        error=result.error
    )


@router.post(
    "/holds/{hold_id}/void",
    response_model=HoldResponse,
    summary="Void hold",
    description="Void (cancel) a payment hold, releasing the funds."
)
async def void_hold(hold_id: str) -> HoldResponse:
    """Void a hold to release the funds."""
    
    hold = _holds.get(hold_id)
    if not hold:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Hold {hold_id} not found"
        )
    
    if hold["status"] != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Hold is {hold['status']}, cannot void"
        )
    
    hold["status"] = "voided"
    hold["voided_at"] = datetime.now(timezone.utc)
    
    return HoldResponse(
        success=True,
        hold_id=hold_id,
        amount=str(hold["amount"]),
        currency=hold["currency"]
    )


@router.get(
    "/holds/agent/{agent_id}",
    response_model=list[HoldResponse],
    summary="List agent holds",
    description="List all holds for an agent."
)
async def list_agent_holds(
    agent_id: str,
    status_filter: Optional[str] = None
) -> list[HoldResponse]:
    """List holds for an agent."""
    
    agent_holds = [h for h in _holds.values() if h["agent_id"] == agent_id]
    
    if status_filter:
        agent_holds = [h for h in agent_holds if h["status"] == status_filter]
    
    # Check for expiry
    now = datetime.now(timezone.utc)
    for hold in agent_holds:
        if hold["status"] == "active" and now > hold["expires_at"]:
            hold["status"] = "expired"
    
    return [
        HoldResponse(
            success=True,
            hold_id=h["hold_id"],
            amount=str(h["amount"]),
            currency=h["currency"],
            expires_at=h["expires_at"]
        )
        for h in agent_holds
    ]


# ========== Refund Endpoints ==========


@router.post(
    "/{tx_id}/refund",
    response_model=RefundResponse,
    summary="Refund transaction",
    description="Refund a completed transaction."
)
async def refund_transaction(
    tx_id: str,
    request: Optional[RefundRequest] = None,
    payment_service: PaymentService = Depends(get_payment_service)
) -> RefundResponse:
    """Refund a transaction."""
    
    # Get original transaction
    tx = payment_service.get_transaction(tx_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {tx_id} not found"
        )
    
    # Determine refund amount
    refund_amount = request.amount if request and request.amount else tx.amount
    
    if refund_amount > tx.amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot refund {refund_amount}, original was only {tx.amount}"
        )
    
    # Process refund
    result = payment_service.refund(
        tx_id=tx_id,
        amount=refund_amount,
        reason=request.reason if request else None
    )
    
    if result.success:
        return RefundResponse(
            success=True,
            refund_id=result.transaction.tx_id if result.transaction else None,
            original_tx_id=tx_id,
            amount=str(refund_amount)
        )
    else:
        return RefundResponse(
            success=False,
            original_tx_id=tx_id,
            error=result.error
        )


@router.get(
    "/estimate",
    response_model=EstimateResponse,
    summary="Estimate payment cost",
    description="Get an estimate of the total cost including fees for a payment."
)
async def estimate_payment(
    amount: Decimal,
    currency: str = "USDC",
    payment_service: PaymentService = Depends(get_payment_service)
) -> EstimateResponse:
    """Estimate total payment cost including fees."""
    estimate = payment_service.estimate_payment(amount, currency)
    return EstimateResponse(**estimate)


@router.get(
    "/{tx_id}",
    response_model=TransactionResponse,
    summary="Get transaction by ID",
    description="Retrieve details of a specific transaction."
)
async def get_transaction(
    tx_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
) -> TransactionResponse:
    """Get transaction details."""
    tx = payment_service.get_transaction(tx_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {tx_id} not found"
        )
    return transaction_to_response(tx)


@router.get(
    "/agent/{agent_id}",
    response_model=list[TransactionResponse],
    summary="List agent transactions",
    description="Get the transaction history for an agent."
)
async def list_agent_transactions(
    agent_id: str,
    limit: int = 50,
    offset: int = 0,
    payment_service: PaymentService = Depends(get_payment_service)
) -> list[TransactionResponse]:
    """List transactions for an agent."""
    transactions = payment_service.list_agent_transactions(
        agent_id=agent_id,
        limit=limit,
        offset=offset
    )
    return [transaction_to_response(tx) for tx in transactions]


# ========== On-Chain Verification Endpoints ==========


class OnChainRecordResponse(BaseModel):
    """On-chain transaction record for verification."""
    chain: str
    tx_hash: str
    block_number: Optional[int] = None
    from_address: str
    to_address: str
    explorer_url: Optional[str] = None
    status: str


class VerificationResponse(BaseModel):
    """Transaction verification data for auditing."""
    sardis_tx_id: str
    amount: str
    fee: str
    currency: str
    status: str
    created_at: datetime
    is_on_chain: bool
    chain_records: list[OnChainRecordResponse]
    verification_message: str


@router.get(
    "/{tx_id}/verify",
    response_model=VerificationResponse,
    summary="Verify transaction on-chain",
    description="Get on-chain verification data for a transaction."
)
async def verify_transaction(
    tx_id: str,
    payment_service: PaymentService = Depends(get_payment_service)
) -> VerificationResponse:
    """
    Get on-chain verification data for a transaction.
    
    This endpoint returns all blockchain records associated with an
    internal Sardis transaction, allowing third parties to verify
    the payment independently on block explorers.
    """
    tx = payment_service.get_transaction(tx_id)
    if not tx:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Transaction {tx_id} not found"
        )
    
    # Build verification data
    chain_records = []
    for record in tx.on_chain_records:
        chain_records.append(OnChainRecordResponse(
            chain=record.chain,
            tx_hash=record.tx_hash,
            block_number=record.block_number,
            from_address=record.from_address,
            to_address=record.to_address,
            explorer_url=record.explorer_url,
            status=record.status
        ))
    
    # Build verification message
    if tx.is_settled_on_chain:
        if chain_records:
            verification_message = f"Transaction verified on {chain_records[0].chain}. " \
                                   f"View on explorer: {chain_records[0].explorer_url}"
        else:
            verification_message = "Transaction is settled on-chain."
    else:
        if tx.status.value == "completed":
            verification_message = "Transaction completed in internal ledger. " \
                                   "On-chain settlement pending or using internal_ledger_only mode."
        else:
            verification_message = f"Transaction status: {tx.status.value}"
    
    return VerificationResponse(
        sardis_tx_id=tx.tx_id,
        amount=str(tx.amount),
        fee=str(tx.fee),
        currency=tx.currency,
        status=tx.status.value,
        created_at=tx.created_at,
        is_on_chain=tx.is_settled_on_chain,
        chain_records=chain_records,
        verification_message=verification_message
    )

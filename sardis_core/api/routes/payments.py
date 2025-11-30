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


# In-memory storage for payment requests (in production, use database)
_payment_requests: dict[str, dict] = {}


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

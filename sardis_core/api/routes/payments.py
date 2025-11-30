"""Payment API routes."""

from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status

from sardis_core.services import PaymentService
from sardis_core.api.dependencies import get_payment_service
from sardis_core.api.schemas import (
    PaymentRequest,
    PaymentResponse,
    TransactionResponse,
    EstimateResponse,
)

router = APIRouter(prefix="/payments", tags=["payments"])


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


"""Merchant API routes."""

from fastapi import APIRouter, Depends, HTTPException, status

from sardis_core.services import WalletService
from sardis_core.api.dependencies import get_wallet_service
from sardis_core.api.schemas import (
    CreateMerchantRequest,
    MerchantResponse,
    WalletResponse,
)
from sardis_core.api.routes.agents import wallet_to_response

from sardis_core.api.auth import get_api_key

router = APIRouter(
    prefix="/merchants", 
    tags=["Merchants"],
    dependencies=[Depends(get_api_key)]
)


def merchant_to_response(merchant) -> MerchantResponse:
    """Convert merchant model to response schema."""
    return MerchantResponse(
        merchant_id=merchant.merchant_id,
        name=merchant.name,
        wallet_id=merchant.wallet_id,
        description=merchant.description,
        category=merchant.category,
        is_active=merchant.is_active,
        created_at=merchant.created_at
    )


@router.post(
    "",
    response_model=MerchantResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new merchant",
    description="Create a new merchant that can receive payments from agents."
)
async def create_merchant(
    request: CreateMerchantRequest,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> MerchantResponse:
    """Register a new merchant with Sardis."""
    try:
        merchant, wallet = await wallet_service.register_merchant(
            name=request.name,
            description=request.description,
            category=request.category
        )
        return merchant_to_response(merchant)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "",
    response_model=list[MerchantResponse],
    summary="List merchants",
    description="List all registered merchants."
)
async def list_merchants(
    wallet_service: WalletService = Depends(get_wallet_service)
) -> list[MerchantResponse]:
    """List registered merchants."""
    merchants = wallet_service.list_merchants()
    return [merchant_to_response(m) for m in merchants]


@router.get(
    "/{merchant_id}",
    response_model=MerchantResponse,
    summary="Get merchant by ID",
    description="Retrieve details of a specific merchant."
)
async def get_merchant(
    merchant_id: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> MerchantResponse:
    """Get merchant details."""
    merchant = wallet_service.get_merchant(merchant_id)
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant {merchant_id} not found"
        )
    return merchant_to_response(merchant)


@router.get(
    "/{merchant_id}/wallet",
    response_model=WalletResponse,
    summary="Get merchant wallet",
    description="Retrieve the wallet details for a merchant."
)
async def get_merchant_wallet(
    merchant_id: str,
    wallet_service: WalletService = Depends(get_wallet_service)
) -> WalletResponse:
    """Get merchant's wallet details."""
    wallet = await wallet_service.get_merchant_wallet(merchant_id)
    if not wallet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Wallet not found for merchant {merchant_id}"
        )
    return wallet_to_response(wallet)


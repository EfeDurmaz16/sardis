"""Product catalog API routes."""

from typing import Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, Query

from sardis_core.api.schemas import ProductResponse

router = APIRouter(prefix="/catalog", tags=["catalog"])


# Mock product catalog - this would normally come from a database
MOCK_PRODUCTS = [
    {
        "product_id": "prod_001",
        "name": "Wireless Bluetooth Headphones",
        "description": "High-quality wireless headphones with noise cancellation",
        "price": "49.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_002",
        "name": "Mechanical Keyboard",
        "description": "RGB mechanical gaming keyboard with Cherry MX switches",
        "price": "89.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_003",
        "name": "USB-C Hub",
        "description": "7-in-1 USB-C hub with HDMI, USB-A, and SD card reader",
        "price": "29.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_004",
        "name": "Portable Charger",
        "description": "10000mAh portable power bank with fast charging",
        "price": "19.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_005",
        "name": "Laptop Stand",
        "description": "Adjustable aluminum laptop stand for ergonomic viewing",
        "price": "34.99",
        "currency": "USDC",
        "category": "office",
        "in_stock": True,
        "merchant_id": "mock_merchant_office"
    },
    {
        "product_id": "prod_006",
        "name": "Webcam HD",
        "description": "1080p HD webcam with built-in microphone",
        "price": "44.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_007",
        "name": "Notebook Set",
        "description": "Set of 3 premium ruled notebooks",
        "price": "12.99",
        "currency": "USDC",
        "category": "office",
        "in_stock": True,
        "merchant_id": "mock_merchant_office"
    },
    {
        "product_id": "prod_008",
        "name": "Desk Organizer",
        "description": "Wooden desk organizer with multiple compartments",
        "price": "24.99",
        "currency": "USDC",
        "category": "office",
        "in_stock": True,
        "merchant_id": "mock_merchant_office"
    },
    {
        "product_id": "prod_009",
        "name": "Mouse Pad XL",
        "description": "Extra large gaming mouse pad with stitched edges",
        "price": "14.99",
        "currency": "USDC",
        "category": "electronics",
        "in_stock": True,
        "merchant_id": "mock_merchant_electronics"
    },
    {
        "product_id": "prod_010",
        "name": "LED Desk Lamp",
        "description": "Adjustable LED desk lamp with touch control",
        "price": "27.99",
        "currency": "USDC",
        "category": "office",
        "in_stock": True,
        "merchant_id": "mock_merchant_office"
    }
]


@router.get(
    "/products",
    response_model=list[ProductResponse],
    summary="List products",
    description="Browse the product catalog with optional filters."
)
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    max_price: Optional[Decimal] = Query(None, description="Maximum price filter"),
    in_stock_only: bool = Query(True, description="Only show in-stock items")
) -> list[ProductResponse]:
    """List available products with optional filters."""
    products = MOCK_PRODUCTS.copy()
    
    # Apply filters
    if category:
        products = [p for p in products if p["category"].lower() == category.lower()]
    
    if max_price is not None:
        products = [p for p in products if Decimal(p["price"]) <= max_price]
    
    if in_stock_only:
        products = [p for p in products if p["in_stock"]]
    
    return [ProductResponse(**p) for p in products]


@router.get(
    "/products/{product_id}",
    response_model=ProductResponse,
    summary="Get product by ID",
    description="Get details of a specific product."
)
async def get_product(product_id: str) -> ProductResponse:
    """Get product details by ID."""
    for product in MOCK_PRODUCTS:
        if product["product_id"] == product_id:
            return ProductResponse(**product)
    
    from fastapi import HTTPException, status
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Product {product_id} not found"
    )


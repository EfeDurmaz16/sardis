"""Pydantic schemas for API request/response validation."""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, field_validator


# ========== Agent Schemas ==========

class CreateAgentRequest(BaseModel):
    """Request to register a new agent."""
    name: str = Field(..., min_length=1, max_length=100)
    owner_id: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    initial_balance: Decimal = Field(default=Decimal("0.00"), ge=0)
    limit_per_tx: Optional[Decimal] = Field(None, ge=0)
    limit_total: Optional[Decimal] = Field(None, ge=0)
    
    @field_validator('initial_balance', 'limit_per_tx', 'limit_total', mode='before')
    @classmethod
    def convert_to_decimal(cls, v):
        """Convert string values to Decimal."""
        if v is None or v == '':
            return None
        if isinstance(v, str):
            return Decimal(v)
        return v


class VirtualCardResponse(BaseModel):
    """Virtual card information."""
    card_id: str
    masked_number: str
    is_active: bool


class WalletResponse(BaseModel):
    """Wallet information response."""
    wallet_id: str
    agent_id: str
    balance: str
    currency: str
    limit_per_tx: str
    limit_total: str
    spent_total: str
    remaining_limit: str
    virtual_card: Optional[VirtualCardResponse] = None
    is_active: bool
    created_at: datetime


class AgentResponse(BaseModel):
    """Agent information response."""
    agent_id: str
    name: str
    owner_id: str
    description: Optional[str]
    wallet_id: Optional[str]
    is_active: bool
    created_at: datetime


class AgentWithWalletResponse(BaseModel):
    """Agent with full wallet information."""
    agent: AgentResponse
    wallet: WalletResponse


class AgentInstructionRequest(BaseModel):
    """Request to instruct an agent."""
    instruction: str = Field(..., min_length=1, max_length=1000)


class AgentInstructionResponse(BaseModel):
    """Response from agent instruction."""
    response: Optional[str] = None
    tool_call: Optional[dict] = None
    error: Optional[str] = None
    tx_id: Optional[str] = None


# ========== Merchant Schemas ==========

class CreateMerchantRequest(BaseModel):
    """Request to register a new merchant."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    category: Optional[str] = Field(None, max_length=50)


class MerchantResponse(BaseModel):
    """Merchant information response."""
    merchant_id: str
    name: str
    wallet_id: Optional[str]
    description: Optional[str]
    category: Optional[str]
    is_active: bool
    created_at: datetime


# ========== Payment Schemas ==========

class PaymentRequest(BaseModel):
    """Request to process a payment."""
    agent_id: str
    amount: Decimal = Field(..., gt=0)
    recipient_wallet_id: Optional[str] = None
    merchant_id: Optional[str] = None
    currency: str = Field(default="USDC")
    purpose: Optional[str] = Field(None, max_length=200)


class TransactionResponse(BaseModel):
    """Transaction information response."""
    tx_id: str
    from_wallet: str
    to_wallet: str
    amount: str
    fee: str
    total_cost: str
    currency: str
    purpose: Optional[str]
    status: str
    error_message: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime]


class PaymentResponse(BaseModel):
    """Payment result response."""
    success: bool
    transaction: Optional[TransactionResponse] = None
    error: Optional[str] = None


class EstimateResponse(BaseModel):
    """Payment estimate response."""
    amount: str
    fee: str
    total: str
    currency: str


# ========== Product Catalog Schemas ==========

class ProductResponse(BaseModel):
    """Product information."""
    product_id: str
    name: str
    description: str
    price: str
    currency: str
    category: str
    in_stock: bool
    merchant_id: str


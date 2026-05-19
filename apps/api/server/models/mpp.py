"""MPP API request and response models."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class CreateMPPSessionRequest(BaseModel):
    mandate_id: str | None = None
    wallet_id: str | None = None
    agent_id: str | None = None
    method: str = Field(default="tempo", description="Payment method: tempo, stripe_spt, bolt11")
    chain: str = Field(default="tempo", description="Target chain")
    currency: str = Field(default="USDC", description="Payment currency")
    spending_limit: Decimal = Field(..., gt=0, description="Maximum amount for this session")
    expires_in_seconds: int | None = Field(default=3600, description="Session TTL in seconds")
    metadata: dict | None = None


class MPPSessionResponse(BaseModel):
    session_id: str
    mandate_id: str | None
    wallet_id: str | None
    agent_id: str | None
    method: str
    chain: str
    currency: str
    spending_limit: str
    remaining: str
    total_spent: str
    payment_count: int
    status: str
    created_at: str
    closed_at: str | None
    expires_at: str | None
    next_steps: list[str] = []


class ExecutePaymentRequest(BaseModel):
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    merchant: str = Field(..., description="Merchant identifier or URL")
    destination: str | None = Field(None, description="Destination wallet address (0x...)")
    merchant_url: str | None = None
    memo: str | None = None
    metadata: dict | None = None


class ExecutePaymentResponse(BaseModel):
    payment_id: str
    session_id: str
    amount: str
    merchant: str
    status: str
    tx_hash: str | None
    chain: str
    remaining: str
    next_steps: list[str] = []


class PolicyEvaluateRequest(BaseModel):
    amount: Decimal = Field(..., gt=0)
    merchant: str
    payment_type: str = "mpp_tempo"
    currency: str = "USDC"
    network: str = "tempo"


class PolicyEvaluateResponse(BaseModel):
    allowed: bool
    reason: str
    checks_passed: int
    checks_total: int


class IssueCardRequest(BaseModel):
    amount: Decimal = Field(..., ge=5, le=1000, description="Card amount in USD ($5-$1,000)")
    currency: str = Field(default="USD", description="Card currency")
    session_id: str | None = Field(default=None, description="MPP session to charge against")


class IssueCardResponse(BaseModel):
    card_id: str
    card_number: str
    cvv: str
    expiry: str
    amount: str
    currency: str
    status: str
    card_type: str
    sandbox: bool = Field(default=False, description="True when card is simulated (non-live mode)")


def mpp_session_response_from_record(
    record: dict,
    next_steps: list[str] | None = None,
) -> MPPSessionResponse:
    return MPPSessionResponse(
        session_id=record["session_id"],
        mandate_id=record.get("mandate_id"),
        wallet_id=record.get("wallet_id"),
        agent_id=record.get("agent_id"),
        method=record["method"],
        chain=record["chain"],
        currency=record["currency"],
        spending_limit=str(record["spending_limit"]),
        remaining=str(record["remaining"]),
        total_spent=str(record["total_spent"]),
        payment_count=record["payment_count"],
        status=record["status"],
        created_at=str(record["created_at"]),
        closed_at=str(record["closed_at"]) if record.get("closed_at") else None,
        expires_at=str(record["expires_at"]) if record.get("expires_at") else None,
        next_steps=next_steps or [],
    )

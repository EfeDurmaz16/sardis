"""Hold (pre-authorization) models for Sardis SDK."""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import Field

from .base import SardisModel


class HoldStatus(str, Enum):
    """Hold status."""
    
    ACTIVE = "active"
    CAPTURED = "captured"
    VOIDED = "voided"
    EXPIRED = "expired"


class Hold(SardisModel):
    """A pre-authorization hold on funds."""
    
    hold_id: str = Field(alias="id")
    wallet_id: str
    merchant_id: Optional[str] = None
    amount: Decimal
    token: str = "USDC"
    status: HoldStatus
    purpose: Optional[str] = None
    expires_at: datetime
    captured_amount: Optional[Decimal] = None
    captured_at: Optional[datetime] = None
    voided_at: Optional[datetime] = None
    created_at: datetime


class CreateHoldRequest(SardisModel):
    """Request to create a hold."""
    
    wallet_id: str
    amount: Decimal
    token: str = "USDC"
    merchant_id: Optional[str] = None
    purpose: Optional[str] = None
    duration_hours: int = 24


class CaptureHoldRequest(SardisModel):
    """Request to capture a hold."""
    
    amount: Optional[Decimal] = None  # If None, capture full amount


class CreateHoldResponse(SardisModel):
    """Response from creating a hold."""
    
    hold_id: str
    status: HoldStatus
    expires_at: datetime


# Aliases
HoldCreate = CreateHoldRequest

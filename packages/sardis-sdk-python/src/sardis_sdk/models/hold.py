"""Hold (pre-authorization) models for Sardis SDK."""
from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import Field

from .base import SardisModel

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal


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
    merchant_id: str | None = None
    amount: Decimal
    token: str = "USDC"
    status: HoldStatus
    purpose: str | None = None
    expires_at: datetime
    captured_amount: Decimal | None = None
    captured_at: datetime | None = None
    voided_at: datetime | None = None
    created_at: datetime


class CreateHoldRequest(SardisModel):
    """Request to create a hold."""
    
    wallet_id: str
    amount: Decimal
    token: str = "USDC"
    merchant_id: str | None = None
    purpose: str | None = None
    duration_hours: int = 24


class CaptureHoldRequest(SardisModel):
    """Request to capture a hold."""
    
    amount: Decimal | None = None  # If None, capture full amount


class CreateHoldResponse(SardisModel):
    """Response from creating a hold."""
    
    hold_id: str
    status: HoldStatus
    expires_at: datetime


# Aliases
HoldCreate = CreateHoldRequest

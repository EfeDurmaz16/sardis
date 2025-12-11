"""API Key management endpoints."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from ..middleware import (
    APIKeyManager,
    APIKey,
    get_api_key_manager,
    require_api_key,
)

router = APIRouter(tags=["api-keys"])


# Request/Response Models

class CreateAPIKeyRequest(BaseModel):
    """Request to create a new API key."""
    name: str = Field(..., description="Human-readable name for the API key")
    scopes: List[str] = Field(
        default=["read", "write"],
        description="Permission scopes for the key"
    )
    rate_limit: int = Field(
        default=100,
        description="Requests per minute limit"
    )
    expires_in_days: Optional[int] = Field(
        default=None,
        description="Days until expiration (None = never expires)"
    )


class APIKeyResponse(BaseModel):
    """API key response (without the secret)."""
    key_id: str
    key_prefix: str
    name: str
    scopes: List[str]
    rate_limit: int
    is_active: bool
    expires_at: Optional[datetime]
    created_at: datetime
    last_used_at: Optional[datetime]


class CreateAPIKeyResponse(BaseModel):
    """Response when creating a new API key."""
    key: str  # Only returned once!
    key_id: str
    key_prefix: str
    name: str
    scopes: List[str]
    rate_limit: int
    expires_at: Optional[datetime]
    created_at: datetime
    
    class Config:
        json_schema_extra = {
            "example": {
                "key": "sk_live_abc123...",
                "key_id": "key_12345678",
                "key_prefix": "sk_live_abc1",
                "name": "Production API Key",
                "scopes": ["read", "write"],
                "rate_limit": 100,
                "expires_at": None,
                "created_at": "2025-01-01T00:00:00Z"
            }
        }


class ListAPIKeysResponse(BaseModel):
    """List of API keys."""
    keys: List[APIKeyResponse]
    total: int


# Routes

@router.post("", response_model=CreateAPIKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    request: CreateAPIKeyRequest,
    current_key: APIKey = Depends(require_api_key),
):
    """
    Create a new API key.
    
    **Important:** The `key` field in the response is only shown once.
    Store it securely - it cannot be retrieved later.
    
    Requires: Valid API key with 'admin' or 'api_keys:create' scope.
    """
    # Check for admin scope
    if "admin" not in current_key.scopes and "api_keys:create" not in current_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires 'admin' or 'api_keys:create' scope"
        )
    
    manager = get_api_key_manager()
    
    # Calculate expiration
    expires_at = None
    if request.expires_in_days:
        from datetime import timedelta
        expires_at = datetime.now(timezone.utc) + timedelta(days=request.expires_in_days)
    
    full_key, api_key = await manager.create_key(
        organization_id=current_key.organization_id,
        name=request.name,
        scopes=request.scopes,
        rate_limit=request.rate_limit,
        expires_at=expires_at,
    )
    
    return CreateAPIKeyResponse(
        key=full_key,
        key_id=api_key.key_id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
    )


@router.get("", response_model=ListAPIKeysResponse)
async def list_api_keys(
    current_key: APIKey = Depends(require_api_key),
):
    """
    List all API keys for the organization.
    
    Note: The actual key secrets are never returned.
    """
    manager = get_api_key_manager()
    keys = await manager.list_keys(current_key.organization_id)
    
    return ListAPIKeysResponse(
        keys=[
            APIKeyResponse(
                key_id=k.key_id,
                key_prefix=k.key_prefix,
                name=k.name,
                scopes=k.scopes,
                rate_limit=k.rate_limit,
                is_active=k.is_active,
                expires_at=k.expires_at,
                created_at=k.created_at,
                last_used_at=k.last_used_at,
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.get("/{key_id}", response_model=APIKeyResponse)
async def get_api_key_by_id(
    key_id: str,
    current_key: APIKey = Depends(require_api_key),
):
    """Get details of a specific API key."""
    manager = get_api_key_manager()
    api_key = await manager.get_key(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check organization access
    if api_key.organization_id != current_key.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    return APIKeyResponse(
        key_id=api_key.key_id,
        key_prefix=api_key.key_prefix,
        name=api_key.name,
        scopes=api_key.scopes,
        rate_limit=api_key.rate_limit,
        is_active=api_key.is_active,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: str,
    current_key: APIKey = Depends(require_api_key),
):
    """
    Revoke (deactivate) an API key.
    
    This action cannot be undone. The key will immediately stop working.
    """
    manager = get_api_key_manager()
    api_key = await manager.get_key(key_id)
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found"
        )
    
    # Check organization access
    if api_key.organization_id != current_key.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Check for admin scope
    if "admin" not in current_key.scopes and "api_keys:delete" not in current_key.scopes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires 'admin' or 'api_keys:delete' scope"
        )
    
    success = await manager.revoke_key(key_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to revoke key"
        )
    
    return None


@router.get("/me/info")
async def get_current_key_info(
    current_key: APIKey = Depends(require_api_key),
):
    """Get information about the currently used API key."""
    return APIKeyResponse(
        key_id=current_key.key_id,
        key_prefix=current_key.key_prefix,
        name=current_key.name,
        scopes=current_key.scopes,
        rate_limit=current_key.rate_limit,
        is_active=current_key.is_active,
        expires_at=current_key.expires_at,
        created_at=current_key.created_at,
        last_used_at=current_key.last_used_at,
    )



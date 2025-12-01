
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import secrets

from sardis_core.database.session import get_db
from sardis_core.database.models import DBApiKey
from sardis_core.auth.security import hash_key

router = APIRouter(prefix="/auth", tags=["Authentication"])

class ApiKeyCreate(BaseModel):
    name: str
    owner_id: str

class ApiKeyResponse(BaseModel):
    key_id: str
    api_key: str  # Only shown once
    name: str
    owner_id: str

from sardis_core.api.auth import get_current_user

@router.post("/keys", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    key_data: ApiKeyCreate,
    db: AsyncSession = Depends(get_db),
    current_user: str = Depends(get_current_user)
):
    """Generate a new API key."""
    # Generate a random key ID and secret
    key_id = f"key_{secrets.token_hex(8)}"
    key_secret = secrets.token_urlsafe(32)
    
    # The full key provided to the user
    raw_key = f"sk_{key_id}_{key_secret}"
    
    # We hash only the secret part to avoid bcrypt 72 byte limit
    key_hash = hash_key(key_secret)
    
    db_key = DBApiKey(
        key_id=key_id,
        key_hash=key_hash,
        owner_id=key_data.owner_id,
        name=key_data.name
    )
    
    db.add(db_key)
    await db.commit()
    
    return ApiKeyResponse(
        key_id=key_id,
        api_key=raw_key,
        name=key_data.name,
        owner_id=key_data.owner_id
    )

from fastapi.security import OAuth2PasswordRequestForm
from sardis_core.auth.security import create_access_token
from sardis_core.config import settings

@router.post("/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Login to get access token."""
    # Simple admin check
    if form_data.username == "admin" and form_data.password == settings.admin_password:
        access_token = create_access_token(data={"sub": "admin"})
        return {"access_token": access_token, "token_type": "bearer"}
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

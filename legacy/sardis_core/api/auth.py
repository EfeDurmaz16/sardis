
from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from sardis_core.database.session import get_db
from sardis_core.database.models import DBApiKey
from sardis_core.auth.security import verify_key

async def get_api_key(
    x_api_key: str = Header(..., description="API Key (sk_keyid_secret)"),
    db: AsyncSession = Depends(get_db)
) -> DBApiKey:
    """Validate API Key and return the key object."""
    # Expected format: sk_key_{hex}_{secret}
    parts = x_api_key.split("_")
    
    # We expect at least 4 parts: sk, key, hex, secret
    if len(parts) < 4 or parts[0] != "sk" or parts[1] != "key":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key format",
        )
    
    # Reconstruct key_id
    key_id = f"{parts[1]}_{parts[2]}"
    
    # Lookup in DB
    result = await db.execute(select(DBApiKey).where(DBApiKey.key_id == key_id))
    api_key = result.scalar_one_or_none()
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
        
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="API Key is inactive",
        )
        
    # Verify hash (verify the secret part)
    # parts[3] is the secret
    if not verify_key(parts[3], api_key.key_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API Key",
        )
        
    return api_key

from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sardis_core.config import settings
from sardis_core.auth.security import ALGORITHM

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.api_prefix}/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)):
    """Validate JWT and return user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    return username

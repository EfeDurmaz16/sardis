"""Authentication endpoints."""
from __future__ import annotations

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, status, Form
from pydantic import BaseModel

router = APIRouter()


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
async def login(
    username: str = Form(...),
    password: str = Form(...),
):
    """Login with username and password."""
    admin_password = os.getenv("SARDIS_ADMIN_PASSWORD", "admin")
    
    if username == "admin" and password == admin_password:
        # Simple token for dev - in production use proper JWT
        token = f"sardis_dev_token_{datetime.utcnow().timestamp()}"
        return TokenResponse(access_token=token)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid username or password",
    )

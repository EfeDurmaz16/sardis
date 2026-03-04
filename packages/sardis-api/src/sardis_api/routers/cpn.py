"""Circle Payments Network webhook + introspection endpoints."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sardis_api.authz import Principal, require_admin_principal
from sardis_api.webhook_replay import run_with_replay_protection

router = APIRouter(prefix="/cpn", tags=["cpn"])
public_router = APIRouter(tags=["cpn-webhooks"])


@dataclass
class CPNDependencies:
    treasury_repo: Any
    webhook_secret: str = ""
    environment: str = "dev"


def get_deps() -> CPNDependencies:
    raise NotImplementedError("Dependency override required")


def _extract_signature(raw_signature: str) -> str:
    value = (raw_signature or "").strip()
    if not value:
        return ""
    if value.startswith("sha256="):
        return value.split("=", 1)[1].strip()
    return value


def _verify_signature(secret: str, body: bytes, signature_header: str) -> bool:
    provided = _extract_signature(signature_header)
    if not provided:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(provided, expected)


@router.get("/security-policy")
async def cpn_security_policy(
    deps: CPNDependencies = Depends(get_deps),
    _: Principal = Depends(require_admin_principal),
):
    env = (deps.environment or os.getenv("SARDIS_ENVIRONMENT", "dev")).strip().lower()
    return {
        "provider": "circle_cpn",
        "signature_required": env in {"prod", "production"},
        "replay_protection_ttl_seconds": 7 * 24 * 60 * 60,
        "secret_configured": bool(deps.webhook_secret),
    }


@public_router.post("/webhooks/cpn", status_code=status.HTTP_200_OK)
async def cpn_webhook(
    request: Request,
    deps: CPNDependencies = Depends(get_deps),
):
    body = await request.body()
    env = (deps.environment or os.getenv("SARDIS_ENVIRONMENT", "dev")).strip().lower()

    signature = (
        request.headers.get("x-circle-signature", "")
        or request.headers.get("circle-signature", "")
        or request.headers.get("x-signature", "")
    )

    if env in {"prod", "production"} and not deps.webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="cpn_webhook_secret_required_in_production",
        )

    if deps.webhook_secret and not _verify_signature(deps.webhook_secret, body, signature):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_webhook_signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json") from exc

    event_id = str(
        payload.get("event_id")
        or payload.get("eventId")
        or payload.get("id")
        or payload.get("payment_id")
        or payload.get("paymentId")
        or hashlib.sha256(body).hexdigest()
    )
    event_type = str(payload.get("type") or payload.get("event_type") or "unknown")

    async def _process() -> dict[str, str]:
        if deps.treasury_repo is not None:
            await deps.treasury_repo.record_treasury_webhook_event(
                provider="circle_cpn",
                event_id=event_id,
                body=body,
                status_value="processed",
                metadata={
                    "event_type": event_type,
                    "payment_id": str(payload.get("payment_id") or payload.get("paymentId") or ""),
                    "status": str(payload.get("status") or ""),
                },
            )
        return {"status": "received"}

    return await run_with_replay_protection(
        request=request,
        provider="circle_cpn",
        event_id=event_id,
        body=body,
        ttl_seconds=7 * 24 * 60 * 60,
        response_on_duplicate={"status": "received"},
        fn=_process,
    )

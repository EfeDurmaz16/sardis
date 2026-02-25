"""Webhook handlers for partner card issuers (Rain / Bridge)."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status

from sardis_api.canonical_state_machine import normalize_partner_card_event
from sardis_api.webhook_replay import run_with_replay_protection

router = APIRouter(tags=["partner-card-webhooks"])


@dataclass
class PartnerCardWebhookDeps:
    card_repo: Any
    wallet_repo: Any
    agent_repo: Any
    canonical_repo: Any = None
    treasury_repo: Any = None
    rain_webhook_secret: str = ""
    bridge_webhook_secret: str = ""
    environment: str = "dev"


def get_deps() -> PartnerCardWebhookDeps:
    raise NotImplementedError("Dependency override required")


def _compute_hmac(secret: str, body: bytes, *, timestamp: Optional[str] = None) -> tuple[str, str]:
    mac_body = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    if timestamp:
        signed_payload = f"{timestamp}.{body.decode('utf-8')}".encode("utf-8")
        mac_timestamped = hmac.new(secret.encode(), signed_payload, hashlib.sha256).hexdigest()
    else:
        mac_timestamped = mac_body
    return mac_body, mac_timestamped


def _extract_sig_from_header(raw_signature: str) -> str:
    value = (raw_signature or "").strip()
    if not value:
        return ""
    # Support formats: "sha256=...", "t=...,v1=...", plain hex
    if "," in value and "v1=" in value:
        for part in value.split(","):
            piece = part.strip()
            if piece.startswith("v1="):
                return piece.split("=", 1)[1].strip()
    if value.startswith("sha256="):
        return value.split("=", 1)[1].strip()
    return value


def _verify_signature(
    *,
    secret: str,
    signature_header: str,
    body: bytes,
    timestamp: Optional[str] = None,
) -> bool:
    provided = _extract_sig_from_header(signature_header)
    if not provided:
        return False
    body_sig, timestamp_sig = _compute_hmac(secret, body, timestamp=timestamp)
    return hmac.compare_digest(provided, body_sig) or hmac.compare_digest(provided, timestamp_sig)


def _normalize_event_type(value: Any) -> str:
    return str(value or "").strip().lower()


def _is_transaction_event(event_type: str) -> bool:
    return "transaction" in event_type or "authorization" in event_type


def _extract_event_id(payload: dict[str, Any], body: bytes) -> str:
    value = (
        payload.get("event_id")
        or payload.get("eventId")
        or payload.get("id")
        or payload.get("token")
        or payload.get("event_token")
    )
    if value:
        return str(value)
    return hashlib.sha256(body).hexdigest()


def _extract_card_token(payload: dict[str, Any]) -> str:
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    return str(
        payload.get("card_token")
        or payload.get("cardToken")
        or data.get("card_token")
        or data.get("card")
        or data.get("card_id")
        or ""
    )


def _normalize_card_status(value: Any) -> str:
    s = str(value or "").strip().lower()
    if s in {"open", "active", "enabled"}:
        return "active"
    if s in {"frozen", "disabled", "locked", "paused"}:
        return "frozen"
    if s in {"cancelled", "canceled", "closed", "terminated"}:
        return "cancelled"
    if s in {"pending", "created", "issued", "inactive"}:
        return "pending"
    if "freeze" in s:
        return "frozen"
    if "cancel" in s or "close" in s:
        return "cancelled"
    if "active" in s or "open" in s:
        return "active"
    return s or "pending"


async def _resolve_org_id(deps: PartnerCardWebhookDeps, card: dict[str, Any] | None) -> str:
    if not card:
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
    wallet_id = str(card.get("wallet_id") or "")
    if not wallet_id:
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
    if deps.wallet_repo is None or deps.agent_repo is None:
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent or not getattr(agent, "owner_id", None):
        return os.getenv("SARDIS_DEFAULT_ORG_ID", "org_demo")
    return str(agent.owner_id)


async def _handle_partner_webhook(
    *,
    provider: str,
    request: Request,
    deps: PartnerCardWebhookDeps,
    secret: str,
    signature_header: str,
    timestamp_header: Optional[str] = None,
) -> dict[str, str]:
    body = await request.body()

    env = (deps.environment or os.getenv("SARDIS_ENVIRONMENT", "dev")).strip().lower()
    if not secret and env in {"prod", "production"}:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{provider}_webhook_secret_required_in_production",
        )

    if secret:
        if not _verify_signature(
            secret=secret,
            signature_header=signature_header,
            body=body,
            timestamp=timestamp_header,
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="invalid_webhook_signature",
            )

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_json") from exc

    event_id = _extract_event_id(payload, body)
    event_type = _normalize_event_type(payload.get("event_type") or payload.get("type"))

    async def _process() -> dict[str, str]:
        if deps.treasury_repo is not None:
            await deps.treasury_repo.record_treasury_webhook_event(
                provider=provider,
                event_id=event_id,
                body=body,
                status_value="processed",
                metadata={"event_type": event_type},
            )

        card_token = _extract_card_token(payload)
        card = None
        if card_token and deps.card_repo is not None:
            card = await deps.card_repo.get_by_provider_card_id(card_token)
            if not card:
                card = await deps.card_repo.get_by_card_id(card_token)

        data = payload.get("data") if isinstance(payload.get("data"), dict) else payload

        if card and not _is_transaction_event(event_type):
            card_status = data.get("status") or payload.get("status")
            if card_status:
                await deps.card_repo.update_status(
                    str(card.get("card_id") or card_token),
                    _normalize_card_status(card_status),
                )

        if card and _is_transaction_event(event_type):
            amount_value = Decimal(str(data.get("amount", 0) or 0))
            amount_float = float(amount_value)
            mcc_code = str(data.get("mcc") or (data.get("merchant") or {}).get("mcc") or "0000")
            settled_at = None
            if data.get("settled_at"):
                try:
                    settled_at = datetime.fromisoformat(str(data.get("settled_at")).replace("Z", "+00:00"))
                except Exception:
                    settled_at = datetime.now(timezone.utc)
            status_value = "pending"
            raw_status = str(data.get("status") or "").lower()
            if "declined" in event_type or raw_status in {"declined", "denied"}:
                status_value = "declined"
            elif "settled" in event_type or raw_status in {"settled", "completed"}:
                status_value = "settled"
                if settled_at is None:
                    settled_at = datetime.now(timezone.utc)
            elif "authorized" in event_type or raw_status in {"approved", "authorized"}:
                status_value = "approved"

            tx_id = str(data.get("transaction_id") or data.get("token") or payload.get("id") or event_id)
            await deps.card_repo.record_transaction(
                card_id=str(card.get("card_id") or card_token),
                transaction_id=tx_id,
                provider_tx_id=tx_id,
                amount=amount_float,
                currency=str(data.get("currency") or "USD"),
                merchant_name=str((data.get("merchant") or {}).get("name") or data.get("merchant_name") or "Unknown"),
                merchant_category=mcc_code,
                merchant_id=str((data.get("merchant") or {}).get("id") or data.get("merchant_id") or ""),
                decline_reason=str(data.get("decline_reason") or "") or None,
                status=status_value,
                settled_at=settled_at,
            )

            if deps.canonical_repo is not None:
                org_id = await _resolve_org_id(deps, card)
                normalized = normalize_partner_card_event(
                    organization_id=org_id,
                    provider=provider,
                    payload=payload,
                    event_type=event_type,
                    transaction_reference=tx_id,
                )
                await deps.canonical_repo.ingest_event(
                    normalized,
                    drift_tolerance_minor=int(os.getenv("SARDIS_CANONICAL_DRIFT_TOLERANCE_MINOR", "1000")),
                )

        return {"status": "received"}

    return await run_with_replay_protection(
        request=request,
        provider=provider,
        event_id=event_id,
        body=body,
        ttl_seconds=7 * 24 * 60 * 60,
        response_on_duplicate={"status": "received"},
        fn=_process,
    )


@router.post("/webhooks/cards/rain", status_code=status.HTTP_200_OK)
async def receive_rain_webhook(
    request: Request,
    deps: PartnerCardWebhookDeps = Depends(get_deps),
):
    signature = request.headers.get("x-rain-signature", "") or request.headers.get("rain-signature", "")
    timestamp = request.headers.get("x-rain-timestamp")
    return await _handle_partner_webhook(
        provider="rain",
        request=request,
        deps=deps,
        secret=deps.rain_webhook_secret,
        signature_header=signature,
        timestamp_header=timestamp,
    )


@router.post("/webhooks/cards/bridge", status_code=status.HTTP_200_OK)
async def receive_bridge_webhook(
    request: Request,
    deps: PartnerCardWebhookDeps = Depends(get_deps),
):
    signature = request.headers.get("x-bridge-signature", "") or request.headers.get("bridge-signature", "")
    timestamp = request.headers.get("x-bridge-timestamp")
    return await _handle_partner_webhook(
        provider="bridge_cards",
        request=request,
        deps=deps,
        secret=deps.bridge_webhook_secret,
        signature_header=signature,
        timestamp_header=timestamp,
    )

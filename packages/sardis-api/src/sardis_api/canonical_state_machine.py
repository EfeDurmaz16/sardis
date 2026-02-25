"""Canonical ledger state normalization across fiat and stablecoin rails."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional


CANONICAL_STATE_RANK = {
    "created": 10,
    "authorized": 20,
    "processing": 30,
    "settled": 40,
    "returned": 50,
    "failed": 50,
}


@dataclass(frozen=True)
class CanonicalEvent:
    organization_id: str
    provider: str
    provider_event_id: Optional[str]
    provider_event_type: str
    canonical_event_type: str
    rail: str
    external_reference: str
    canonical_state: Optional[str] = None
    direction: Optional[str] = None
    amount_minor: Optional[int] = None
    currency: Optional[str] = None
    return_code: Optional[str] = None
    event_ts: Optional[datetime] = None
    metadata: Optional[dict[str, Any]] = None
    raw_payload: Optional[dict[str, Any]] = None


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _parse_ts(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, (int, float)):
        raw = float(value)
        if raw > 1e12:
            raw = raw / 1000.0
        return datetime.fromtimestamp(raw, tz=timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(s)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            return None
    return None


def _extract_return_code(payload: dict[str, Any]) -> Optional[str]:
    direct = payload.get("return_reason_code")
    if direct:
        return str(direct)
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("return_reason_code")
        if nested:
            return str(nested)
        method_attr = data.get("method_attributes")
        if isinstance(method_attr, dict) and method_attr.get("return_reason_code"):
            return str(method_attr["return_reason_code"])
    method_attr = payload.get("method_attributes")
    if isinstance(method_attr, dict) and method_attr.get("return_reason_code"):
        return str(method_attr["return_reason_code"])
    return None


def apply_state_transition(current_state: Optional[str], incoming_state: Optional[str]) -> tuple[Optional[str], bool]:
    """
    Return (next_state, out_of_order).

    Out-of-order is raised when an older/lower-priority state arrives after the journey
    already advanced to a later state.
    """
    if not incoming_state:
        return current_state, False
    if not current_state:
        return incoming_state, False
    current_rank = CANONICAL_STATE_RANK.get(current_state, 0)
    incoming_rank = CANONICAL_STATE_RANK.get(incoming_state, 0)
    if incoming_rank < current_rank:
        return current_state, True
    return incoming_state, False


def normalize_lithic_ach_event(
    *,
    organization_id: str,
    payload: dict[str, Any],
    event_type: str,
    payment_token: str,
) -> CanonicalEvent:
    et = (event_type or "").strip().upper()
    mapping = {
        "ACH_ORIGINATION_INITIATED": ("fiat.ach.initiated", "created"),
        "ACH_ORIGINATION_REVIEWED": ("fiat.ach.reviewed", "authorized"),
        "ACH_ORIGINATION_PROCESSED": ("fiat.ach.processed", "processing"),
        "ACH_ORIGINATION_SETTLED": ("fiat.ach.settled", "settled"),
        "ACH_ORIGINATION_RELEASED": ("fiat.ach.released", "settled"),
        "ACH_RETURN_INITIATED": ("fiat.ach.return_initiated", "returned"),
        "ACH_RETURN_PROCESSED": ("fiat.ach.return_processed", "returned"),
        "ACH_RECEIPT_PROCESSED": ("fiat.ach.receipt_processed", "processing"),
        "ACH_RECEIPT_SETTLED": ("fiat.ach.receipt_settled", "settled"),
    }
    canonical_event_type, canonical_state = mapping.get(et, ("fiat.ach.unknown", None))
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    event_ts = (
        _parse_ts(payload.get("created"))
        or _parse_ts(data.get("created"))
        or datetime.now(timezone.utc)
    )
    amount_minor = (
        _safe_int(payload.get("amount"))
        or _safe_int(data.get("amount"))
        or _safe_int(data.get("pending_amount"))
    )
    return CanonicalEvent(
        organization_id=organization_id,
        provider="lithic",
        provider_event_id=str(payload.get("event_token") or payload.get("token") or "") or None,
        provider_event_type=et or "UNKNOWN",
        canonical_event_type=canonical_event_type,
        rail="fiat_ach",
        external_reference=payment_token,
        canonical_state=canonical_state,
        direction=str(data.get("direction", "")).lower() or None,
        amount_minor=amount_minor,
        currency=str(data.get("currency", payload.get("currency", "USD"))),
        return_code=_extract_return_code(payload),
        event_ts=event_ts,
        metadata={
            "source": "lithic_webhook",
            "status": data.get("status"),
            "result": data.get("result"),
        },
        raw_payload=payload,
    )


def normalize_lithic_card_event(
    *,
    organization_id: str,
    payload: dict[str, Any],
    event_type: str,
    transaction_reference: str,
) -> CanonicalEvent:
    et = (event_type or "").strip().lower()
    data = payload.get("data") if isinstance(payload.get("data"), dict) else payload
    status = str(data.get("status") or payload.get("status") or "").lower()
    canonical_event_type = "fiat.card.transaction_observed"
    canonical_state: Optional[str] = "processing"
    if "declined" in et or status in {"declined", "denied"}:
        canonical_event_type = "fiat.card.declined"
        canonical_state = "failed"
    elif "settled" in et or status in {"settled", "completed"}:
        canonical_event_type = "fiat.card.settled"
        canonical_state = "settled"
    elif "authorized" in et or status in {"authorized", "approved"}:
        canonical_event_type = "fiat.card.authorized"
        canonical_state = "authorized"

    amount_minor = _safe_int(data.get("amount"))
    event_ts = (
        _parse_ts(data.get("created"))
        or _parse_ts(data.get("settled_at"))
        or _parse_ts(payload.get("created"))
        or datetime.now(timezone.utc)
    )
    provider_event_id = str(payload.get("event_token") or payload.get("token") or "") or None
    return CanonicalEvent(
        organization_id=organization_id,
        provider="lithic",
        provider_event_id=provider_event_id,
        provider_event_type=et or "unknown",
        canonical_event_type=canonical_event_type,
        rail="fiat_card",
        external_reference=transaction_reference,
        canonical_state=canonical_state,
        direction="debit",
        amount_minor=amount_minor,
        currency=str(data.get("currency", "USD")),
        event_ts=event_ts,
        metadata={
            "card_token": payload.get("card_token") or data.get("card_token"),
            "merchant": (data.get("merchant") or {}).get("descriptor") if isinstance(data.get("merchant"), dict) else None,
            "decline_reason": data.get("decline_reason") or data.get("reason"),
        },
        raw_payload=payload,
    )


def normalize_stablecoin_event(
    *,
    organization_id: str,
    rail: str,
    reference: str,
    provider_event_id: str,
    provider_event_type: str,
    canonical_event_type: str,
    canonical_state: Optional[str],
    amount_minor: Optional[int],
    currency: str,
    metadata: Optional[dict[str, Any]] = None,
    raw_payload: Optional[dict[str, Any]] = None,
    event_ts: Optional[datetime] = None,
) -> CanonicalEvent:
    return CanonicalEvent(
        organization_id=organization_id,
        provider="onchain",
        provider_event_id=provider_event_id or None,
        provider_event_type=provider_event_type,
        canonical_event_type=canonical_event_type,
        rail=rail,
        external_reference=reference,
        canonical_state=canonical_state,
        direction="debit",
        amount_minor=amount_minor,
        currency=currency,
        event_ts=event_ts or datetime.now(timezone.utc),
        metadata=metadata or {},
        raw_payload=raw_payload or {},
    )


def normalize_stripe_issuing_funding_event(
    *,
    organization_id: str,
    payload: dict[str, Any],
    transfer_id: str,
    connected_account_id: Optional[str] = None,
) -> CanonicalEvent:
    """
    Normalize Stripe Issuing funding events into canonical journey records.

    Rail semantics:
    - rail: fiat_card_funding
    - external_reference: topup/transfer id
    """
    raw_status = str(payload.get("status") or "").strip().lower()
    status_map = {
        "posted": ("fiat.card_funding.posted", "settled"),
        "succeeded": ("fiat.card_funding.posted", "settled"),
        "processing": ("fiat.card_funding.processing", "processing"),
        "pending": ("fiat.card_funding.pending", "processing"),
        "failed": ("fiat.card_funding.failed", "failed"),
        "canceled": ("fiat.card_funding.canceled", "failed"),
        "cancelled": ("fiat.card_funding.canceled", "failed"),
        "returned": ("fiat.card_funding.returned", "returned"),
    }
    canonical_event_type, canonical_state = status_map.get(
        raw_status,
        ("fiat.card_funding.observed", "processing"),
    )
    amount_minor = _safe_int(payload.get("amount_minor"))
    event_ts = _parse_ts(payload.get("created_at")) or datetime.now(timezone.utc)
    return CanonicalEvent(
        organization_id=organization_id,
        provider="stripe",
        provider_event_id=str(transfer_id) or None,
        provider_event_type=raw_status or "unknown",
        canonical_event_type=canonical_event_type,
        rail="fiat_card_funding",
        external_reference=str(transfer_id),
        canonical_state=canonical_state,
        direction="credit",
        amount_minor=amount_minor,
        currency=str(payload.get("currency") or "USD").upper(),
        event_ts=event_ts,
        metadata={
            "source": "stripe_funding_topup",
            "connected_account_id": connected_account_id,
            "description": payload.get("description"),
        },
        raw_payload=payload,
    )

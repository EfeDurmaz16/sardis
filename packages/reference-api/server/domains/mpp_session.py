"""MPP session state and budget transitions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from server.models.mpp import CreateMPPSessionRequest


class MPPSessionInactiveError(ValueError):
    pass


class MPPSessionExpiredError(ValueError):
    pass


class MPPBudgetExceededError(ValueError):
    pass


@dataclass(frozen=True)
class MPPBudgetTransition:
    remaining: Decimal
    total_spent: Decimal
    payment_count: int
    status: str


@dataclass(frozen=True)
class MPPNewSession:
    record: dict
    expires_at_dt: datetime | None


def parse_session_expiry(expires_at) -> datetime | None:
    if not expires_at:
        return None
    try:
        if isinstance(expires_at, datetime):
            expiry = expires_at
        elif isinstance(expires_at, str):
            expiry = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
        else:
            expiry = datetime.fromisoformat(str(expires_at).replace(" ", "T").replace("Z", "+00:00"))
    except Exception:
        return None
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=UTC)
    return expiry


def create_session_record_payload(
    *,
    request: CreateMPPSessionRequest,
    session_id: str,
    organization_id: str,
    now: datetime,
) -> MPPNewSession:
    expires_at_dt = None
    expires_at = None
    if request.expires_in_seconds:
        expires_at_dt = now + timedelta(seconds=request.expires_in_seconds)
        expires_at = expires_at_dt.isoformat()

    return MPPNewSession(
        record={
            "session_id": session_id,
            "org_id": organization_id,
            "mandate_id": request.mandate_id,
            "wallet_id": request.wallet_id,
            "agent_id": request.agent_id,
            "method": request.method,
            "chain": request.chain,
            "currency": request.currency,
            "spending_limit": request.spending_limit,
            "remaining": request.spending_limit,
            "total_spent": Decimal("0"),
            "payment_count": 0,
            "status": "active",
            "created_at": now,
            "closed_at": None,
            "expires_at": expires_at,
        },
        expires_at_dt=expires_at_dt,
    )


def ensure_session_can_execute(session: dict, now: datetime | None = None) -> None:
    if session["status"] != "active":
        raise MPPSessionInactiveError(f"Session is {session['status']}, cannot execute")

    expiry = parse_session_expiry(session.get("expires_at"))
    if expiry and (now or datetime.now(UTC)) > expiry:
        raise MPPSessionExpiredError("Session has expired")


def apply_payment_budget(session: dict, amount: Decimal) -> MPPBudgetTransition:
    remaining = Decimal(str(session["remaining"]))
    if amount > remaining:
        raise MPPBudgetExceededError(
            f"Amount {amount} exceeds remaining session budget {remaining}"
        )

    new_remaining = remaining - amount
    new_total = Decimal(str(session["total_spent"])) + amount
    new_count = int(session["payment_count"]) + 1
    new_status = "exhausted" if new_remaining <= Decimal("0") else "active"
    return MPPBudgetTransition(
        remaining=new_remaining,
        total_spent=new_total,
        payment_count=new_count,
        status=new_status,
    )


def ensure_card_budget(session: dict, amount: Decimal) -> None:
    if session["status"] != "active":
        raise MPPSessionInactiveError(f"Session is {session['status']}")
    remaining = Decimal(str(session["remaining"]))
    if amount > remaining:
        raise MPPBudgetExceededError(
            f"Card amount {amount} exceeds remaining session budget {remaining}"
        )

"""Enterprise SLA profile and support ticket endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal

router = APIRouter(prefix="/api/v2/enterprise/support", tags=["enterprise-support"])


@dataclass
class EnterpriseSupportDependencies:
    support_repo: Any


def get_deps() -> EnterpriseSupportDependencies:
    raise NotImplementedError("Dependency override required")


class SupportProfileResponse(BaseModel):
    organization_id: str
    plan: Literal["free", "pro", "enterprise"]
    first_response_sla_minutes: int
    resolution_sla_hours: int
    channels: list[str]
    pager: bool


class CreateSupportTicketRequest(BaseModel):
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=4000)
    priority: Literal["low", "medium", "high", "urgent"] = "medium"
    category: Literal["payments", "compliance", "infrastructure", "cards", "other"] = "other"
    metadata: dict[str, Any] = Field(default_factory=dict)


class ResolveSupportTicketRequest(BaseModel):
    resolution_note: Optional[str] = Field(default=None, max_length=1000)


class SupportTicketResponse(BaseModel):
    id: str
    organization_id: str
    requester_id: str
    requester_kind: str
    subject: str
    description: str
    priority: str
    category: str
    status: str
    first_response_due_at: str
    resolution_due_at: str
    acknowledged_at: Optional[str] = None
    resolved_at: Optional[str] = None
    response_sla_breached: bool
    resolution_sla_breached: bool
    metadata: dict[str, Any]
    created_at: str
    updated_at: str


def _as_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
    return str(value)


def _to_utc_datetime(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    try:
        parsed = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _ticket_response(row: dict[str, Any]) -> SupportTicketResponse:
    now = datetime.now(timezone.utc)
    response_due = _to_utc_datetime(row.get("first_response_due_at"))
    resolution_due = _to_utc_datetime(row.get("resolution_due_at"))
    acknowledged = _to_utc_datetime(row.get("acknowledged_at"))
    resolved = _to_utc_datetime(row.get("resolved_at"))
    response_sla_breached = (
        response_due is not None
        and acknowledged is None
        and resolved is None
        and now > response_due
    )
    resolution_sla_breached = (
        resolution_due is not None
        and resolved is None
        and now > resolution_due
    )
    return SupportTicketResponse(
        id=str(row.get("id")),
        organization_id=str(row.get("organization_id")),
        requester_id=str(row.get("requester_id")),
        requester_kind=str(row.get("requester_kind")),
        subject=str(row.get("subject")),
        description=str(row.get("description")),
        priority=str(row.get("priority")),
        category=str(row.get("category")),
        status=str(row.get("status")),
        first_response_due_at=_as_iso(response_due) or "",
        resolution_due_at=_as_iso(resolution_due) or "",
        acknowledged_at=_as_iso(acknowledged),
        resolved_at=_as_iso(resolved),
        response_sla_breached=response_sla_breached,
        resolution_sla_breached=resolution_sla_breached,
        metadata=dict(row.get("metadata") or {}),
        created_at=_as_iso(row.get("created_at")) or "",
        updated_at=_as_iso(row.get("updated_at")) or "",
    )


def _assert_support_write(principal: Principal) -> None:
    if principal.is_admin:
        return
    scopes = {scope.strip().lower() for scope in principal.scopes}
    if "support:write" in scopes or "*" in scopes:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="support_write_scope_required",
    )


@router.get("/profile", response_model=SupportProfileResponse)
async def get_support_profile(
    deps: EnterpriseSupportDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    profile = deps.support_repo.get_support_profile(principal.organization_id)
    return SupportProfileResponse(**profile)


@router.get("/tickets", response_model=list[SupportTicketResponse])
async def list_support_tickets(
    status_filter: Optional[Literal["open", "acknowledged", "resolved", "closed"]] = Query(default=None),
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    deps: EnterpriseSupportDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    rows = await deps.support_repo.list_tickets(
        organization_id=principal.organization_id,
        status=status_filter,
        priority=priority,
        limit=limit,
        offset=offset,
    )
    return [_ticket_response(row) for row in rows]


@router.post("/tickets", response_model=SupportTicketResponse, status_code=status.HTTP_201_CREATED)
async def create_support_ticket(
    request: CreateSupportTicketRequest,
    deps: EnterpriseSupportDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    requester_id = principal.user.email if principal.kind == "jwt" and principal.user else principal.organization_id
    row = await deps.support_repo.create_ticket(
        organization_id=principal.organization_id,
        requester_id=requester_id,
        requester_kind=principal.kind,
        subject=request.subject,
        description=request.description,
        priority=request.priority,
        category=request.category,
        metadata=request.metadata,
    )
    return _ticket_response(row)


@router.post("/tickets/{ticket_id}/acknowledge", response_model=SupportTicketResponse)
async def acknowledge_support_ticket(
    ticket_id: str,
    deps: EnterpriseSupportDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    _assert_support_write(principal)
    actor = principal.user.email if principal.kind == "jwt" and principal.user else principal.organization_id
    row = await deps.support_repo.acknowledge_ticket(
        organization_id=principal.organization_id,
        ticket_id=ticket_id,
        actor_id=actor,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="support_ticket_not_found")
    return _ticket_response(row)


@router.post("/tickets/{ticket_id}/resolve", response_model=SupportTicketResponse)
async def resolve_support_ticket(
    ticket_id: str,
    request: ResolveSupportTicketRequest,
    deps: EnterpriseSupportDependencies = Depends(get_deps),
    principal: Principal = Depends(require_principal),
):
    _assert_support_write(principal)
    actor = principal.user.email if principal.kind == "jwt" and principal.user else principal.organization_id
    row = await deps.support_repo.resolve_ticket(
        organization_id=principal.organization_id,
        ticket_id=ticket_id,
        actor_id=actor,
        resolution_note=request.resolution_note,
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="support_ticket_not_found")
    return _ticket_response(row)

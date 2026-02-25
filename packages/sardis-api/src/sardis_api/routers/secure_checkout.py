"""Secure checkout executor endpoints (PAN-safe orchestration)."""
from __future__ import annotations

import asyncio
import hmac
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal


class MerchantExecutionMode(str, Enum):
    TOKENIZED_API = "tokenized_api"
    PAN_ENTRY = "pan_entry"
    BLOCKED = "blocked"


class SecureCheckoutJobStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    DISPATCHED = "dispatched"
    FAILED = "failed"
    REJECTED = "rejected"


@dataclass
class SecureCheckoutDependencies:
    wallet_repo: Any
    agent_repo: Any
    card_repo: Any
    card_provider: Any
    policy_store: Any | None = None
    approval_service: Any | None = None
    store: "InMemorySecureCheckoutStore | None" = None


class SecureExecutionOptions(BaseModel):
    """Execution safety flags for external browser workers."""

    trace: bool = False
    screenshot: bool = False
    video: bool = False
    strict_origin_check: bool = True


class CreateSecureCheckoutJobRequest(BaseModel):
    """Create a secure checkout job from an approved intent."""

    wallet_id: str
    card_id: str
    merchant_url: str
    amount: Decimal = Field(gt=0)
    currency: str = "USD"
    purpose: str = "agent_checkout"
    intent_id: str = Field(default_factory=lambda: f"intent_{uuid.uuid4().hex[:16]}")
    approval_id: Optional[str] = None
    options: SecureExecutionOptions = Field(default_factory=SecureExecutionOptions)


class ExecuteSecureCheckoutJobRequest(BaseModel):
    """Dispatch an already created secure checkout job."""

    approval_id: Optional[str] = None


class SecureCheckoutJobResponse(BaseModel):
    job_id: str
    intent_id: str
    wallet_id: str
    card_id: str
    merchant_origin: str
    merchant_mode: MerchantExecutionMode
    status: SecureCheckoutJobStatus
    amount: str
    currency: str
    approval_required: bool
    approval_id: Optional[str] = None
    policy_reason: str = "OK"
    executor_ref: Optional[str] = None
    secret_ref: Optional[str] = None
    secret_expires_at: Optional[str] = None
    redacted_card: dict[str, Any] = Field(default_factory=dict)
    options: SecureExecutionOptions
    created_at: str
    updated_at: str
    error_code: Optional[str] = None
    error: Optional[str] = None


class ConsumeExecutorSecretResponse(BaseModel):
    """One-time payload for isolated executor runtime."""

    pan: str
    cvv: str
    exp_month: int
    exp_year: int
    merchant_origin: str
    amount: str
    currency: str
    purpose: str


def get_deps() -> SecureCheckoutDependencies:
    raise NotImplementedError("Dependency override required")


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    return os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower() in {"prod", "production"}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_csv_env(name: str) -> list[str]:
    raw = os.getenv(name, "")
    return [part.strip().lower() for part in raw.split(",") if part.strip()]


def _host_matches(patterns: list[str], host: str) -> bool:
    host = (host or "").strip().lower()
    for pattern in patterns:
        if pattern.startswith("*."):
            suffix = pattern[1:]
            if host.endswith(suffix):
                return True
        elif host == pattern:
            return True
    return False


def _normalize_merchant_origin(merchant_url: str) -> tuple[str, str]:
    parsed = urlparse(merchant_url)
    scheme = (parsed.scheme or "").strip().lower()
    host = (parsed.hostname or "").strip().lower()
    if scheme not in {"https", "http"}:
        raise ValueError("merchant_url must include http/https scheme")
    if not host:
        raise ValueError("merchant_url missing hostname")
    port = parsed.port
    if port and not ((scheme == "https" and port == 443) or (scheme == "http" and port == 80)):
        origin = f"{scheme}://{host}:{port}"
    else:
        origin = f"{scheme}://{host}"
    return origin, host


def _resolve_merchant_mode(host: str) -> tuple[MerchantExecutionMode, str]:
    blocked = _parse_csv_env("SARDIS_CHECKOUT_BLOCKED_MERCHANTS")
    if _host_matches(blocked, host):
        return MerchantExecutionMode.BLOCKED, "merchant_blocked"

    tokenized = _parse_csv_env("SARDIS_CHECKOUT_TOKENIZED_MERCHANTS")
    if _host_matches(tokenized, host):
        return MerchantExecutionMode.TOKENIZED_API, "merchant_supports_tokenized_api"

    return MerchantExecutionMode.PAN_ENTRY, "merchant_requires_pan_entry"


def _sanitize_options(options: SecureExecutionOptions) -> SecureExecutionOptions:
    allow_trace = _is_truthy(os.getenv("SARDIS_CHECKOUT_ALLOW_EXECUTOR_TRACING", "0"))
    if allow_trace:
        return options
    return SecureExecutionOptions(
        trace=False,
        screenshot=False,
        video=False,
        strict_origin_check=options.strict_origin_check,
    )


def _redacted_card_summary(card: dict[str, Any] | None) -> dict[str, Any]:
    if not card:
        return {}
    last4 = str(card.get("card_number_last4") or "")
    expiry_month = card.get("expiry_month")
    expiry_year = card.get("expiry_year")
    return {
        "last4": last4,
        "expiry_month": expiry_month,
        "expiry_year": expiry_year,
        "provider": card.get("provider"),
    }


def _approval_threshold() -> Decimal:
    raw = os.getenv("SARDIS_CHECKOUT_APPROVAL_THRESHOLD_USD", "500")
    try:
        return Decimal(raw)
    except Exception:
        return Decimal("500")


def _require_approval_for_pan() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_REQUIRE_APPROVAL_FOR_PAN", "1"))


def _pan_execution_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "0"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_PAN_EXECUTION_ENABLED", "1"))


def _secret_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_CHECKOUT_SECRET_TTL_SECONDS", "60").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 60
    return max(10, min(value, 300))


class InMemorySecureCheckoutStore:
    """In-memory state for secure checkout jobs and one-time secret refs."""

    def __init__(self) -> None:
        self._jobs_by_id: dict[str, dict[str, Any]] = {}
        self._jobs_by_intent_id: dict[str, str] = {}
        self._secrets: dict[str, dict[str, Any]] = {}
        self._lock = asyncio.Lock()

    async def upsert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        async with self._lock:
            existing_id = self._jobs_by_intent_id.get(job["intent_id"])
            if existing_id:
                existing = self._jobs_by_id[existing_id]
                return dict(existing)
            self._jobs_by_id[job["job_id"]] = dict(job)
            self._jobs_by_intent_id[job["intent_id"]] = job["job_id"]
            return dict(job)

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            return dict(job) if job else None

    async def update_job(self, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        async with self._lock:
            job = self._jobs_by_id.get(job_id)
            if not job:
                return None
            updated = dict(job)
            updated.update(fields)
            updated["updated_at"] = _now_utc()
            self._jobs_by_id[job_id] = updated
            return dict(updated)

    async def put_secret(self, secret_ref: str, payload: dict[str, Any], expires_at: datetime) -> None:
        async with self._lock:
            self._secrets[secret_ref] = {
                "payload": dict(payload),
                "expires_at": expires_at,
                "consumed": False,
            }

    async def consume_secret(self, secret_ref: str) -> Optional[dict[str, Any]]:
        async with self._lock:
            secret = self._secrets.get(secret_ref)
            if not secret:
                return None
            if secret["consumed"]:
                return None
            if _now_utc() > secret["expires_at"]:
                self._secrets.pop(secret_ref, None)
                return None
            secret["consumed"] = True
            payload = dict(secret["payload"])
            self._secrets.pop(secret_ref, None)
            return payload


_DEFAULT_STORE = InMemorySecureCheckoutStore()


def _resolve_store(deps: SecureCheckoutDependencies) -> InMemorySecureCheckoutStore:
    return deps.store or _DEFAULT_STORE


def _serialize_job(job: dict[str, Any]) -> SecureCheckoutJobResponse:
    return SecureCheckoutJobResponse(
        job_id=job["job_id"],
        intent_id=job["intent_id"],
        wallet_id=job["wallet_id"],
        card_id=job["card_id"],
        merchant_origin=job["merchant_origin"],
        merchant_mode=MerchantExecutionMode(job["merchant_mode"]),
        status=SecureCheckoutJobStatus(job["status"]),
        amount=str(job["amount"]),
        currency=job["currency"],
        approval_required=bool(job["approval_required"]),
        approval_id=job.get("approval_id"),
        policy_reason=job.get("policy_reason", "OK"),
        executor_ref=job.get("executor_ref"),
        secret_ref=job.get("secret_ref"),
        secret_expires_at=job.get("secret_expires_at"),
        redacted_card=job.get("redacted_card") or {},
        options=SecureExecutionOptions(**(job.get("options") or {})),
        created_at=job["created_at"].isoformat(),
        updated_at=job["updated_at"].isoformat(),
        error_code=job.get("error_code"),
        error=job.get("error"),
    )


async def _require_wallet_access(
    *,
    deps: SecureCheckoutDependencies,
    principal: Principal,
    wallet_id: str,
) -> Any:
    if not deps.wallet_repo or not deps.agent_repo:
        if _is_production_env():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="wallet_or_agent_repository_not_configured",
            )
        return None

    wallet = await deps.wallet_repo.get(wallet_id)
    if not wallet:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wallet not found")

    agent = await deps.agent_repo.get(wallet.agent_id)
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    if not principal.is_admin and getattr(agent, "owner_id", None) != principal.organization_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")
    return wallet


async def _evaluate_policy(
    *,
    deps: SecureCheckoutDependencies,
    wallet: Any,
    amount: Decimal,
) -> tuple[bool, str]:
    if not deps.policy_store:
        if _is_production_env():
            return False, "policy_store_not_configured"
        return True, "OK"

    policy = await deps.policy_store.fetch_policy(wallet.agent_id)
    if not policy:
        return True, "OK"

    allowed, reason = policy.validate_payment(
        amount=amount,
        fee=Decimal("0"),
        mcc_code=None,
        merchant_category=None,
    )
    return bool(allowed), str(reason or "policy_denied")


async def _validate_approved_token(
    *,
    deps: SecureCheckoutDependencies,
    approval_id: Optional[str],
    principal: Principal,
    wallet_id: str,
) -> bool:
    if not approval_id:
        return False
    if not deps.approval_service:
        return False
    approval = await deps.approval_service.get_approval(approval_id)
    if not approval:
        return False
    if getattr(approval, "status", None) != "approved":
        return False
    approval_wallet_id = getattr(approval, "wallet_id", None)
    if approval_wallet_id and str(approval_wallet_id) != wallet_id:
        return False
    approval_org_id = getattr(approval, "organization_id", None)
    if approval_org_id and str(approval_org_id) != principal.organization_id and not principal.is_admin:
        return False
    return True


def create_secure_checkout_router() -> APIRouter:
    """Create secure checkout router."""
    router = APIRouter(dependencies=[Depends(require_principal)])

    @router.post("/secure/jobs", response_model=SecureCheckoutJobResponse, status_code=status.HTTP_201_CREATED)
    async def create_secure_job(
        payload: CreateSecureCheckoutJobRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        wallet = await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=payload.wallet_id,
        )

        if not deps.card_repo:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="card_repository_not_configured",
            )

        card = await deps.card_repo.get_by_card_id(payload.card_id)
        if not card:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Card not found")
        if str(card.get("wallet_id") or "") != payload.wallet_id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Card does not belong to wallet")

        card_status = str(card.get("status") or "").strip().lower()
        if card_status != "active":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Card is not active")

        try:
            merchant_origin, merchant_host = _normalize_merchant_origin(payload.merchant_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        merchant_mode, mode_reason = _resolve_merchant_mode(merchant_host)
        if merchant_mode == MerchantExecutionMode.BLOCKED:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=mode_reason)

        if wallet is None:
            policy_ok, policy_reason = (True, "OK")
        else:
            policy_ok, policy_reason = await _evaluate_policy(
                deps=deps,
                wallet=wallet,
                amount=payload.amount,
            )
        if not policy_ok:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=policy_reason)

        approval_required = (
            policy_reason == "requires_approval"
            or payload.amount >= _approval_threshold()
            or (merchant_mode == MerchantExecutionMode.PAN_ENTRY and _require_approval_for_pan())
        )
        approval_ok = await _validate_approved_token(
            deps=deps,
            approval_id=payload.approval_id,
            principal=principal,
            wallet_id=payload.wallet_id,
        )
        job_status = SecureCheckoutJobStatus.READY
        if approval_required and not approval_ok:
            job_status = SecureCheckoutJobStatus.PENDING_APPROVAL

        now = _now_utc()
        options = _sanitize_options(payload.options)
        job = {
            "job_id": f"scj_{uuid.uuid4().hex[:16]}",
            "intent_id": payload.intent_id,
            "wallet_id": payload.wallet_id,
            "card_id": payload.card_id,
            "merchant_origin": merchant_origin,
            "merchant_mode": merchant_mode.value,
            "status": job_status.value,
            "amount": payload.amount,
            "currency": payload.currency.upper(),
            "purpose": payload.purpose,
            "approval_required": approval_required,
            "approval_id": payload.approval_id if approval_ok else None,
            "policy_reason": policy_reason,
            "executor_ref": None,
            "secret_ref": None,
            "secret_expires_at": None,
            "redacted_card": _redacted_card_summary(card),
            "options": options.model_dump(),
            "created_at": now,
            "updated_at": now,
            "error_code": None,
            "error": None,
        }
        saved = await store.upsert_job(job)
        return _serialize_job(saved)

    @router.get("/secure/jobs/{job_id}", response_model=SecureCheckoutJobResponse)
    async def get_secure_job(
        job_id: str,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=job["wallet_id"],
        )
        return _serialize_job(job)

    @router.post("/secure/jobs/{job_id}/execute", response_model=SecureCheckoutJobResponse)
    async def execute_secure_job(
        job_id: str,
        payload: ExecuteSecureCheckoutJobRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await _require_wallet_access(
            deps=deps,
            principal=principal,
            wallet_id=job["wallet_id"],
        )

        if job["status"] == SecureCheckoutJobStatus.PENDING_APPROVAL.value:
            approval_ok = await _validate_approved_token(
                deps=deps,
                approval_id=payload.approval_id,
                principal=principal,
                wallet_id=job["wallet_id"],
            )
            if not approval_ok:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="approval_required")
            job = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.READY.value,
                approval_id=payload.approval_id,
            ) or job

        if job["status"] != SecureCheckoutJobStatus.READY.value:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"job_not_ready:{job['status']}")

        if job["merchant_mode"] == MerchantExecutionMode.TOKENIZED_API.value:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.DISPATCHED.value,
                executor_ref=f"tokenized:{job_id}",
            )
            return _serialize_job(updated or job)

        if not _pan_execution_enabled():
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="pan_execution_disabled",
                error="PAN execution is disabled by policy",
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            )

        if not deps.card_provider:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="card_provider_not_configured",
            )

        try:
            details = await deps.card_provider.reveal_card_details(
                card_id=job["card_id"],
                reason="secure_checkout_executor",
            )
        except Exception as exc:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="card_details_reveal_failed",
                error=str(exc),
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=(updated or job).get("error_code"),
            ) from exc

        secret_ref = f"sec_{uuid.uuid4().hex[:18]}"
        expires_at = _now_utc() + timedelta(seconds=_secret_ttl_seconds())
        secret_payload = {
            "pan": str(details.get("pan") or ""),
            "cvv": str(details.get("cvv") or ""),
            "exp_month": int(details.get("exp_month") or 0),
            "exp_year": int(details.get("exp_year") or 0),
            "merchant_origin": job["merchant_origin"],
            "amount": str(job["amount"]),
            "currency": job["currency"],
            "purpose": job["purpose"],
        }
        await store.put_secret(secret_ref, secret_payload, expires_at=expires_at)
        updated = await store.update_job(
            job_id,
            status=SecureCheckoutJobStatus.DISPATCHED.value,
            secret_ref=secret_ref,
            secret_expires_at=expires_at.isoformat(),
            executor_ref=f"secret_ref:{secret_ref}",
        )
        return _serialize_job(updated or job)

    @router.post(
        "/secure/secrets/{secret_ref}/consume",
        response_model=ConsumeExecutorSecretResponse,
        include_in_schema=False,
    )
    async def consume_executor_secret(
        secret_ref: str,
        x_sardis_executor_token: Optional[str] = Header(default=None),
        deps: SecureCheckoutDependencies = Depends(get_deps),
    ):
        expected = os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
        if expected:
            presented = (x_sardis_executor_token or "").strip()
            if not presented or not hmac.compare_digest(presented, expected):
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_executor_token")
        elif _is_production_env():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="executor_token_not_configured",
            )

        store = _resolve_store(deps)
        payload = await store.consume_secret(secret_ref)
        if not payload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="secret_not_found_or_expired")
        return ConsumeExecutorSecretResponse(**payload)

    return router


router = create_secure_checkout_router()

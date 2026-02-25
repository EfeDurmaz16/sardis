"""Secure checkout executor endpoints (PAN-safe orchestration)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import inspect
import json
import os
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Optional
from urllib.parse import urlparse

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field

from sardis_api.authz import Principal, require_principal


class MerchantExecutionMode(str, Enum):
    TOKENIZED_API = "tokenized_api"
    EMBEDDED_IFRAME = "embedded_iframe"
    PAN_ENTRY = "pan_entry"
    BLOCKED = "blocked"


class SecureCheckoutJobStatus(str, Enum):
    PENDING_APPROVAL = "pending_approval"
    READY = "ready"
    DISPATCHED = "dispatched"
    COMPLETED = "completed"
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
    audit_sink: Any | None = None
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


class CompleteSecureCheckoutJobRequest(BaseModel):
    status: str = Field(pattern="^(completed|failed)$")
    executor_ref: Optional[str] = None
    failure_reason: Optional[str] = None


class MerchantCapabilityRequest(BaseModel):
    merchant_url: str
    amount: Optional[Decimal] = Field(default=None, gt=0)
    currency: str = "USD"


class MerchantCapabilityResponse(BaseModel):
    merchant_origin: str
    merchant_host: str
    merchant_mode: MerchantExecutionMode
    mode_reason: str
    approval_likely_required: bool
    pan_execution_enabled: bool
    pan_allowed_for_merchant: bool
    pan_compliance_ready: bool
    pan_compliance_reason: str


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

    embedded = _parse_csv_env("SARDIS_CHECKOUT_EMBEDDED_IFRAME_MERCHANTS")
    if _host_matches(embedded, host):
        return MerchantExecutionMode.EMBEDDED_IFRAME, "merchant_supports_embedded_iframe"

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


def _require_tokenized_in_prod() -> bool:
    if not _is_production_env():
        return False
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_REQUIRE_TOKENIZED_IN_PROD", "1"))


def _pan_entry_allowed_for_host(host: str) -> bool:
    allowlist = _parse_csv_env("SARDIS_CHECKOUT_PAN_ENTRY_ALLOWED_MERCHANTS")
    return _host_matches(allowlist, host)


def _pan_entry_policy_decision(host: str) -> tuple[bool, str]:
    if not _pan_execution_enabled():
        return False, "pan_execution_disabled"
    if _is_production_env():
        if not _is_truthy(os.getenv("SARDIS_CHECKOUT_PCI_ATTESTATION_ACK", "0")):
            return False, "pan_compliance_not_attested"
        if not os.getenv("SARDIS_CHECKOUT_QSA_CONTACT", "").strip():
            return False, "pan_qsa_contact_missing"
    if _require_tokenized_in_prod() and not _pan_entry_allowed_for_host(host):
        return False, "pan_entry_not_allowlisted"
    return True, "pan_entry_allowed"


def _secret_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_CHECKOUT_SECRET_TTL_SECONDS", "60").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 60
    return max(10, min(value, 300))


def _executor_dispatch_url() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_URL", "").strip()


def _dispatch_required() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_DISPATCH_REQUIRED", "0"))


def _dispatch_timeout_seconds() -> float:
    raw = os.getenv("SARDIS_CHECKOUT_DISPATCH_TIMEOUT_SECONDS", "5").strip()
    try:
        value = float(raw)
    except ValueError:
        value = 5.0
    return max(1.0, min(value, 30.0))


def _dispatch_signing_key() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "").strip()


def _executor_attestation_enabled() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "1"))
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_ENFORCE_EXECUTOR_ATTESTATION", "0"))


def _executor_attestation_key() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_KEY", "").strip()


def _executor_attestation_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_CHECKOUT_EXECUTOR_ATTESTATION_TTL_SECONDS", "120").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 120
    return max(30, min(value, 900))


def _hash_payload_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _compute_executor_signature(
    *,
    key: str,
    method: str,
    path: str,
    timestamp: str,
    nonce: str,
    payload_hash: str,
) -> str:
    canonical = "\n".join([method.upper(), path, timestamp, nonce, payload_hash])
    return hmac.new(key.encode("utf-8"), canonical.encode("utf-8"), hashlib.sha256).hexdigest()


async def _dispatch_to_executor(
    *,
    job: dict[str, Any],
    secret_ref: Optional[str] = None,
    secret_expires_at: Optional[str] = None,
) -> tuple[bool, Optional[str], Optional[str]]:
    """
    Dispatch metadata-only execution request to an isolated worker.

    Never includes PAN/CVV in payload. Worker must consume secret_ref separately.
    """
    dispatch_url = _executor_dispatch_url()
    if not dispatch_url:
        return True, None, None

    token = (
        os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "").strip()
        or os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
    )
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    payload = {
        "job_id": job["job_id"],
        "intent_id": job["intent_id"],
        "wallet_id": job["wallet_id"],
        "card_id": job["card_id"],
        "merchant_origin": job["merchant_origin"],
        "merchant_mode": job["merchant_mode"],
        "amount": str(job["amount"]),
        "currency": job["currency"],
        "purpose": job["purpose"],
        "options": job.get("options") or {},
        "secret_ref": secret_ref,
        "secret_expires_at": secret_expires_at,
    }

    timeout = _dispatch_timeout_seconds()
    signing_key = _dispatch_signing_key()
    if signing_key:
        now_ts = str(int(time.time()))
        nonce = uuid.uuid4().hex
        payload_hash = _hash_payload_bytes(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8"))
        dispatch_path = urlparse(dispatch_url).path or "/"
        headers["X-Sardis-Timestamp"] = now_ts
        headers["X-Sardis-Nonce"] = nonce
        headers["X-Sardis-Signature"] = _compute_executor_signature(
            key=signing_key,
            method="POST",
            path=dispatch_path,
            timestamp=now_ts,
            nonce=nonce,
            payload_hash=payload_hash,
        )
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(dispatch_url, json=payload, headers=headers)
    except Exception as exc:  # noqa: BLE001
        return False, None, f"executor_dispatch_failed:{exc}"

    if response.status_code >= 400:
        return False, None, f"executor_dispatch_http_{response.status_code}"

    executor_ref: Optional[str] = None
    try:
        body = response.json()
        if isinstance(body, dict):
            candidate = body.get("execution_id") or body.get("executor_ref") or body.get("job_id")
            if candidate:
                executor_ref = str(candidate)
    except Exception:
        executor_ref = None
    return True, executor_ref, None


class InMemorySecureCheckoutStore:
    """In-memory state for secure checkout jobs and one-time secret refs."""

    def __init__(self) -> None:
        self.is_persistent = False
        self._jobs_by_id: dict[str, dict[str, Any]] = {}
        self._jobs_by_intent_id: dict[str, str] = {}
        self._secrets: dict[str, dict[str, Any]] = {}
        self._used_executor_nonces: dict[str, float] = {}
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

    async def drop_secret(self, secret_ref: str) -> None:
        async with self._lock:
            self._secrets.pop(secret_ref, None)

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

    async def mark_executor_nonce_used(self, nonce: str, *, ttl_seconds: int) -> bool:
        now = time.time()
        expires_at = now + float(ttl_seconds)
        async with self._lock:
            expired = [n for n, exp in self._used_executor_nonces.items() if exp <= now]
            for n in expired:
                self._used_executor_nonces.pop(n, None)
            if nonce in self._used_executor_nonces:
                return False
            self._used_executor_nonces[nonce] = expires_at
            return True


_DEFAULT_STORE = InMemorySecureCheckoutStore()


def _resolve_store(deps: SecureCheckoutDependencies) -> InMemorySecureCheckoutStore:
    return deps.store or _DEFAULT_STORE


class RepositoryBackedSecureCheckoutStore(InMemorySecureCheckoutStore):
    """Persistent job storage + in-memory one-time secret storage."""

    def __init__(self, job_repository: Any):
        super().__init__()
        self.is_persistent = True
        self._job_repository = job_repository

    async def upsert_job(self, job: dict[str, Any]) -> dict[str, Any]:
        if not self._job_repository:
            return await super().upsert_job(job)
        return await self._job_repository.upsert_job(job)

    async def get_job(self, job_id: str) -> Optional[dict[str, Any]]:
        if not self._job_repository:
            return await super().get_job(job_id)
        return await self._job_repository.get_job(job_id)

    async def update_job(self, job_id: str, **fields: Any) -> Optional[dict[str, Any]]:
        if not self._job_repository:
            return await super().update_job(job_id, **fields)
        return await self._job_repository.update_job(job_id, **fields)


def _allow_inmemory_store_in_prod() -> bool:
    return _is_truthy(os.getenv("SARDIS_CHECKOUT_ALLOW_INMEMORY_STORE", "0"))


def _require_persistent_job_store() -> bool:
    return _is_production_env() and not _allow_inmemory_store_in_prod()


def _is_persistent_store(store: Any) -> bool:
    return bool(getattr(store, "is_persistent", False))


async def _emit_audit_event(
    deps: SecureCheckoutDependencies,
    *,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    sink = deps.audit_sink
    if not sink:
        return
    event = {
        "event_type": event_type,
        "ts": _now_utc().isoformat(),
        "payload": payload,
    }
    record_callable = None
    if hasattr(sink, "record_event"):
        record_callable = getattr(sink, "record_event")
    elif hasattr(sink, "write_event"):
        record_callable = getattr(sink, "write_event")
    elif hasattr(sink, "append"):
        try:
            from sardis_compliance.checks import ComplianceAuditEntry
        except Exception:
            ComplianceAuditEntry = None  # type: ignore[assignment]

        if ComplianceAuditEntry is not None:
            entry = ComplianceAuditEntry(
                mandate_id=str(payload.get("intent_id") or payload.get("job_id") or ""),
                subject=str(payload.get("wallet_id") or ""),
                allowed=event_type != "secure_checkout.job_failed",
                reason=str(payload.get("error_code") or payload.get("status") or event_type),
                rule_id=event_type,
                provider="secure_checkout",
                metadata=dict(payload),
            )
            record_callable = getattr(sink, "append")
            result = record_callable(entry)
            if inspect.isawaitable(result):
                await result
            return
    elif callable(sink):
        record_callable = sink

    if record_callable is None:
        return

    result = record_callable(event)
    if inspect.isawaitable(result):
        await result


async def _verify_executor_auth(
    *,
    deps: SecureCheckoutDependencies,
    request: Request,
    token: Optional[str],
    timestamp: Optional[str],
    nonce: Optional[str],
    signature: Optional[str],
    payload_bytes: bytes,
) -> None:
    expected = os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
    if expected:
        presented = (token or "").strip()
        if not presented or not hmac.compare_digest(presented, expected):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_executor_token")
    elif _is_production_env():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="executor_token_not_configured",
        )

    if not _executor_attestation_enabled():
        return

    key = _executor_attestation_key()
    if not key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="executor_attestation_key_not_configured",
        )

    ts = (timestamp or "").strip()
    nonce_value = (nonce or "").strip()
    signature_value = (signature or "").strip()
    if not ts or not nonce_value or not signature_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_missing")

    try:
        ts_value = int(ts)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_invalid_ts") from exc

    ttl_seconds = _executor_attestation_ttl_seconds()
    now = int(time.time())
    if abs(now - ts_value) > ttl_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_expired")

    payload_hash = _hash_payload_bytes(payload_bytes)
    expected_sig = _compute_executor_signature(
        key=key,
        method=request.method,
        path=request.url.path,
        timestamp=ts,
        nonce=nonce_value,
        payload_hash=payload_hash,
    )
    if not hmac.compare_digest(signature_value, expected_sig):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_invalid_signature")

    store = _resolve_store(deps)
    first_seen = await store.mark_executor_nonce_used(nonce_value, ttl_seconds=ttl_seconds)
    if not first_seen:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="executor_attestation_replay")


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

    @router.post("/secure/merchant-capability", response_model=MerchantCapabilityResponse)
    async def get_merchant_capability(
        payload: MerchantCapabilityRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        # Keep the same wallet/org auth surface by requiring principal even for preflight.
        _ = deps
        _ = principal
        try:
            merchant_origin, merchant_host = _normalize_merchant_origin(payload.merchant_url)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

        merchant_mode, mode_reason = _resolve_merchant_mode(merchant_host)
        pan_allowed_for_merchant = True
        pan_compliance_ready = True
        pan_compliance_reason = "ok"
        if merchant_mode == MerchantExecutionMode.PAN_ENTRY:
            pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
            pan_compliance_ready = pan_mode_reason in {"pan_entry_allowed", "pan_entry_not_allowlisted"}
            pan_compliance_reason = "ok" if pan_compliance_ready else pan_mode_reason
            if not pan_allowed_for_merchant:
                mode_reason = pan_mode_reason
        threshold = _approval_threshold()
        amount = payload.amount or Decimal("0")
        approval_likely_required = (
            (merchant_mode == MerchantExecutionMode.PAN_ENTRY and _require_approval_for_pan())
            or (payload.amount is not None and amount >= threshold)
        )
        return MerchantCapabilityResponse(
            merchant_origin=merchant_origin,
            merchant_host=merchant_host,
            merchant_mode=merchant_mode,
            mode_reason=mode_reason,
            approval_likely_required=approval_likely_required,
            pan_execution_enabled=_pan_execution_enabled(),
            pan_allowed_for_merchant=pan_allowed_for_merchant,
            pan_compliance_ready=pan_compliance_ready,
            pan_compliance_reason=pan_compliance_reason,
        )

    @router.post("/secure/jobs", response_model=SecureCheckoutJobResponse, status_code=status.HTTP_201_CREATED)
    async def create_secure_job(
        payload: CreateSecureCheckoutJobRequest,
        deps: SecureCheckoutDependencies = Depends(get_deps),
        principal: Principal = Depends(require_principal),
    ):
        store = _resolve_store(deps)
        if _require_persistent_job_store() and not _is_persistent_store(store):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="secure_checkout_persistent_store_required",
            )
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
        if merchant_mode == MerchantExecutionMode.PAN_ENTRY:
            pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
            if not pan_allowed_for_merchant:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=pan_mode_reason)

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
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_created",
            payload={
                "job_id": saved["job_id"],
                "intent_id": saved["intent_id"],
                "wallet_id": saved["wallet_id"],
                "merchant_origin": saved["merchant_origin"],
                "merchant_mode": saved["merchant_mode"],
                "status": saved["status"],
                "approval_required": saved["approval_required"],
                "policy_reason": saved.get("policy_reason"),
            },
        )
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
        if _require_persistent_job_store() and not _is_persistent_store(store):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="secure_checkout_persistent_store_required",
            )
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

        if job["merchant_mode"] in {
            MerchantExecutionMode.TOKENIZED_API.value,
            MerchantExecutionMode.EMBEDDED_IFRAME.value,
        }:
            dispatch_ok, executor_ref, dispatch_error = await _dispatch_to_executor(job=job)
            if not dispatch_ok and _dispatch_required():
                updated = await store.update_job(
                    job_id,
                    status=SecureCheckoutJobStatus.FAILED.value,
                    error_code="executor_dispatch_failed",
                    error=dispatch_error or "executor_dispatch_failed",
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail=(updated or job).get("error_code"),
                )
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.DISPATCHED.value,
                executor_ref=executor_ref
                or (
                    f"embedded_iframe:{job_id}"
                    if job["merchant_mode"] == MerchantExecutionMode.EMBEDDED_IFRAME.value
                    else f"tokenized:{job_id}"
                ),
            )
            dispatched = updated or job
            await _emit_audit_event(
                deps,
                event_type="secure_checkout.job_dispatched",
                payload={
                    "job_id": dispatched["job_id"],
                    "intent_id": dispatched["intent_id"],
                    "wallet_id": dispatched["wallet_id"],
                    "merchant_mode": dispatched["merchant_mode"],
                    "executor_ref": dispatched.get("executor_ref"),
                    "secret_ref": None,
                },
            )
            return _serialize_job(updated or job)

        merchant_host = urlparse(job["merchant_origin"]).hostname or ""
        pan_allowed_for_merchant, pan_mode_reason = _pan_entry_policy_decision(merchant_host)
        if not pan_allowed_for_merchant:
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code=pan_mode_reason,
                error=f"PAN execution rejected: {pan_mode_reason}",
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
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
        dispatch_ok, executor_ref, dispatch_error = await _dispatch_to_executor(
            job=job,
            secret_ref=secret_ref,
            secret_expires_at=expires_at.isoformat(),
        )
        if not dispatch_ok and _dispatch_required():
            updated = await store.update_job(
                job_id,
                status=SecureCheckoutJobStatus.FAILED.value,
                error_code="executor_dispatch_failed",
                error=dispatch_error or "executor_dispatch_failed",
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=(updated or job).get("error_code"),
            )
        updated = await store.update_job(
            job_id,
            status=SecureCheckoutJobStatus.DISPATCHED.value,
            secret_ref=secret_ref,
            secret_expires_at=expires_at.isoformat(),
            executor_ref=executor_ref or f"secret_ref:{secret_ref}",
        )
        dispatched = updated or job
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_dispatched",
            payload={
                "job_id": dispatched["job_id"],
                "intent_id": dispatched["intent_id"],
                "wallet_id": dispatched["wallet_id"],
                "merchant_mode": dispatched["merchant_mode"],
                "executor_ref": dispatched.get("executor_ref"),
                "secret_ref_present": bool(dispatched.get("secret_ref")),
                "secret_expires_at": dispatched.get("secret_expires_at"),
            },
        )
        return _serialize_job(updated or job)

    @router.post(
        "/secure/secrets/{secret_ref}/consume",
        response_model=ConsumeExecutorSecretResponse,
        include_in_schema=False,
    )
    async def consume_executor_secret(
        secret_ref: str,
        request: Request,
        x_sardis_executor_token: Optional[str] = Header(default=None),
        x_sardis_executor_timestamp: Optional[str] = Header(default=None),
        x_sardis_executor_nonce: Optional[str] = Header(default=None),
        x_sardis_executor_signature: Optional[str] = Header(default=None),
        deps: SecureCheckoutDependencies = Depends(get_deps),
    ):
        await _verify_executor_auth(
            deps=deps,
            request=request,
            token=x_sardis_executor_token,
            timestamp=x_sardis_executor_timestamp,
            nonce=x_sardis_executor_nonce,
            signature=x_sardis_executor_signature,
            payload_bytes=await request.body(),
        )

        store = _resolve_store(deps)
        payload = await store.consume_secret(secret_ref)
        if not payload:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="secret_not_found_or_expired")
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.secret_consumed",
            payload={
                "secret_ref": secret_ref,
                "merchant_origin": payload.get("merchant_origin"),
                "amount": payload.get("amount"),
                "currency": payload.get("currency"),
                "purpose": payload.get("purpose"),
            },
        )
        return ConsumeExecutorSecretResponse(**payload)

    @router.post(
        "/secure/jobs/{job_id}/complete",
        response_model=SecureCheckoutJobResponse,
        include_in_schema=False,
    )
    async def complete_executor_job(
        job_id: str,
        payload: CompleteSecureCheckoutJobRequest,
        request: Request,
        x_sardis_executor_token: Optional[str] = Header(default=None),
        x_sardis_executor_timestamp: Optional[str] = Header(default=None),
        x_sardis_executor_nonce: Optional[str] = Header(default=None),
        x_sardis_executor_signature: Optional[str] = Header(default=None),
        deps: SecureCheckoutDependencies = Depends(get_deps),
    ):
        await _verify_executor_auth(
            deps=deps,
            request=request,
            token=x_sardis_executor_token,
            timestamp=x_sardis_executor_timestamp,
            nonce=x_sardis_executor_nonce,
            signature=x_sardis_executor_signature,
            payload_bytes=await request.body(),
        )

        store = _resolve_store(deps)
        job = await store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        if job["status"] != SecureCheckoutJobStatus.DISPATCHED.value:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"job_not_dispatched:{job['status']}",
            )

        desired_status = SecureCheckoutJobStatus.COMPLETED.value
        error_code = None
        error = None
        if payload.status == "failed":
            desired_status = SecureCheckoutJobStatus.FAILED.value
            error_code = "executor_failed"
            error = payload.failure_reason or "executor_failed"

        secret_ref = job.get("secret_ref")
        if secret_ref:
            await store.drop_secret(secret_ref)

        updated = await store.update_job(
            job_id,
            status=desired_status,
            executor_ref=payload.executor_ref or job.get("executor_ref"),
            error_code=error_code,
            error=error,
            secret_ref=None,
            secret_expires_at=None,
        )
        finalized = updated or job
        await _emit_audit_event(
            deps,
            event_type="secure_checkout.job_finalized",
            payload={
                "job_id": finalized["job_id"],
                "intent_id": finalized["intent_id"],
                "wallet_id": finalized["wallet_id"],
                "status": finalized["status"],
                "executor_ref": finalized.get("executor_ref"),
                "error_code": finalized.get("error_code"),
            },
        )
        return _serialize_job(updated or job)

    return router


router = create_secure_checkout_router()

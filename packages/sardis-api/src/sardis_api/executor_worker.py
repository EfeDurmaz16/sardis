"""Reference secure checkout executor worker (dispatch ingress)."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

import httpx
from fastapi import APIRouter, FastAPI, Header, HTTPException, Request, status
from pydantic import BaseModel


class DispatchJobRequest(BaseModel):
    job_id: str
    intent_id: str
    wallet_id: str
    card_id: str
    merchant_origin: str
    merchant_mode: str
    amount: str
    currency: str
    purpose: str
    options: dict[str, Any] = {}
    secret_ref: Optional[str] = None
    secret_expires_at: Optional[str] = None


class DispatchJobResponse(BaseModel):
    accepted: bool
    duplicate: bool
    execution_id: str
    job_id: str
    received_at: str


class CompletionResult(BaseModel):
    delivered: bool
    attempts: int
    status_code: int | None = None
    error: str | None = None


class InMemoryExecutorDispatchStore:
    """Idempotent job acceptance + nonce replay protection."""

    def __init__(self) -> None:
        self._jobs_by_id: dict[str, dict[str, Any]] = {}
        self._used_nonces: dict[str, float] = {}
        self._lock = asyncio.Lock()

    async def register_or_get(self, payload: DispatchJobRequest) -> tuple[dict[str, Any], bool]:
        async with self._lock:
            existing = self._jobs_by_id.get(payload.job_id)
            if existing:
                return dict(existing), True
            now = datetime.now(timezone.utc)
            item = {
                "execution_id": f"exec_{uuid.uuid4().hex[:16]}",
                "job_id": payload.job_id,
                "intent_id": payload.intent_id,
                "wallet_id": payload.wallet_id,
                "merchant_mode": payload.merchant_mode,
                "secret_ref_present": bool(payload.secret_ref),
                "received_at": now,
            }
            self._jobs_by_id[payload.job_id] = item
            return dict(item), False

    async def mark_nonce(self, nonce: str, *, ttl_seconds: int) -> bool:
        now = time.time()
        expires_at = now + float(ttl_seconds)
        async with self._lock:
            expired = [n for n, exp in self._used_nonces.items() if exp <= now]
            for key in expired:
                self._used_nonces.pop(key, None)
            if nonce in self._used_nonces:
                return False
            self._used_nonces[nonce] = expires_at
            return True


def _is_truthy(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _is_production_env() -> bool:
    return os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower() in {"prod", "production"}


def _dispatch_token() -> str:
    return (
        os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_TOKEN", "").strip()
        or os.getenv("SARDIS_CHECKOUT_EXECUTOR_TOKEN", "").strip()
    )


def _dispatch_signing_key() -> str:
    return os.getenv("SARDIS_CHECKOUT_EXECUTOR_DISPATCH_SIGNING_KEY", "").strip()


def _dispatch_signature_ttl_seconds() -> int:
    raw = os.getenv("SARDIS_EXECUTOR_DISPATCH_SIGNATURE_TTL_SECONDS", "120").strip()
    try:
        value = int(raw)
    except ValueError:
        value = 120
    return max(30, min(value, 900))


def _enforce_signed_dispatch() -> bool:
    if _is_production_env():
        return _is_truthy(os.getenv("SARDIS_EXECUTOR_ENFORCE_SIGNED_DISPATCH", "1"))
    return _is_truthy(os.getenv("SARDIS_EXECUTOR_ENFORCE_SIGNED_DISPATCH", "0"))


def _hash_payload_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _compute_signature(
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


async def _verify_dispatch_request(
    *,
    request: Request,
    store: InMemoryExecutorDispatchStore,
    authorization: Optional[str],
    timestamp: Optional[str],
    nonce: Optional[str],
    signature: Optional[str],
    body_bytes: bytes,
) -> None:
    expected_token = _dispatch_token()
    if expected_token:
        presented = (authorization or "").strip()
        if presented.startswith("Bearer "):
            presented = presented[len("Bearer ") :].strip()
        if not presented or not hmac.compare_digest(presented, expected_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_dispatch_token")
    elif _is_production_env():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dispatch_token_not_configured",
        )

    if not _enforce_signed_dispatch():
        return

    signing_key = _dispatch_signing_key()
    if not signing_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="dispatch_signing_key_not_configured",
        )

    ts = (timestamp or "").strip()
    nonce_value = (nonce or "").strip()
    signature_value = (signature or "").strip()
    if not ts or not nonce_value or not signature_value:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="dispatch_signature_missing")

    try:
        ts_value = int(ts)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="dispatch_signature_invalid_ts") from exc

    ttl_seconds = _dispatch_signature_ttl_seconds()
    now = int(time.time())
    if abs(now - ts_value) > ttl_seconds:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="dispatch_signature_expired")

    payload_hash = _hash_payload_bytes(body_bytes)
    expected_signature = _compute_signature(
        key=signing_key,
        method=request.method,
        path=request.url.path,
        timestamp=ts,
        nonce=nonce_value,
        payload_hash=payload_hash,
    )
    if not hmac.compare_digest(signature_value, expected_signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="dispatch_signature_invalid",
        )

    if not await store.mark_nonce(nonce_value, ttl_seconds=ttl_seconds):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="dispatch_signature_replay",
        )


def create_executor_worker_router(store: InMemoryExecutorDispatchStore | None = None) -> APIRouter:
    router = APIRouter()
    dispatch_store = store or InMemoryExecutorDispatchStore()

    @router.post("/internal/executor/jobs", response_model=DispatchJobResponse, status_code=status.HTTP_202_ACCEPTED)
    async def accept_dispatch_job(
        payload: DispatchJobRequest,
        request: Request,
        authorization: Optional[str] = Header(default=None),
        x_sardis_timestamp: Optional[str] = Header(default=None),
        x_sardis_nonce: Optional[str] = Header(default=None),
        x_sardis_signature: Optional[str] = Header(default=None),
    ):
        # Ensure signature validation uses the exact request body bytes.
        body = await request.body()
        await _verify_dispatch_request(
            request=request,
            store=dispatch_store,
            authorization=authorization,
            timestamp=x_sardis_timestamp,
            nonce=x_sardis_nonce,
            signature=x_sardis_signature,
            body_bytes=body,
        )

        record, duplicate = await dispatch_store.register_or_get(payload)
        return DispatchJobResponse(
            accepted=True,
            duplicate=duplicate,
            execution_id=str(record["execution_id"]),
            job_id=str(record["job_id"]),
            received_at=record["received_at"].isoformat(),
        )

    return router


def create_executor_worker_app(store: InMemoryExecutorDispatchStore | None = None) -> FastAPI:
    app = FastAPI(
        title="Sardis Secure Checkout Executor Worker",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.include_router(create_executor_worker_router(store=store))
    return app


def canonical_dispatch_payload_bytes(payload: dict[str, Any]) -> bytes:
    """Helper for tests/clients to sign dispatch payload exactly."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


class SecureCheckoutCompletionClient:
    """Callback client for secure checkout completion notifications."""

    def __init__(
        self,
        *,
        callback_base_url: str,
        executor_token: str,
        timeout_seconds: float = 5.0,
        max_attempts: int = 3,
        backoff_seconds: float = 0.25,
    ) -> None:
        self._base_url = callback_base_url.rstrip("/")
        self._token = executor_token.strip()
        self._timeout_seconds = max(0.5, float(timeout_seconds))
        self._max_attempts = max(1, int(max_attempts))
        self._backoff_seconds = max(0.05, float(backoff_seconds))

    async def complete_job(
        self,
        *,
        job_id: str,
        status_value: str,
        executor_ref: str | None = None,
        failure_reason: str | None = None,
        idempotency_key: str | None = None,
    ) -> CompletionResult:
        endpoint = f"{self._base_url}/api/v2/checkout/secure/jobs/{job_id}/complete"
        payload: dict[str, Any] = {
            "status": status_value,
            "executor_ref": executor_ref,
            "failure_reason": failure_reason,
        }
        headers = {
            "Content-Type": "application/json",
            "X-Sardis-Executor-Token": self._token,
        }
        headers["X-Sardis-Completion-Idempotency-Key"] = (
            idempotency_key.strip()
            if idempotency_key and idempotency_key.strip()
            else f"complete:{job_id}:{status_value}"
        )

        last_error: str | None = None
        last_status: int | None = None
        async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
            for attempt in range(1, self._max_attempts + 1):
                try:
                    response = await client.post(endpoint, json=payload, headers=headers)
                    last_status = response.status_code
                    if response.status_code < 500:
                        delivered = response.status_code < 400
                        return CompletionResult(
                            delivered=delivered,
                            attempts=attempt,
                            status_code=response.status_code,
                            error=None if delivered else f"http_{response.status_code}",
                        )
                    last_error = f"http_{response.status_code}"
                except Exception as exc:  # noqa: BLE001
                    last_error = str(exc)
                if attempt < self._max_attempts:
                    await asyncio.sleep(self._backoff_seconds * attempt)

        return CompletionResult(
            delivered=False,
            attempts=self._max_attempts,
            status_code=last_status,
            error=last_error or "delivery_failed",
        )

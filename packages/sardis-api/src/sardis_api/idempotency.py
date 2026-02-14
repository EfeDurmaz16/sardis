"""Idempotency helpers for fintech-safe endpoints."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Optional

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from sardis_api.authz import Principal


IDEMPOTENCY_HEADERS = ("Idempotency-Key", "X-Idempotency-Key")


@dataclass(frozen=True)
class IdempotencyRecord:
    status_code: int
    body: Any
    request_hash: str


def _hash_payload(payload: Any) -> str:
    encoded = jsonable_encoder(payload)
    raw = json.dumps(encoded, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def get_idempotency_key(request: Request) -> Optional[str]:
    for header in IDEMPOTENCY_HEADERS:
        value = request.headers.get(header)
        if value:
            return value.strip()
    return None


def _cache_key(*parts: str) -> str:
    safe = [p.replace(":", "_") for p in parts]
    return "sardis:idem:" + ":".join(safe)


async def run_idempotent(
    *,
    request: Request,
    principal: Principal,
    operation: str,
    key: str,
    payload: Any,
    ttl_seconds: int = 24 * 60 * 60,
    lock_ttl_seconds: int = 30,
    fn: Callable[[], Awaitable[tuple[int, Any]]],
) -> JSONResponse:
    """
    Execute `fn()` exactly-once for a given (org, operation, key).

    Stores and returns the first response for subsequent retries.
    Rejects re-use with a different payload (tampering).
    """
    cache = getattr(request.app.state, "cache_service", None)
    if cache is None:
        status_code, body = await fn()
        return JSONResponse(status_code=status_code, content=jsonable_encoder(body))

    req_hash = _hash_payload(payload)
    record_key = _cache_key(principal.organization_id, operation, key, "record")
    lock_resource = _cache_key(principal.organization_id, operation, key, "lock")

    existing_raw = await cache.get(record_key)
    if existing_raw:
        try:
            existing = json.loads(existing_raw)
            if existing.get("request_hash") != req_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key_reuse_different_payload",
                )
            return JSONResponse(
                status_code=int(existing.get("status_code", 200)),
                content=existing.get("body"),
            )
        except HTTPException:
            raise
        except (json.JSONDecodeError, TypeError, ValueError):
            # If cache value is corrupted, ignore and proceed with lock path.
            pass

    owner = await cache.acquire_lock(lock_resource, ttl_seconds=lock_ttl_seconds)
    if not owner:
        # Another worker is in progress; return cached result if it appears, else tell client to retry.
        existing_raw = await cache.get(record_key)
        if existing_raw:
            existing = json.loads(existing_raw)
            if existing.get("request_hash") != req_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key_reuse_different_payload",
                )
            return JSONResponse(
                status_code=int(existing.get("status_code", 200)),
                content=existing.get("body"),
            )
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="idempotency_in_progress")

    try:
        # Re-check under lock (avoid double execution).
        existing_raw = await cache.get(record_key)
        if existing_raw:
            existing = json.loads(existing_raw)
            if existing.get("request_hash") != req_hash:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="idempotency_key_reuse_different_payload",
                )
            return JSONResponse(
                status_code=int(existing.get("status_code", 200)),
                content=existing.get("body"),
            )

        status_code, body = await fn()
        record = IdempotencyRecord(status_code=status_code, body=jsonable_encoder(body), request_hash=req_hash)
        await cache.set(record_key, json.dumps(record.__dict__, default=str), ttl=ttl_seconds)
        return JSONResponse(status_code=status_code, content=record.body)
    finally:
        await cache.release_lock(lock_resource, owner)

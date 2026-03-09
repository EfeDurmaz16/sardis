"""Idempotency helpers for fintech-safe endpoints.

Uses Redis as primary fast path with DB write-through for durability.
Falls back to DB when Redis is unavailable.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from sardis_api.authz import Principal

_logger = logging.getLogger("sardis.api.idempotency")


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


def get_idempotency_key(request: Request) -> str | None:
    for header in IDEMPOTENCY_HEADERS:
        value = request.headers.get(header)
        if value:
            return value.strip()
    return None


def _cache_key(*parts: str) -> str:
    safe = [p.replace(":", "_") for p in parts]
    return "sardis:idem:" + ":".join(safe)


async def _db_get_idempotency(key: str) -> dict | None:
    """Fallback: read idempotency record from DB."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT response_status, response_body
                FROM idempotency_records
                WHERE idempotency_key = $1 AND expires_at > now()
                """,
                key,
            )
            if row:
                return {
                    "status_code": row["response_status"],
                    "body": row["response_body"] if isinstance(row["response_body"], dict) else json.loads(row["response_body"]),
                }
    except Exception as e:
        _logger.debug("DB idempotency lookup failed for key=%s: %s", key, e)
    return None


async def _db_set_idempotency(key: str, status_code: int, body: Any) -> None:
    """Write-through: persist idempotency record to DB."""
    try:
        from sardis_v2_core.database import get_pool

        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO idempotency_records (idempotency_key, response_status, response_body)
                VALUES ($1, $2, $3::jsonb)
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                key,
                status_code,
                json.dumps(jsonable_encoder(body), default=str),
            )
    except Exception as e:
        _logger.warning("DB idempotency write-through failed for key=%s: %s", key, e)


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
    req_hash = _hash_payload(payload)
    record_key = _cache_key(principal.organization_id, operation, key, "record")
    db_key = f"{principal.organization_id}:{operation}:{key}"

    if cache is None:
        # No Redis — use DB-only path
        db_record = await _db_get_idempotency(db_key)
        if db_record:
            return JSONResponse(
                status_code=db_record["status_code"],
                content=db_record["body"],
            )
        status_code, body = await fn()
        await _db_set_idempotency(db_key, status_code, body)
        return JSONResponse(status_code=status_code, content=jsonable_encoder(body))

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
    else:
        # Redis miss — check DB fallback
        db_record = await _db_get_idempotency(db_key)
        if db_record:
            return JSONResponse(
                status_code=db_record["status_code"],
                content=db_record["body"],
            )

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
        # Write-through to DB for durability
        await _db_set_idempotency(db_key, status_code, body)
        return JSONResponse(status_code=status_code, content=record.body)
    finally:
        await cache.release_lock(lock_resource, owner)

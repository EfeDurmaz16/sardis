"""
Durable deduplication store for mandate execution.

Provides cross-instance duplicate detection to prevent double-payments
when multiple orchestrator instances run behind a load balancer.

Two implementations:
  - RedisDedupStore: production-grade, Redis-backed, with configurable TTL.
  - InMemoryDedupStore: development fallback, process-local only.

Usage:
    store = RedisDedupStore(redis_client, ttl_seconds=86_400)
    existing = await store.check_and_set("mdt_123", result_dict)
    if existing is not None:
        return existing  # duplicate blocked

IMPORTANT: The in-memory store does NOT protect against duplicate mandates
across instances.  Always use RedisDedupStore in production.
"""
from __future__ import annotations

import dataclasses
import json
import logging
from typing import Any, Protocol

logger = logging.getLogger(__name__)

KEY_PREFIX = "sardis:dedup:"
# Marker so a stored value can be rehydrated into the exact result type on read,
# keeping RedisDedupStore interchangeable with InMemoryDedupStore (which returns
# the original object).  Without this a Redis hit returned a raw string/dict and
# callers crashed on ``result.chain_tx_hash``.
_TYPE_KEY = "__sardis_dedup_type__"
_DATA_KEY = "__sardis_dedup_data__"
# Placeholder written by ``reserve`` before a result exists. ``check`` returns
# None for it (reserved, not yet completed) rather than treating it as a result.
_RESERVED_PLACEHOLDER = "__reserved__"


def _encode_result(result: Any) -> str:
    """JSON-encode a dedup result, tagging dataclasses for rehydration.

    A :class:`~sardis.core.orchestrator.PaymentResult` (a dataclass) is stored
    as ``{_TYPE_KEY: "PaymentResult", _DATA_KEY: {...fields...}}`` so ``check``
    can reconstruct it.  Plain dicts (used in tests / non-typed callers) are
    stored as-is.
    """
    if dataclasses.is_dataclass(result) and not isinstance(result, type):
        return json.dumps(
            {_TYPE_KEY: type(result).__name__, _DATA_KEY: dataclasses.asdict(result)},
            default=str,
        )
    return json.dumps(result, default=str)


def _decode_result(raw: str) -> Any:
    """Decode a stored dedup value, rehydrating tagged dataclasses.

    Returns a reconstructed :class:`PaymentResult` when the stored value was a
    tagged ``PaymentResult``; otherwise returns the decoded JSON unchanged.
    A bare reservation placeholder (no result yet) decodes to ``None``.
    """
    if raw == _RESERVED_PLACEHOLDER:
        return None
    decoded = json.loads(raw)
    if isinstance(decoded, dict) and decoded.get(_TYPE_KEY) == "PaymentResult":
        # Lazy import avoids a circular dependency with orchestrator.py.
        from sardis.core.orchestrator import FastPathResult, PaymentResult

        data = dict(decoded.get(_DATA_KEY) or {})
        fastpath = data.get("fastpath")
        if isinstance(fastpath, dict):
            data["fastpath"] = FastPathResult(**fastpath)
        return PaymentResult(**data)
    return decoded


class DedupStorePort(Protocol):
    """Port for mandate deduplication stores."""

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        ...

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None (read-only)."""
        ...

    async def reserve(self, mandate_id: str) -> bool:
        """Atomically reserve a mandate_id before dispatch.

        Returns ``True`` if this caller won the reservation, ``False`` if it
        was already reserved (another worker is dispatching).  Prevents
        duplicate *executions* under concurrency (the pre-dispatch check/store
        window is not atomic on its own).
        """
        ...

    async def release(self, mandate_id: str) -> None:
        """Release a reservation that did NOT settle (so a retry isn't blocked).

        Only removes a bare reservation placeholder — a key already finalized
        with a real result is left intact (that IS a completed payment).
        """
        ...


class RedisDedupStore:
    """
    Redis-backed mandate deduplication.  Fail-closed.

    Uses a simple GET/SET pattern with a TTL.  The key format is
    ``sardis:dedup:{mandate_id}`` and the value is the JSON-serialised
    payment result.

    Args:
        redis_client: An async Redis client (e.g. ``redis.asyncio.Redis``).
        ttl_seconds: How long to keep dedup entries (default 24 h).
    """

    def __init__(self, redis_client: Any, ttl_seconds: int = 86_400) -> None:
        self._redis = redis_client
        self._ttl = ttl_seconds

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None."""
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            existing = await self._redis.get(key)
            if existing is not None:
                return _decode_result(existing)
            return None
        except Exception:
            # Fail-closed: if Redis is unreachable we cannot confirm uniqueness.
            # Raising lets the caller decide (orchestrator will reject).
            logger.exception("Redis dedup check failed for mandate=%s", mandate_id)
            raise

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            existing = await self._redis.get(key)
            # A bare reservation placeholder means THIS worker reserved the key
            # and is now finalizing — overwrite it with the real result rather
            # than treating the reservation as a completed duplicate.
            if existing is not None and existing != _RESERVED_PLACEHOLDER:
                logger.warning("Duplicate mandate detected via Redis: %s", mandate_id)
                return _decode_result(existing)
            await self._redis.set(key, _encode_result(result), ex=self._ttl)
            return None
        except Exception:
            # Fail-closed: if Redis is unreachable we cannot confirm uniqueness.
            logger.exception("Redis dedup check_and_set failed for mandate=%s", mandate_id)
            raise

    async def reserve(self, mandate_id: str) -> bool:
        """Atomically reserve a mandate before dispatch via Redis ``SET NX``.

        ``SET key value NX EX ttl`` sets the key only if it does not exist,
        returning a truthy reply when set and ``None`` when the key already
        existed.  This is the atomic gate that prevents two workers from both
        passing the (non-atomic) pre-dispatch ``check`` and double-settling.
        The placeholder value is overwritten by ``check_and_set`` with the real
        result after settlement.
        """
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            # ``nx=True`` => only set if absent; redis-py returns True or None.
            ok = await self._redis.set(key, _RESERVED_PLACEHOLDER, nx=True, ex=self._ttl)
            return bool(ok)
        except Exception:
            logger.exception("Redis dedup reserve failed for mandate=%s", mandate_id)
            raise

    async def release(self, mandate_id: str) -> None:
        """Delete a bare reservation so a failed dispatch can be retried.

        Leaves a finalized result intact (only the reservation placeholder is
        removed).  Best-effort: a release failure is logged, not raised, since
        the TTL is the safety net.
        """
        key = f"{KEY_PREFIX}{mandate_id}"
        try:
            existing = await self._redis.get(key)
            if existing == _RESERVED_PLACEHOLDER:
                await self._redis.delete(key)
        except Exception:
            logger.warning(
                "Redis dedup release failed for mandate=%s (TTL will expire it)",
                mandate_id,
            )


class InMemoryDedupStore:
    """
    In-memory dedup for development.  NOT suitable for production.

    Process-local dict — duplicates sent to different instances will
    not be caught.
    """

    def __init__(self) -> None:
        import os

        env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "development")).strip().lower()
        if env in ("production", "prod", "staging"):
            raise RuntimeError(
                "InMemoryDedupStore is NOT suitable for production. "
                "Duplicate mandates across instances WILL cause double-payments. "
                "Set dedup_store= to a RedisDedupStore."
            )
        logger.warning(
            "Using InMemoryDedupStore — duplicates across instances will not be caught. "
            "Not suitable for production."
        )
        self._store: dict[str, Any] = {}
        # Reservations are tracked separately from stored results so that a
        # pre-dispatch reserve() does NOT make check() report a (non-existent)
        # completed result.
        self._reserved: set[str] = set()

    async def check(self, mandate_id: str) -> Any | None:
        """Return existing result if present, else None."""
        return self._store.get(mandate_id)

    async def check_and_set(self, mandate_id: str, result: Any) -> Any | None:
        """Return existing result if duplicate, else store and return None."""
        if mandate_id in self._store:
            return self._store[mandate_id]
        self._store[mandate_id] = result
        return None

    async def reserve(self, mandate_id: str) -> bool:
        """Atomically reserve a mandate before dispatch (process-local).

        Returns ``True`` if newly reserved, ``False`` if already reserved or
        already has a stored result.  Single-threaded asyncio makes this
        check-and-set atomic within the process; it does NOT protect across
        instances (use RedisDedupStore in production).
        """
        if mandate_id in self._reserved or mandate_id in self._store:
            return False
        self._reserved.add(mandate_id)
        return True

    async def release(self, mandate_id: str) -> None:
        """Release a reservation that did not settle (so a retry isn't blocked)."""
        self._reserved.discard(mandate_id)

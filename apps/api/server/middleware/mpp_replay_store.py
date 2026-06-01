"""Replay-protection Store for the MPP gate.

pympp's ``mpp.store.Store`` Protocol (``get`` / ``put`` / ``delete`` /
``put_if_absent``) is how ``ChargeIntent`` deduplicates settled transaction
hashes: each verified tx hash is recorded with ``put_if_absent`` and any
subsequent attempt to reuse it is rejected. Without a store, a single settled
Tempo transaction can be replayed across unlimited paid requests — i.e.
"charged once, served forever."

This adapter backs that Protocol with Sardis's existing cache backend
(``sardis.core.cache.CacheBackend``), whose ``acquire_lock`` is an atomic
SETNX (`SET ... NX EX` on Redis, dict check-and-set in memory). We reuse it so
the gate's replay protection is durable across processes when Redis is wired
and degrades to in-memory only in dev.

Fail-closed: if the backend errors, ``acquire_lock`` returns ``False`` →
``put_if_absent`` returns ``False`` → pympp treats the hash as a duplicate and
rejects the credential. On the money path, a store we cannot trust must reject,
never re-grant access.
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Replayed tx hashes are kept for this long. A Tempo settlement is final well
# inside this window; keeping the key bounded avoids unbounded growth while
# covering any plausible retry/replay attempt against the same challenge.
_REPLAY_TTL_SECONDS = 86_400  # 24h


class CacheBackedReplayStore:
    """Adapts ``sardis.core.cache.CacheBackend`` to the ``mpp.store.Store`` Protocol."""

    __slots__ = ("_backend", "_ttl")

    def __init__(self, backend: Any, ttl_seconds: int = _REPLAY_TTL_SECONDS) -> None:
        self._backend = backend
        self._ttl = ttl_seconds

    async def get(self, key: str) -> Any | None:
        try:
            return await self._backend.get(key)
        except Exception as exc:  # pragma: no cover - backend error path
            logger.error("MPP replay store get failed for %s: %s", key, exc)
            return None

    async def put(self, key: str, value: Any) -> None:
        try:
            await self._backend.set(key, str(value), ttl=self._ttl)
        except Exception as exc:  # pragma: no cover - backend error path
            logger.error("MPP replay store put failed for %s: %s", key, exc)

    async def delete(self, key: str) -> None:
        try:
            await self._backend.delete(key)
        except Exception as exc:  # pragma: no cover - backend error path
            logger.error("MPP replay store delete failed for %s: %s", key, exc)

    async def put_if_absent(self, key: str, value: Any) -> bool:
        """Atomic first-writer-wins. ``True`` if newly stored, ``False`` if it existed.

        Backed by the cache's atomic SETNX (``acquire_lock``). A backend error
        yields ``False`` (treated as a duplicate by pympp → credential rejected),
        which is the fail-closed choice for replay protection.
        """
        try:
            return bool(await self._backend.acquire_lock(key, ttl=self._ttl, owner=str(value)))
        except Exception as exc:  # pragma: no cover - backend error path
            logger.error("MPP replay store put_if_absent failed for %s: %s", key, exc)
            return False


__all__ = ["CacheBackedReplayStore"]

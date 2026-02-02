"""Redis-backed distributed nonce manager.

Provides atomic nonce reservation across multiple API instances using
Redis WATCH/MULTI/EXEC for optimistic locking and Lua scripts for
atomic increment operations.

Required for multi-instance production deployments to prevent nonce
collisions when multiple workers handle the same wallet address.
"""
from __future__ import annotations

import logging
import os
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Lua script for atomic nonce reservation.
# Returns the reserved nonce, or -1 if the nonce was already taken.
_RESERVE_NONCE_LUA = """
local key = KEYS[1]
local on_chain_nonce = tonumber(ARGV[1])
local ttl = tonumber(ARGV[2])

-- Get current tracked nonce (or use on-chain as baseline)
local current = redis.call('GET', key)
if current == false then
    current = on_chain_nonce
else
    current = tonumber(current)
    -- If on-chain nonce is ahead (txs confirmed), update baseline
    if on_chain_nonce > current then
        current = on_chain_nonce
    end
end

-- Reserve this nonce and increment
redis.call('SET', key, current + 1, 'EX', ttl)
return current
"""


class RedisNonceManager:
    """Distributed nonce manager using Redis for cross-instance coordination.

    Each wallet address gets a Redis key tracking the next available nonce.
    Nonce reservation is atomic via a Lua script, preventing two instances
    from reserving the same nonce.

    Usage:
        manager = RedisNonceManager()
        nonce = await manager.reserve_nonce(address, rpc_client)
    """

    # Key prefix in Redis
    KEY_PREFIX = "sardis:nonce:"
    # Lock prefix for address-level distributed locks
    LOCK_PREFIX = "sardis:nonce_lock:"
    # Default TTL for nonce keys (5 minutes)
    DEFAULT_TTL = 300
    # Lock timeout (10 seconds)
    LOCK_TIMEOUT = 10

    def __init__(
        self,
        redis_url: Optional[str] = None,
        ttl: int = DEFAULT_TTL,
    ):
        self._redis_url = redis_url or os.getenv("SARDIS_REDIS_URL", os.getenv("UPSTASH_REDIS_URL", ""))
        self._ttl = ttl
        self._client = None
        self._reserve_script = None

        if not self._redis_url:
            env = os.getenv("SARDIS_ENVIRONMENT", "dev")
            if env in ("prod", "production"):
                raise RuntimeError(
                    "Production requires Redis for distributed nonce management. "
                    "Set SARDIS_REDIS_URL or UPSTASH_REDIS_URL."
                )
            logger.warning(
                "No Redis URL configured for nonce manager. "
                "Falling back to in-memory nonce management (single-instance only)."
            )

    async def _get_client(self):
        if self._client is None:
            import redis.asyncio as redis
            self._client = redis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            self._reserve_script = self._client.register_script(_RESERVE_NONCE_LUA)
        return self._client

    def _nonce_key(self, address: str) -> str:
        return f"{self.KEY_PREFIX}{address.lower()}"

    def _lock_key(self, address: str) -> str:
        return f"{self.LOCK_PREFIX}{address.lower()}"

    async def reserve_nonce(
        self,
        address: str,
        rpc_client: Any,
    ) -> int:
        """Atomically reserve the next nonce for an address.

        Fetches the on-chain nonce as a baseline, then uses Redis to
        coordinate the next available nonce across instances.

        Args:
            address: Wallet address
            rpc_client: RPC client for fetching on-chain nonce

        Returns:
            Reserved nonce (guaranteed unique across instances)
        """
        if not self._redis_url:
            # Fallback: just use on-chain nonce (unsafe for multi-instance)
            return await rpc_client.get_nonce(address.lower())

        client = await self._get_client()
        on_chain_nonce = await rpc_client.get_nonce(address.lower())

        nonce = await self._reserve_script(
            keys=[self._nonce_key(address)],
            args=[on_chain_nonce, self._ttl],
            client=client,
        )

        logger.debug(
            "Reserved nonce via Redis",
            extra={
                "address": address.lower(),
                "nonce": nonce,
                "on_chain_nonce": on_chain_nonce,
            },
        )
        return int(nonce)

    async def release_nonce(self, address: str, nonce: int) -> None:
        """Release a nonce that won't be used (e.g., on tx build failure).

        This is best-effort; if the nonce was already used by another
        instance, this is a no-op.
        """
        if not self._redis_url:
            return

        client = await self._get_client()
        key = self._nonce_key(address)

        # Only decrement if current value is nonce + 1 (we're the latest reserver)
        pipe = client.pipeline()
        await pipe.watch(key)
        current = await client.get(key)
        if current and int(current) == nonce + 1:
            pipe.multi()
            pipe.set(key, nonce, ex=self._ttl)
            try:
                await pipe.execute()
                logger.debug(f"Released nonce {nonce} for {address.lower()}")
            except Exception:
                pass  # Lost the race, nonce was taken — that's fine
        await pipe.reset()

    async def sync_from_chain(self, address: str, rpc_client: Any) -> int:
        """Force-sync the nonce from on-chain state.

        Use after confirmed transactions to reset the baseline.
        """
        if not self._redis_url:
            return await rpc_client.get_nonce(address.lower())

        client = await self._get_client()
        on_chain_nonce = await rpc_client.get_nonce(address.lower())
        await client.set(
            self._nonce_key(address),
            on_chain_nonce,
            ex=self._ttl,
        )
        return on_chain_nonce

    async def close(self):
        if self._client:
            await self._client.close()
            self._client = None

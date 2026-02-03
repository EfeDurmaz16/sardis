"""Unit tests for RedisNonceManager."""
from __future__ import annotations

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from sardis_chain.redis_nonce_manager import RedisNonceManager


class MockRPCClient:
    """Mock RPC client for testing."""

    def __init__(self, nonce: int = 0):
        self._nonce = nonce

    async def get_nonce(self, address: str) -> int:
        """Return mock nonce."""
        return self._nonce

    def set_nonce(self, nonce: int):
        """Update mock nonce."""
        self._nonce = nonce


class MockRedisClient:
    """Mock Redis client for testing."""

    def __init__(self):
        self._store: dict[str, str] = {}
        self._scripts: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        """Get value from store."""
        return self._store.get(key)

    async def set(self, key: str, value: str | int, ex: int = None) -> bool:
        """Set value in store."""
        self._store[key] = str(value)
        return True

    async def delete(self, key: str) -> int:
        """Delete key from store."""
        if key in self._store:
            del self._store[key]
            return 1
        return 0

    def register_script(self, script: str):
        """Register a Lua script."""
        script_id = str(len(self._scripts))
        self._scripts[script_id] = script

        async def execute(keys, args, client):
            # Simulate the Lua script behavior
            key = keys[0]
            on_chain_nonce = int(args[0])
            ttl = int(args[1])

            current = self._store.get(key)
            if current is None:
                current = on_chain_nonce
            else:
                current = int(current)
                if on_chain_nonce > current:
                    current = on_chain_nonce

            # Reserve and increment
            self._store[key] = str(current + 1)
            return current

        return execute

    def pipeline(self):
        """Create a pipeline for transaction."""
        return MockPipeline(self)

    async def close(self):
        """Close connection."""
        pass


class MockPipeline:
    """Mock Redis pipeline for transactions."""

    def __init__(self, client: MockRedisClient):
        self._client = client
        self._watching = None
        self._commands = []

    async def watch(self, key: str):
        """Watch a key for changes."""
        self._watching = key
        return True

    async def get(self, key: str):
        """Get in pipeline context."""
        return self._client._store.get(key)

    def multi(self):
        """Start transaction."""
        pass

    def set(self, key: str, value: str | int, ex: int = None):
        """Queue set command."""
        self._commands.append(("set", key, str(value)))

    async def execute(self):
        """Execute queued commands."""
        for cmd in self._commands:
            if cmd[0] == "set":
                self._client._store[cmd[1]] = cmd[2]
        self._commands = []
        return [True]

    async def reset(self):
        """Reset pipeline."""
        self._watching = None
        self._commands = []


class TestRedisNonceManager:
    """Test RedisNonceManager."""

    @pytest.mark.asyncio
    async def test_init_without_redis_url(self):
        """Test initialization without Redis URL (dev mode)."""
        with patch.dict("os.environ", {"SARDIS_ENVIRONMENT": "dev"}, clear=False):
            manager = RedisNonceManager(redis_url=None)
            assert manager._redis_url == ""
            assert manager._client is None

    @pytest.mark.asyncio
    async def test_init_with_redis_url(self):
        """Test initialization with Redis URL."""
        manager = RedisNonceManager(redis_url="redis://localhost:6379")
        assert manager._redis_url == "redis://localhost:6379"
        assert manager._ttl == RedisNonceManager.DEFAULT_TTL

    @pytest.mark.asyncio
    async def test_init_production_without_redis(self):
        """Test that production requires Redis."""
        with patch.dict("os.environ", {"SARDIS_ENVIRONMENT": "production"}, clear=False):
            with pytest.raises(RuntimeError, match="Production requires Redis"):
                RedisNonceManager(redis_url=None)

    @pytest.mark.asyncio
    async def test_nonce_key_formatting(self):
        """Test nonce key formatting."""
        manager = RedisNonceManager(redis_url="redis://localhost")

        key = manager._nonce_key("0x1234ABCD")
        assert key == "sardis:nonce:0x1234abcd"

        key = manager._nonce_key("0xABCDEF")
        assert key == "sardis:nonce:0xabcdef"

    @pytest.mark.asyncio
    async def test_lock_key_formatting(self):
        """Test lock key formatting."""
        manager = RedisNonceManager(redis_url="redis://localhost")

        key = manager._lock_key("0x1234ABCD")
        assert key == "sardis:nonce_lock:0x1234abcd"

    @pytest.mark.asyncio
    async def test_reserve_nonce_without_redis(self):
        """Test nonce reservation falls back to on-chain when no Redis."""
        manager = RedisNonceManager(redis_url=None)
        rpc_client = MockRPCClient(nonce=5)

        nonce = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce == 5

    @pytest.mark.asyncio
    async def test_reserve_nonce_with_redis_first_time(self):
        """Test nonce reservation with Redis (first reservation)."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=10)

        # First reservation should use on-chain nonce as baseline
        nonce = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce == 10

        # Check that next nonce is tracked in Redis
        stored = await manager._client.get("sardis:nonce:0x1234")
        assert stored == "11"

    @pytest.mark.asyncio
    async def test_reserve_nonce_sequential(self):
        """Test sequential nonce reservations."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve first nonce
        nonce1 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce1 == 5

        # Reserve second nonce (should increment)
        nonce2 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce2 == 6

        # Reserve third nonce
        nonce3 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce3 == 7

    @pytest.mark.asyncio
    async def test_reserve_nonce_on_chain_ahead(self):
        """Test nonce reservation when on-chain nonce is ahead (tx confirmed)."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve first nonce
        nonce1 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce1 == 5

        # Simulate on-chain nonce advancing (tx confirmed)
        rpc_client.set_nonce(10)

        # Next reservation should use updated on-chain nonce
        nonce2 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce2 == 10

    @pytest.mark.asyncio
    async def test_reserve_nonce_multiple_addresses(self):
        """Test that different addresses have independent nonce tracking."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client1 = MockRPCClient(nonce=5)
        rpc_client2 = MockRPCClient(nonce=20)

        # Reserve for address 1
        nonce1 = await manager.reserve_nonce("0xAAAA", rpc_client1)
        assert nonce1 == 5

        # Reserve for address 2 (should be independent)
        nonce2 = await manager.reserve_nonce("0xBBBB", rpc_client2)
        assert nonce2 == 20

        # Reserve again for address 1 (should continue from 5)
        nonce3 = await manager.reserve_nonce("0xAAAA", rpc_client1)
        assert nonce3 == 6

    @pytest.mark.asyncio
    async def test_release_nonce_without_redis(self):
        """Test release_nonce is no-op without Redis."""
        manager = RedisNonceManager(redis_url=None)

        # Should not raise
        await manager.release_nonce("0x1234", 5)

    @pytest.mark.asyncio
    async def test_release_nonce_success(self):
        """Test successful nonce release."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve a nonce
        nonce = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce == 5

        # Release it
        await manager.release_nonce("0x1234", 5)

        # Next reservation should re-use the released nonce
        nonce2 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce2 == 5

    @pytest.mark.asyncio
    async def test_release_nonce_stale(self):
        """Test releasing a stale nonce (already used)."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve two nonces
        nonce1 = await manager.reserve_nonce("0x1234", rpc_client)
        nonce2 = await manager.reserve_nonce("0x1234", rpc_client)

        # Try to release the first one (stale, won't decrement)
        await manager.release_nonce("0x1234", nonce1)

        # Next nonce should be 7 (not affected by stale release)
        nonce3 = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce3 == 7

    @pytest.mark.asyncio
    async def test_sync_from_chain_without_redis(self):
        """Test sync_from_chain without Redis."""
        manager = RedisNonceManager(redis_url=None)
        rpc_client = MockRPCClient(nonce=15)

        nonce = await manager.sync_from_chain("0x1234", rpc_client)
        assert nonce == 15

    @pytest.mark.asyncio
    async def test_sync_from_chain_with_redis(self):
        """Test sync_from_chain updates Redis state."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve some nonces
        await manager.reserve_nonce("0x1234", rpc_client)
        await manager.reserve_nonce("0x1234", rpc_client)

        # Simulate on-chain state advancing
        rpc_client.set_nonce(20)

        # Force sync
        synced_nonce = await manager.sync_from_chain("0x1234", rpc_client)
        assert synced_nonce == 20

        # Next reservation should continue from synced state
        nonce = await manager.reserve_nonce("0x1234", rpc_client)
        assert nonce == 20

    @pytest.mark.asyncio
    async def test_close_client(self):
        """Test closing Redis client."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()

        await manager.close()
        assert manager._client is None

    @pytest.mark.asyncio
    async def test_close_without_client(self):
        """Test closing when no client exists."""
        manager = RedisNonceManager(redis_url="redis://localhost")

        # Should not raise
        await manager.close()

    @pytest.mark.asyncio
    async def test_custom_ttl(self):
        """Test custom TTL configuration."""
        manager = RedisNonceManager(redis_url="redis://localhost", ttl=600)
        assert manager._ttl == 600

    @pytest.mark.asyncio
    async def test_concurrent_reservations(self):
        """Test concurrent nonce reservations don't collide."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=10)

        # Simulate concurrent reservations
        tasks = [
            manager.reserve_nonce("0x1234", rpc_client)
            for _ in range(5)
        ]
        nonces = await asyncio.gather(*tasks)

        # All nonces should be unique
        assert len(set(nonces)) == 5
        assert min(nonces) == 10
        assert max(nonces) == 14

    @pytest.mark.asyncio
    async def test_address_normalization(self):
        """Test that addresses are normalized to lowercase."""
        manager = RedisNonceManager(redis_url="redis://localhost")
        manager._client = MockRedisClient()
        manager._reserve_script = manager._client.register_script("")

        rpc_client = MockRPCClient(nonce=5)

        # Reserve with uppercase address
        nonce1 = await manager.reserve_nonce("0xABCD1234", rpc_client)

        # Reserve with lowercase (should be same address)
        nonce2 = await manager.reserve_nonce("0xabcd1234", rpc_client)

        # Should be sequential (same address)
        assert nonce1 == 5
        assert nonce2 == 6

    @pytest.mark.asyncio
    async def test_environment_variable_redis_url(self):
        """Test Redis URL from environment variables."""
        with patch.dict("os.environ", {"UPSTASH_REDIS_URL": "redis://upstash:6379"}, clear=False):
            manager = RedisNonceManager()
            assert manager._redis_url == "redis://upstash:6379"

    @pytest.mark.asyncio
    async def test_sardis_redis_url_priority(self):
        """Test SARDIS_REDIS_URL takes priority over UPSTASH_REDIS_URL."""
        with patch.dict(
            "os.environ",
            {
                "SARDIS_REDIS_URL": "redis://sardis:6379",
                "UPSTASH_REDIS_URL": "redis://upstash:6379",
            },
            clear=False,
        ):
            manager = RedisNonceManager()
            assert manager._redis_url == "redis://sardis:6379"

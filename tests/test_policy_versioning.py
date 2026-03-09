"""Tests for policy versioning — immutable audit trail for policy changes."""
from __future__ import annotations

import json

import pytest
from sardis_v2_core.policy_version_store import (
    PolicyVersionStore,
    compute_policy_hash,
)

# ============ Hash Tests ============


def test_hash_determinism():
    """Same policy dict always produces the same hash."""
    policy = {"limit_per_tx": "500.00", "daily": "1000.00", "blocked": ["gambling"]}
    h1 = compute_policy_hash(policy)
    h2 = compute_policy_hash(policy)
    assert h1 == h2
    assert len(h1) == 64  # SHA-256 hex


def test_hash_key_order_independence():
    """Hash is the same regardless of key insertion order."""
    p1 = {"b": 2, "a": 1}
    p2 = {"a": 1, "b": 2}
    assert compute_policy_hash(p1) == compute_policy_hash(p2)


def test_hash_different_policies():
    """Different policies produce different hashes."""
    p1 = {"limit_per_tx": "500.00"}
    p2 = {"limit_per_tx": "1000.00"}
    assert compute_policy_hash(p1) != compute_policy_hash(p2)


def test_hash_nested_objects():
    """Hash works correctly for nested dicts/lists."""
    p1 = {"rules": [{"type": "allow", "merchant": "aws"}], "meta": {"v": 1}}
    p2 = {"rules": [{"type": "allow", "merchant": "aws"}], "meta": {"v": 1}}
    assert compute_policy_hash(p1) == compute_policy_hash(p2)

    p3 = {"rules": [{"type": "deny", "merchant": "aws"}], "meta": {"v": 1}}
    assert compute_policy_hash(p1) != compute_policy_hash(p3)


# ============ Mock Pool Helpers ============


class MockPool:
    """Minimal mock for asyncpg pool used in version store tests."""

    def __init__(self):
        self._rows: list[dict] = []

    def acquire(self):
        return MockConnection(self)


class _MockTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


class MockConnection:
    def __init__(self, pool: MockPool):
        self._pool = pool

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass

    def transaction(self):
        return _MockTransaction()

    async def fetchrow(self, query: str, *args):
        agent_id = args[0] if args else None
        if "ORDER BY version DESC LIMIT 1" in query:  # matches both with and without FOR UPDATE
            # get_latest or create_version: find latest for agent
            matching = [r for r in self._pool._rows if r["agent_id"] == agent_id]
            if matching:
                return max(matching, key=lambda r: r["version"])
            return None
        if "version = $2" in query:
            # get_version: exact match
            version = args[1] if len(args) > 1 else None
            for r in self._pool._rows:
                if r["agent_id"] == agent_id and r["version"] == version:
                    return r
            return None
        return None

    async def fetch(self, query: str, *args):
        agent_id = args[0] if args else None
        limit = args[1] if len(args) > 1 else 20
        matching = [r for r in self._pool._rows if r["agent_id"] == agent_id]
        matching.sort(key=lambda r: r["version"], reverse=True)
        return matching[:limit]

    async def execute(self, query: str, *args):
        if "INSERT INTO policy_versions" in query:
            row = {
                "id": args[0],
                "agent_id": args[1],
                "version": args[2],
                "policy_json": json.loads(args[3]) if isinstance(args[3], str) else args[3],
                "policy_text": args[4],
                "created_at": args[5],
                "created_by": args[6],
                "parent_version_id": args[7],
                "hash": args[8],
            }
            self._pool._rows.append(row)


# ============ Version Store Tests ============


@pytest.mark.asyncio
async def test_create_first_version():
    pool = MockPool()
    store = PolicyVersionStore()
    policy = {"limit_per_tx": "500.00", "daily": "1000.00"}

    v = await store.create_version(pool, "agent_1", policy, "max $500/tx", "admin")

    assert v.agent_id == "agent_1"
    assert v.version == 1
    assert v.policy_json == policy
    assert v.policy_text == "max $500/tx"
    assert v.created_by == "admin"
    assert v.parent_version_id is None
    assert v.hash == compute_policy_hash(policy)
    assert v.id.startswith("pvr_")


@pytest.mark.asyncio
async def test_version_auto_increment():
    pool = MockPool()
    store = PolicyVersionStore()

    v1 = await store.create_version(pool, "agent_1", {"v": 1})
    v2 = await store.create_version(pool, "agent_1", {"v": 2})
    v3 = await store.create_version(pool, "agent_1", {"v": 3})

    assert v1.version == 1
    assert v2.version == 2
    assert v3.version == 3


@pytest.mark.asyncio
async def test_parent_chain_integrity():
    pool = MockPool()
    store = PolicyVersionStore()

    v1 = await store.create_version(pool, "agent_1", {"v": 1})
    v2 = await store.create_version(pool, "agent_1", {"v": 2})
    v3 = await store.create_version(pool, "agent_1", {"v": 3})

    assert v1.parent_version_id is None
    assert v2.parent_version_id == v1.id
    assert v3.parent_version_id == v2.id


@pytest.mark.asyncio
async def test_get_version():
    pool = MockPool()
    store = PolicyVersionStore()
    await store.create_version(pool, "agent_1", {"v": 1})
    await store.create_version(pool, "agent_1", {"v": 2})

    v = await store.get_version(pool, "agent_1", 1)
    assert v is not None
    assert v.version == 1
    assert v.policy_json == {"v": 1}

    missing = await store.get_version(pool, "agent_1", 99)
    assert missing is None


@pytest.mark.asyncio
async def test_get_latest():
    pool = MockPool()
    store = PolicyVersionStore()
    await store.create_version(pool, "agent_1", {"v": 1})
    await store.create_version(pool, "agent_1", {"v": 2})
    await store.create_version(pool, "agent_1", {"v": 3})

    latest = await store.get_latest(pool, "agent_1")
    assert latest is not None
    assert latest.version == 3

    # Different agent has no versions
    none_result = await store.get_latest(pool, "agent_other")
    assert none_result is None


@pytest.mark.asyncio
async def test_list_versions():
    pool = MockPool()
    store = PolicyVersionStore()
    for i in range(5):
        await store.create_version(pool, "agent_1", {"v": i + 1})

    versions = await store.list_versions(pool, "agent_1", limit=3)
    assert len(versions) == 3
    assert versions[0].version == 5  # newest first
    assert versions[2].version == 3


@pytest.mark.asyncio
async def test_diff_versions():
    pool = MockPool()
    store = PolicyVersionStore()
    await store.create_version(pool, "agent_1", {
        "limit_per_tx": "500.00",
        "daily": "1000.00",
        "blocked": ["gambling"],
    })
    await store.create_version(pool, "agent_1", {
        "limit_per_tx": "200.00",
        "daily": "1000.00",
        "blocked": ["gambling", "adult"],
        "new_field": True,
    })

    diff = await store.diff_versions(pool, "agent_1", 1, 2)
    assert diff["from_version"] == 1
    assert diff["to_version"] == 2
    assert "limit_per_tx" in diff["changed"]
    assert diff["changed"]["limit_per_tx"]["from"] == "500.00"
    assert diff["changed"]["limit_per_tx"]["to"] == "200.00"
    assert "new_field" in diff["added"]
    assert diff["added"]["new_field"] is True
    assert "blocked" in diff["changed"]


@pytest.mark.asyncio
async def test_diff_version_not_found():
    pool = MockPool()
    store = PolicyVersionStore()
    await store.create_version(pool, "agent_1", {"v": 1})

    with pytest.raises(ValueError, match="Version not found"):
        await store.diff_versions(pool, "agent_1", 1, 99)


@pytest.mark.asyncio
async def test_agents_have_independent_versions():
    pool = MockPool()
    store = PolicyVersionStore()

    v1_a = await store.create_version(pool, "agent_a", {"agent": "a"})
    v1_b = await store.create_version(pool, "agent_b", {"agent": "b"})

    assert v1_a.version == 1
    assert v1_b.version == 1

    v2_a = await store.create_version(pool, "agent_a", {"agent": "a", "v": 2})
    assert v2_a.version == 2

    latest_b = await store.get_latest(pool, "agent_b")
    assert latest_b.version == 1


@pytest.mark.asyncio
async def test_same_policy_same_hash():
    """Property: identical policy content always produces the same hash."""
    pool = MockPool()
    store = PolicyVersionStore()
    policy = {"limit": "100", "scope": "all"}

    v1 = await store.create_version(pool, "agent_1", policy)
    v2 = await store.create_version(pool, "agent_1", policy)

    assert v1.hash == v2.hash
    assert v1.version != v2.version  # different versions, same content


@pytest.mark.asyncio
async def test_create_version_no_text_no_creator():
    pool = MockPool()
    store = PolicyVersionStore()

    v = await store.create_version(pool, "agent_1", {"simple": True})
    assert v.policy_text is None
    assert v.created_by is None

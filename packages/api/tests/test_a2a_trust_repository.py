from __future__ import annotations

import pytest

from sardis_api.repositories.a2a_trust_repository import A2ATrustRepository


class _FakeConn:
    def __init__(self, *, exists: bool = True):
        self.exists = exists
        self.executed_sql: list[str] = []

    async def execute(self, sql: str):
        self.executed_sql.append(sql)
        return "OK"

    async def fetchval(self, sql: str):
        self.executed_sql.append(sql)
        return self.exists


class _AcquireCtx:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    async def __aenter__(self):
        return self._conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakePool:
    def __init__(self, conn: _FakeConn):
        self._conn = conn

    def acquire(self):
        return _AcquireCtx(self._conn)


@pytest.mark.asyncio
async def test_a2a_trust_repo_memory_crud():
    repo = A2ATrustRepository(dsn="memory://")

    await repo.upsert_relation(
        organization_id="org_1",
        sender_agent_id="agent_a",
        recipient_agent_id="agent_b",
        metadata={"reason": "ops"},
    )

    table = await repo.get_trust_table("org_1")
    assert table["agent_a"] == {"agent_b"}

    deleted = await repo.delete_relation(
        organization_id="org_1",
        sender_agent_id="agent_a",
        recipient_agent_id="agent_b",
    )
    assert deleted is True

    table_after = await repo.get_trust_table("org_1")
    assert table_after == {}


@pytest.mark.asyncio
async def test_ensure_table_prod_requires_migration(monkeypatch):
    conn = _FakeConn(exists=False)
    repo = A2ATrustRepository(pool=_FakePool(conn), dsn="postgresql://example")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="a2a_trust_relations table not found"):
        await repo._ensure_table()


@pytest.mark.asyncio
async def test_ensure_table_dev_creates_table(monkeypatch):
    conn = _FakeConn(exists=False)
    repo = A2ATrustRepository(pool=_FakePool(conn), dsn="postgresql://example")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    await repo._ensure_table()

    assert any("CREATE TABLE IF NOT EXISTS a2a_trust_relations" in sql for sql in conn.executed_sql)

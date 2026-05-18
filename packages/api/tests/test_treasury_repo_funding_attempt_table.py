from __future__ import annotations

import pytest

from sardis_api.repositories.treasury_repository import TreasuryRepository


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
async def test_ensure_funding_attempt_table_prod_requires_migration(monkeypatch):
    conn = _FakeConn(exists=False)
    repo = TreasuryRepository(pool=_FakePool(conn), dsn="postgresql://example")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")

    with pytest.raises(RuntimeError, match="issuer_funding_attempts table not found"):
        await repo._ensure_funding_attempt_table()


@pytest.mark.asyncio
async def test_ensure_funding_attempt_table_dev_creates_table(monkeypatch):
    conn = _FakeConn(exists=False)
    repo = TreasuryRepository(pool=_FakePool(conn), dsn="postgresql://example")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")

    await repo._ensure_funding_attempt_table()

    assert any("CREATE TABLE IF NOT EXISTS issuer_funding_attempts" in sql for sql in conn.executed_sql)

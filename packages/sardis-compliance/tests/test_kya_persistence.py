from __future__ import annotations

from decimal import Decimal

import pytest

from sardis_compliance.kya import AgentManifest, InMemoryKYAStore, KYAService, create_kya_service


class _FakePersistentStore(InMemoryKYAStore):
    def __init__(self):
        super().__init__()
        self.ensure_loaded_calls = 0
        self.persisted: list[tuple[str, dict | None]] = []

    async def ensure_loaded(self):
        self.ensure_loaded_calls += 1

    async def persist_agent(self, agent_id: str, liveness=None):
        self.persisted.append((agent_id, liveness))


@pytest.mark.asyncio
async def test_register_agent_persists_state_when_store_supports_persistence():
    store = _FakePersistentStore()
    service = KYAService(store=store, liveness_timeout=30)

    result = await service.register_agent(
        AgentManifest(agent_id="agent_1", owner_id="org_1")
    )

    assert result.allowed is True
    assert store.ensure_loaded_calls >= 1
    assert store.persisted
    assert store.persisted[-1][0] == "agent_1"


@pytest.mark.asyncio
async def test_ping_async_persists_liveness_snapshot():
    store = _FakePersistentStore()
    service = KYAService(store=store, liveness_timeout=30)
    await service.register_agent(AgentManifest(agent_id="agent_2", owner_id="org_2"))

    await service.ping_async("agent_2")

    assert len(store.persisted) >= 2
    last_agent_id, liveness = store.persisted[-1]
    assert last_agent_id == "agent_2"
    assert isinstance(liveness, dict)
    assert int(liveness.get("ping_count", 0)) >= 1


@pytest.mark.asyncio
async def test_async_getters_load_persisted_state():
    store = _FakePersistentStore()
    manifest = AgentManifest(
        agent_id="agent_3",
        owner_id="org_3",
        max_budget_per_tx=Decimal("25.00"),
    )
    store.store_manifest(manifest)
    service = KYAService(store=store, liveness_timeout=30)

    got_manifest = await service.get_manifest_async("agent_3")

    assert got_manifest is not None
    assert got_manifest.agent_id == "agent_3"
    assert store.ensure_loaded_calls >= 1


def test_create_kya_service_requires_persistent_store_in_prod_when_enforced(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.setenv("SARDIS_KYA_ENFORCEMENT_ENABLED", "true")
    monkeypatch.setenv("DATABASE_URL", "")

    with pytest.raises(RuntimeError, match="requires PostgreSQL"):
        create_kya_service()


def test_create_kya_service_uses_inmemory_in_dev_without_database(monkeypatch):
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "dev")
    monkeypatch.setenv("DATABASE_URL", "")

    service = create_kya_service()

    assert isinstance(service, KYAService)
    assert isinstance(service._store, InMemoryKYAStore)

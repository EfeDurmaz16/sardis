from __future__ import annotations

import inspect
from datetime import datetime, timezone

from sardis_v2_core.agent_repository_postgres import PostgresAgentRepository
from sardis_v2_core.wallet_repository_postgres import PostgresWalletRepository


def test_postgres_agent_repo_create_accepts_kya_fields():
    sig = inspect.signature(PostgresAgentRepository.create)
    assert "kya_level" in sig.parameters
    assert "kya_status" in sig.parameters


def test_postgres_agent_repo_update_accepts_kya_fields():
    sig = inspect.signature(PostgresAgentRepository.update)
    assert "kya_level" in sig.parameters
    assert "kya_status" in sig.parameters


def test_agent_from_row_maps_kya_fields_from_metadata():
    now = datetime.now(timezone.utc)
    row = {
        "external_id": "agent_1",
        "name": "Agent One",
        "description": "test",
        "is_active": True,
        "created_at": now,
        "updated_at": now,
        "organization_external_id": "org_1",
        "metadata": {
            "owner_id": "org_1",
            "kya_level": "verified",
            "kya_status": "active",
            "spending_limits": {},
            "policy": {},
        },
    }

    agent = PostgresAgentRepository._agent_from_row(row, wallet_external_id=None)

    assert agent.kya_level == "verified"
    assert agent.kya_status == "active"


def test_postgres_agent_repo_exposes_batch_get_many():
    sig = inspect.signature(PostgresAgentRepository.get_many)
    assert "agent_ids" in sig.parameters


def test_postgres_wallet_repo_exposes_batch_get_many():
    sig = inspect.signature(PostgresWalletRepository.get_many)
    assert "wallet_ids" in sig.parameters

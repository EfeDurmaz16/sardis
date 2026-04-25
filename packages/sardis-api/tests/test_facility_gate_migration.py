from __future__ import annotations

import os
from pathlib import Path

import pytest

POSTGRES_TEST_DSN = os.getenv("SARDIS_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DSN,
    reason="Set SARDIS_TEST_POSTGRES_DSN to run Facility Gate Postgres migration tests",
)


def _alembic_config():
    from alembic.config import Config

    root = Path(__file__).resolve().parents[1]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "alembic"))
    config.set_main_option("sqlalchemy.url", POSTGRES_TEST_DSN or "")
    return config


def _sync_dsn() -> str:
    assert POSTGRES_TEST_DSN
    if POSTGRES_TEST_DSN.startswith("postgresql+asyncpg://"):
        return POSTGRES_TEST_DSN.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if POSTGRES_TEST_DSN.startswith("postgresql://"):
        return POSTGRES_TEST_DSN.replace("postgresql://", "postgresql+psycopg://", 1)
    return POSTGRES_TEST_DSN


def test_facility_gate_migration_creates_postgres_tables(monkeypatch) -> None:
    sa = pytest.importorskip("sqlalchemy")
    command = pytest.importorskip("alembic.command")

    assert POSTGRES_TEST_DSN
    monkeypatch.setenv("DATABASE_URL", POSTGRES_TEST_DSN)
    config = _alembic_config()

    command.stamp(config, "029")
    command.upgrade(config, "030")

    engine = sa.create_engine(_sync_dsn())
    inspector = sa.inspect(engine)
    try:
        assert "facility_events" in inspector.get_table_names()
        assert "facility_request_states" in inspector.get_table_names()
        assert "facility_records" in inspector.get_table_names()
        assert "facility_policy_records" in inspector.get_table_names()
        assert "facility_mandate_records" in inspector.get_table_names()
        facility_events_columns = {column["name"] for column in inspector.get_columns("facility_events")}
        assert {
            "event_id",
            "organization_id",
            "aggregate_id",
            "event_type",
            "idempotency_key",
            "payload",
            "previous_event_hash",
            "event_hash",
            "occurred_at",
            "created_at",
        }.issubset(facility_events_columns)
        unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("facility_events")
        }
        assert "uq_facility_events_idempotency" in unique_constraints
        facility_events_indexes = {index["name"] for index in inspector.get_indexes("facility_events")}
        assert "idx_facility_events_org_aggregate" in facility_events_indexes
        assert "idx_facility_events_type" in facility_events_indexes
        request_state_indexes = {index["name"] for index in inspector.get_indexes("facility_request_states")}
        assert "idx_facility_request_states_org" in request_state_indexes
        facility_record_columns = {column["name"] for column in inspector.get_columns("facility_records")}
        assert {
            "facility_id",
            "organization_id",
            "sponsor_id",
            "provider",
            "facility_type",
            "status",
            "version",
            "limit_payload",
            "approval_threshold_minor",
        }.issubset(facility_record_columns)
        facility_record_indexes = {index["name"] for index in inspector.get_indexes("facility_records")}
        assert "idx_facility_records_org_sponsor" in facility_record_indexes
        assert "idx_facility_records_status" in facility_record_indexes
        policy_record_columns = {column["name"] for column in inspector.get_columns("facility_policy_records")}
        assert {
            "policy_record_id",
            "organization_id",
            "facility_id",
            "policy_version",
            "snapshot",
            "snapshot_hash",
        }.issubset(policy_record_columns)
        policy_unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("facility_policy_records")
        }
        assert "uq_facility_policy_records_version" in policy_unique_constraints
        policy_record_indexes = {index["name"] for index in inspector.get_indexes("facility_policy_records")}
        assert "idx_facility_policy_records_latest" in policy_record_indexes
        mandate_record_columns = {column["name"] for column in inspector.get_columns("facility_mandate_records")}
        assert {
            "mandate_record_id",
            "organization_id",
            "mandate_id",
            "agent_id",
            "version",
            "snapshot",
            "snapshot_hash",
        }.issubset(mandate_record_columns)
        mandate_unique_constraints = {
            constraint["name"]
            for constraint in inspector.get_unique_constraints("facility_mandate_records")
        }
        assert "uq_facility_mandate_records_version" in mandate_unique_constraints
        mandate_record_indexes = {index["name"] for index in inspector.get_indexes("facility_mandate_records")}
        assert "idx_facility_mandate_records_lookup" in mandate_record_indexes
    finally:
        engine.dispose()
        command.downgrade(config, "029")

    engine = sa.create_engine(_sync_dsn())
    inspector = sa.inspect(engine)
    try:
        assert "facility_events" not in inspector.get_table_names()
        assert "facility_request_states" not in inspector.get_table_names()
        assert "facility_records" not in inspector.get_table_names()
        assert "facility_policy_records" not in inspector.get_table_names()
        assert "facility_mandate_records" not in inspector.get_table_names()
    finally:
        engine.dispose()

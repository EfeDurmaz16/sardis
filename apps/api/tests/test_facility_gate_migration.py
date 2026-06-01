from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

# Postgres DSN to run the SQL migration runner against. The DSN must point at a
# THROWAWAY database — the runner applies the full chain. Skipped by default.
POSTGRES_TEST_DSN = os.getenv("SARDIS_TEST_POSTGRES_DSN")

pytestmark = pytest.mark.skipif(
    not POSTGRES_TEST_DSN,
    reason="Set SARDIS_TEST_POSTGRES_DSN (throwaway DB) to run Facility Gate Postgres migration tests",
)


def _repo_root() -> Path:
    # apps/api/tests/ -> repo root is three parents up.
    return Path(__file__).resolve().parents[3]


def _runner_dsn() -> str:
    assert POSTGRES_TEST_DSN
    # The SQL runner shells out to psql, which expects a libpq URL. Strip any
    # SQLAlchemy driver suffix (postgresql+asyncpg:// / postgresql+psycopg://).
    dsn = POSTGRES_TEST_DSN
    for prefix in ("postgresql+asyncpg://", "postgresql+psycopg://"):
        if dsn.startswith(prefix):
            return "postgresql://" + dsn[len(prefix):]
    return dsn


def test_sql_runner_creates_facility_gate_tables() -> None:
    """The SQL migration chain (migration 113, ported from retired Alembic 030)
    must create the Facility Gate tables when applied by run_migrations.sh."""
    psycopg = pytest.importorskip("psycopg")

    root = _repo_root()
    runner = root / "scripts" / "run_migrations.sh"
    assert runner.exists(), f"migration runner not found at {runner}"

    env = dict(os.environ)
    env["DATABASE_URL"] = _runner_dsn()

    result = subprocess.run(
        ["bash", str(runner)],
        cwd=str(root),
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"run_migrations.sh failed (exit {result.returncode}).\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )

    expected_tables = {
        "facility_events",
        "facility_request_states",
        "facility_records",
        "facility_policy_records",
        "facility_mandate_records",
    }

    with psycopg.connect(_runner_dsn()) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public'"
            )
            tables = {row[0] for row in cur.fetchall()}
            assert expected_tables.issubset(tables), (
                f"missing facility tables: {sorted(expected_tables - tables)}"
            )

            cur.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'facility_events'"
            )
            facility_events_columns = {row[0] for row in cur.fetchall()}
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

            cur.execute(
                "SELECT conname FROM pg_constraint WHERE conname = "
                "'uq_facility_events_idempotency'"
            )
            assert cur.fetchone() is not None

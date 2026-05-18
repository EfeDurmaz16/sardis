from __future__ import annotations

import pytest

from sardis_api.repositories.treasury_repository import TreasuryRepository


@pytest.mark.asyncio
async def test_issuing_funding_repo_records_lists_and_summarizes_in_memory():
    repo = TreasuryRepository(dsn="memory://")

    await repo.record_issuing_funding_event(
        organization_id="org_1",
        provider="stripe",
        transfer_id="tu_1",
        amount_minor=1250,
        currency="USD",
        status_value="posted",
        connected_account_id="acct_1",
        idempotency_key="idem_1",
        metadata={"k": "v"},
    )

    rows = await repo.list_issuing_funding_events("org_1")
    assert len(rows) == 1
    assert rows[0]["transfer_id"] == "tu_1"
    assert rows[0]["connected_account_id"] == "acct_1"

    summary = await repo.summarize_issuing_funding_events("org_1", hours=24)
    assert summary["count"] == 1
    assert summary["total_minor"] == 1250
    assert summary["by_status"]["posted"] == 1


@pytest.mark.asyncio
async def test_funding_attempts_are_recorded_and_listed_in_order():
    repo = TreasuryRepository(dsn="memory://")

    await repo.record_funding_attempt(
        organization_id="org_1",
        operation_id="idem_1",
        attempt_index=1,
        provider="lithic",
        rail="fiat",
        status_value="failed",
        error_message="provider_down",
        amount_minor=500,
        currency="USD",
        connected_account_id=None,
        metadata={"path": "primary"},
    )
    await repo.record_funding_attempt(
        organization_id="org_1",
        operation_id="idem_1",
        attempt_index=2,
        provider="stripe",
        rail="fiat",
        status_value="success",
        amount_minor=500,
        currency="USD",
        connected_account_id="acct_1",
        metadata={"path": "fallback"},
    )

    rows = await repo.list_funding_attempts("org_1", operation_id="idem_1", limit=10)
    assert len(rows) == 2
    assert rows[0]["attempt_index"] == 1
    assert rows[0]["status"] == "failed"
    assert rows[1]["attempt_index"] == 2
    assert rows[1]["status"] == "success"

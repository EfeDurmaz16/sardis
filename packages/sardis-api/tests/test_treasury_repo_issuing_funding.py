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

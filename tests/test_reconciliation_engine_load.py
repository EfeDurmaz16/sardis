from __future__ import annotations

import asyncio
import random

import pytest

from sardis_api.canonical_state_machine import normalize_stablecoin_event
from sardis_api.repositories.canonical_ledger_repository import CanonicalLedgerRepository


@pytest.mark.asyncio
async def test_reconciliation_engine_handles_concurrent_out_of_order_events():
    repo = CanonicalLedgerRepository(dsn="memory://")

    async def ingest_for_idx(idx: int) -> None:
        ref = f"0xload{idx:04d}"
        submitted = normalize_stablecoin_event(
            organization_id="org_demo",
            rail="stablecoin_tx",
            reference=ref,
            provider_event_id=f"{ref}:submitted",
            provider_event_type="ONCHAIN_TX_SUBMITTED",
            canonical_event_type="stablecoin.tx.submitted",
            canonical_state="processing",
            amount_minor=1000 + idx,
            currency="USDC",
        )
        confirmed = normalize_stablecoin_event(
            organization_id="org_demo",
            rail="stablecoin_tx",
            reference=ref,
            provider_event_id=f"{ref}:confirmed",
            provider_event_type="ONCHAIN_TX_STATUS_CONFIRMED",
            canonical_event_type="stablecoin.tx.confirmed",
            canonical_state="settled",
            amount_minor=1000 + idx,
            currency="USDC",
        )
        events = [submitted, confirmed]
        if idx % 3 == 0:
            events = [confirmed, submitted]  # out-of-order branch
        if idx % 5 == 0:
            events.append(submitted)  # duplicate branch
        random.shuffle(events)
        for event in events:
            await repo.ingest_event(event, drift_tolerance_minor=5)

    await asyncio.gather(*(ingest_for_idx(i) for i in range(200)))

    journeys = await repo.list_journeys("org_demo", limit=1000)
    assert len(journeys) == 200
    # At scale, terminal state should remain stable despite replays/out-of-order events.
    settled = [j for j in journeys if str(j.get("canonical_state")) == "settled"]
    assert len(settled) >= 180


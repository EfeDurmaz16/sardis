from __future__ import annotations

from sardis_api.canonical_state_machine import (
    normalize_lithic_ach_event,
    normalize_stablecoin_event,
)
from sardis_api.repositories.canonical_ledger_repository import CanonicalLedgerRepository
import pytest


async def _build_repo() -> CanonicalLedgerRepository:
    return CanonicalLedgerRepository(dsn="memory://")


@pytest.mark.asyncio
async def test_canonical_repository_dedupes_provider_event_ids():
    repo = await _build_repo()
    event = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0xabc",
        provider_event_id="0xabc:submitted",
        provider_event_type="ONCHAIN_TX_SUBMITTED",
        canonical_event_type="stablecoin.tx.submitted",
        canonical_state="processing",
        amount_minor=100,
        currency="USDC",
    )
    first = await repo.ingest_event(event)
    second = await repo.ingest_event(event)
    assert first.duplicate is False
    assert second.duplicate is True
    assert second.event is None


@pytest.mark.asyncio
async def test_out_of_order_event_does_not_downgrade_state():
    repo = await _build_repo()
    settled = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0xdef",
        provider_event_id="0xdef:confirmed",
        provider_event_type="ONCHAIN_TX_STATUS_CONFIRMED",
        canonical_event_type="stablecoin.tx.confirmed",
        canonical_state="settled",
        amount_minor=500,
        currency="USDC",
    )
    old_processing = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0xdef",
        provider_event_id="0xdef:pending",
        provider_event_type="ONCHAIN_TX_STATUS_PENDING",
        canonical_event_type="stablecoin.tx.pending",
        canonical_state="processing",
        amount_minor=500,
        currency="USDC",
    )
    await repo.ingest_event(settled)
    result = await repo.ingest_event(old_processing)
    assert result.out_of_order is True
    assert str(result.journey.get("canonical_state")) == "settled"


@pytest.mark.asyncio
async def test_expected_vs_settled_mismatch_creates_break_and_manual_review():
    repo = await _build_repo()
    created = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0x123",
        provider_event_id="0x123:submitted",
        provider_event_type="ONCHAIN_TX_SUBMITTED",
        canonical_event_type="stablecoin.tx.submitted",
        canonical_state="processing",
        amount_minor=1000,
        currency="USDC",
    )
    settled_mismatch = normalize_stablecoin_event(
        organization_id="org_demo",
        rail="stablecoin_tx",
        reference="0x123",
        provider_event_id="0x123:confirmed",
        provider_event_type="ONCHAIN_TX_STATUS_CONFIRMED",
        canonical_event_type="stablecoin.tx.confirmed",
        canonical_state="settled",
        amount_minor=700,
        currency="USDC",
    )
    await repo.ingest_event(created, drift_tolerance_minor=0)
    result = await repo.ingest_event(settled_mismatch, drift_tolerance_minor=0)
    assert result.break_detected is True
    assert result.manual_review_created is True
    breaks = await repo.list_breaks("org_demo", status_value="open")
    reviews = await repo.list_manual_reviews("org_demo", status_value="queued")
    assert any(str(b.get("break_type")) == "expected_settled_mismatch" for b in breaks)
    assert any(str(r.get("reason_code")) == "drift_mismatch" for r in reviews)


@pytest.mark.asyncio
async def test_r29_ach_event_creates_critical_manual_review():
    repo = await _build_repo()
    payload = {
        "token": "evt_r29",
        "event_token": "evt_r29",
        "event_type": "ACH_RETURN_PROCESSED",
        "return_reason_code": "R29",
        "data": {
            "token": "pay_r29",
            "payment_token": "pay_r29",
            "currency": "USD",
            "direction": "COLLECTION",
            "amount": 2500,
            "status": "RETURNED",
        },
    }
    event = normalize_lithic_ach_event(
        organization_id="org_demo",
        payload=payload,
        event_type="ACH_RETURN_PROCESSED",
        payment_token="pay_r29",
    )
    result = await repo.ingest_event(event, drift_tolerance_minor=100)
    assert result.manual_review_created is True
    reviews = await repo.list_manual_reviews("org_demo", status_value="queued")
    assert any(str(r.get("reason_code")) == "R29" for r in reviews)

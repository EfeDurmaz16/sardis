from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock

import pytest

from sardis_cards.models import CardType
from sardis_cards.providers.partner_issuers import (
    BridgeCardsProvider,
    RainCardsProvider,
    parse_mapping,
)


def test_parse_mapping_accepts_dict_and_json():
    assert parse_mapping({"a": "b"}) == {"a": "b"}
    assert parse_mapping('{"x":"y"}') == {"x": "y"}
    assert parse_mapping("not-json") == {}


@pytest.mark.asyncio
async def test_bridge_provider_create_card_builds_payload_and_parses_response():
    provider = BridgeCardsProvider(
        api_key="bridge_key",
        api_secret="bridge_secret",
        program_id="program_1",
    )
    provider._send = AsyncMock(  # type: ignore[method-assign]
        return_value={
            "id": "card_br_123",
            "status": "active",
            "last4": "4242",
            "exp_month": 12,
            "exp_year": 2030,
        }
    )

    card = await provider.create_card(
        wallet_id="wallet_1",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("50"),
        limit_daily=Decimal("500"),
        limit_monthly=Decimal("2500"),
    )

    assert card.provider == "bridge_cards"
    assert card.provider_card_id == "card_br_123"
    assert card.card_number_last4 == "4242"
    assert card.limit_per_tx == Decimal("50")

    send_call = provider._send.await_args  # type: ignore[attr-defined]
    assert send_call.args[0] == "create_card"
    payload = send_call.kwargs["payload"]
    assert payload["program_id"] == "program_1"
    assert payload["limits"]["daily"] == "500"


@pytest.mark.asyncio
async def test_rain_provider_fund_card_updates_cached_balance():
    provider = RainCardsProvider(api_key="rain_key", program_id="rain_program")

    async def fake_send(operation: str, **kwargs):
        if operation == "create_card":
            return {
                "id": "card_rain_1",
                "status": "active",
                "last4": "1111",
                "exp_month": 1,
                "exp_year": 2031,
            }
        if operation == "fund_card":
            return {"id": "card_rain_1", "status": "active"}
        raise AssertionError(f"unexpected operation: {operation}")

    provider._send = fake_send  # type: ignore[method-assign]

    await provider.create_card(
        wallet_id="wallet_rain",
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("25"),
        limit_daily=Decimal("250"),
        limit_monthly=Decimal("1000"),
    )

    funded = await provider.fund_card("card_rain_1", Decimal("12.50"))

    assert funded.provider_card_id == "card_rain_1"
    assert funded.funded_amount == Decimal("12.50")
    assert funded.last_funded_at is not None

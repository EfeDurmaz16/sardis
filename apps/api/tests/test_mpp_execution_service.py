"""Tests for MPP payment execution helpers."""

from __future__ import annotations

from decimal import Decimal

import pytest

from server.models.mpp import ExecutePaymentRequest
from server.services.mpp_execution import chain_executor_key, execute_chain_payment


class _Receipt:
    tx_hash = "0xtest"


class _Executor:
    def __init__(self) -> None:
        self.mandate = None

    async def dispatch_payment(self, mandate):
        self.mandate = mandate
        return _Receipt()


def test_chain_executor_key_maps_tempo_aliases():
    assert chain_executor_key("tempo") == "tempo"
    assert chain_executor_key("tempo_testnet") == "tempo_testnet"
    assert chain_executor_key("tempo_moderato") == "tempo_testnet"
    assert chain_executor_key("base") == "base"


@pytest.mark.asyncio
async def test_execute_chain_payment_builds_payment_mandate(monkeypatch):
    from server.services import mpp_execution

    async def _resolve_wallet_address(wallet_id: str) -> str:
        assert wallet_id == "wallet_123"
        return "0xwallet"

    monkeypatch.setattr(mpp_execution, "resolve_wallet_address", _resolve_wallet_address)

    executor = _Executor()
    tx_hash = await execute_chain_payment(
        chain_executor=executor,
        session={
            "session_id": "mpp_sess_123",
            "wallet_id": "wallet_123",
            "chain": "tempo_moderato",
            "currency": "USDC",
        },
        request=ExecutePaymentRequest(
            amount=Decimal("1.25"),
            merchant="api.example.com",
            destination="0xmerchant",
            merchant_url="https://api.example.com",
        ),
        payment_id="mpp_pay_123",
        organization_id="org_123",
    )

    assert tx_hash == "0xtest"
    assert executor.mandate.mandate_id == "mpp_pay_123"
    assert executor.mandate.issuer == "sardis:mpp:mpp_sess_123"
    assert executor.mandate.subject == "org_123"
    assert executor.mandate.chain == "tempo_testnet"
    assert executor.mandate.token == "USDC"
    assert executor.mandate.amount_minor == 1_250_000
    assert executor.mandate.destination == "0xmerchant"
    assert executor.mandate.wallet_id == "wallet_123"
    assert executor.mandate.from_address == "0xwallet"
    assert executor.mandate.merchant_domain == "https://api.example.com"


@pytest.mark.asyncio
async def test_execute_chain_payment_requires_wallet_id():
    with pytest.raises(RuntimeError, match="no wallet_id"):
        await execute_chain_payment(
            chain_executor=_Executor(),
            session={
                "session_id": "mpp_sess_123",
                "chain": "tempo",
                "currency": "USDC",
            },
            request=ExecutePaymentRequest(amount=Decimal("1"), merchant="api.example.com"),
            payment_id="mpp_pay_123",
            organization_id="org_123",
        )

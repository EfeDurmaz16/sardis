from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from types import SimpleNamespace

import pytest

from sardis_v2_core.fiat_orchestrator import FiatPaymentOrchestrator


@dataclass
class _Session:
    session_id: str
    provider: str
    status: str


class _FakeRampRouter:
    def __init__(self, status: str) -> None:
        self._status = status

    async def get_best_offramp(self, **kwargs):  # noqa: ANN003
        return _Session(session_id="ramp_1", provider="bridge", status=self._status)


class _FakeTreasury:
    async def fund_issuing_balance(self, *, amount: Decimal, description: str):
        return SimpleNamespace(id="treasury_tx_1", amount=amount, description=description)


class _FakeSubLedger:
    def __init__(self) -> None:
        self.deposit_calls = 0

    async def get_account(self, agent_id: str):  # noqa: ARG002
        return None

    async def create_account(self, agent_id: str):  # noqa: ARG002
        return SimpleNamespace(account_id="acct_1")

    async def deposit(self, **kwargs):  # noqa: ANN003
        self.deposit_calls += 1
        return SimpleNamespace(tx_id="ledger_tx_1")


@pytest.mark.asyncio
async def test_fund_card_from_crypto_returns_pending_until_offramp_settles():
    sub_ledger = _FakeSubLedger()
    orchestrator = FiatPaymentOrchestrator(
        treasury=_FakeTreasury(),
        sub_ledger=sub_ledger,
        ramp_router=_FakeRampRouter(status="pending"),
        issuing_provider=None,
    )

    result = await orchestrator.fund_card_from_crypto(
        agent_id="agent_1",
        amount_usd=Decimal("25.00"),
        wallet_address="0xabc",
    )

    assert result.status == "pending"
    assert result.ramp_session_id == "ramp_1"
    assert sub_ledger.deposit_calls == 0


@pytest.mark.asyncio
async def test_fund_card_from_crypto_completed_session_credits_ledger_and_issuing():
    sub_ledger = _FakeSubLedger()
    orchestrator = FiatPaymentOrchestrator(
        treasury=_FakeTreasury(),
        sub_ledger=sub_ledger,
        ramp_router=_FakeRampRouter(status="completed"),
        issuing_provider=None,
    )

    result = await orchestrator.fund_card_from_crypto(
        agent_id="agent_1",
        amount_usd=Decimal("25.00"),
        wallet_address="0xabc",
    )

    assert result.status == "completed"
    assert result.sub_ledger_tx_id == "ledger_tx_1"
    assert result.treasury_tx_id == "treasury_tx_1"
    assert sub_ledger.deposit_calls == 1

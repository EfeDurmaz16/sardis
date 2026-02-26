from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from sardis_v2_core.a2a_escrow import Escrow, EscrowState
from sardis_v2_core.a2a_settlement import SettlementEngine
from sardis_v2_core.database import Database
from sardis_v2_core.exceptions import SardisTransactionFailedError, SardisValidationError
from sardis_v2_core.wallets import Wallet


@dataclass
class _Ctx:
    conn: Any

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _CaptureConn:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...]]] = []

    async def execute(self, query: str, *args) -> None:
        self.calls.append((query, args))

    async def fetchrow(self, query: str, *args):
        return None

    async def fetch(self, query: str, *args):
        return []


class _WalletRepo:
    def __init__(self, wallets: dict[str, Wallet]) -> None:
        self._wallets = wallets

    async def get_by_agent(self, agent_id: str):
        return self._wallets.get(agent_id)


class _Receipt:
    def __init__(self) -> None:
        self.tx_hash = "0xabc123"
        self.block_number = 123456
        self.execution_path = "legacy_tx"
        self.user_op_hash = None


class _ChainExecutor:
    def __init__(self, receipt: Any) -> None:
        self._receipt = receipt
        self.mandates: list[Any] = []

    async def dispatch_payment(self, mandate):
        self.mandates.append(mandate)
        return self._receipt


def _released_escrow() -> Escrow:
    now = datetime.now(timezone.utc)
    return Escrow(
        id="escrow_123",
        payer_agent_id="agent_payer",
        payee_agent_id="agent_payee",
        amount=Decimal("12.50"),
        token="USDC",
        chain="base",
        state=EscrowState.RELEASED,
        created_at=now - timedelta(hours=3),
        expires_at=now + timedelta(hours=3),
    )


def _wallet(agent_id: str, chain: str, address: str) -> Wallet:
    w = Wallet.new(agent_id=agent_id, wallet_id=f"wallet_{agent_id[-5:]}")
    w.set_address(chain, address)
    return w


@pytest.mark.asyncio
async def test_settle_on_chain_uses_chain_executor_and_persists(monkeypatch):
    write_conn = _CaptureConn()
    tx_conn = _CaptureConn()
    monkeypatch.setattr(Database, "connection", staticmethod(lambda: _Ctx(write_conn)))
    monkeypatch.setattr(Database, "transaction", staticmethod(lambda: _Ctx(tx_conn)))

    repo = _WalletRepo(
        {
            "agent_payer": _wallet("agent_payer", "base", "0x1111111111111111111111111111111111111111"),
            "agent_payee": _wallet("agent_payee", "base", "0x2222222222222222222222222222222222222222"),
        }
    )
    exec_ = _ChainExecutor(_Receipt())
    engine = SettlementEngine(chain_executor=exec_, wallet_repo=repo)

    result = await engine.settle_on_chain(_released_escrow())

    assert result.tx_hash == "0xabc123"
    assert result.block_number == 123456
    assert result.explorer_url == "https://basescan.org/tx/0xabc123"
    assert result.execution_path == "legacy_tx"
    assert exec_.mandates
    assert exec_.mandates[0].destination == "0x2222222222222222222222222222222222222222"
    assert exec_.mandates[0].wallet_id is not None
    assert len(tx_conn.calls) == 2  # debit + credit
    assert len(write_conn.calls) == 1  # settlements insert


@pytest.mark.asyncio
async def test_settle_on_chain_requires_dependencies():
    engine = SettlementEngine()
    with pytest.raises(SardisValidationError, match="chain_executor is required"):
        await engine.settle_on_chain(_released_escrow())


@pytest.mark.asyncio
async def test_settle_on_chain_rejects_missing_tx_hash(monkeypatch):
    write_conn = _CaptureConn()
    tx_conn = _CaptureConn()
    monkeypatch.setattr(Database, "connection", staticmethod(lambda: _Ctx(write_conn)))
    monkeypatch.setattr(Database, "transaction", staticmethod(lambda: _Ctx(tx_conn)))

    repo = _WalletRepo(
        {
            "agent_payer": _wallet("agent_payer", "base", "0x1111111111111111111111111111111111111111"),
            "agent_payee": _wallet("agent_payee", "base", "0x2222222222222222222222222222222222222222"),
        }
    )
    exec_ = _ChainExecutor(receipt=object())
    engine = SettlementEngine(chain_executor=exec_, wallet_repo=repo)

    with pytest.raises(SardisTransactionFailedError, match="empty transaction hash"):
        await engine.settle_on_chain(_released_escrow())

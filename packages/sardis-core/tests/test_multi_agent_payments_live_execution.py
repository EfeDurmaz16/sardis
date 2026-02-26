from __future__ import annotations

from decimal import Decimal
from types import SimpleNamespace

import pytest

from sardis_v2_core.multi_agent_payments import (
    FlowState,
    PaymentLegState,
    PaymentOrchestrator,
)
from sardis_v2_core.wallet_repository import WalletRepository


def _address(seed: int) -> str:
    return f"0x{seed:040x}"


class _FakeChainExecutor:
    def __init__(self, *, fail_on_calls: set[int] | None = None) -> None:
        self.calls = []
        self._call_count = 0
        self._fail_on_calls = fail_on_calls or set()

    async def dispatch_payment(self, mandate):
        self._call_count += 1
        self.calls.append(mandate)
        if self._call_count in self._fail_on_calls:
            raise RuntimeError(f"forced failure on call {self._call_count}")
        return SimpleNamespace(
            tx_hash=f"0x{self._call_count:064x}",
            block_number=100 + self._call_count,
            execution_path="erc4337_userop",
            user_op_hash=f"0x{(1000 + self._call_count):064x}",
        )


async def _seed_wallet(repo: WalletRepository, *, agent_id: str, seed: int) -> None:
    wallet = await repo.create(
        agent_id=agent_id,
        wallet_id=f"wallet_{agent_id}",
        account_type="erc4337_v2",
    )
    await repo.set_address(wallet.wallet_id, "base", _address(seed))


@pytest.mark.asyncio
async def test_split_flow_executes_legs_via_chain_executor() -> None:
    repo = WalletRepository()
    await _seed_wallet(repo, agent_id="agent_payer", seed=1)
    await _seed_wallet(repo, agent_id="agent_a", seed=2)
    await _seed_wallet(repo, agent_id="agent_b", seed=3)
    executor = _FakeChainExecutor()
    orchestrator = PaymentOrchestrator(
        chain_executor=executor,
        wallet_repo=repo,
        require_chain_execution=True,
    )

    flow = await orchestrator.create_split_payment(
        payer_id="agent_payer",
        recipients=[("agent_a", Decimal("0.50")), ("agent_b", Decimal("0.50"))],
        total_amount=Decimal("10.00"),
        token="USDC",
        chain="base",
    )
    flow = await orchestrator.execute_flow(flow.id)

    assert flow.state == FlowState.COMPLETED
    assert len(executor.calls) == 2
    assert all(leg.state == PaymentLegState.COMPLETED for leg in flow.legs)
    assert all((leg.tx_hash or "").startswith("0x") for leg in flow.legs)
    assert all((leg.explorer_url or "").startswith("https://basescan.org/tx/") for leg in flow.legs)


@pytest.mark.asyncio
async def test_live_execution_requires_chain_dependencies() -> None:
    orchestrator = PaymentOrchestrator(require_chain_execution=True)
    flow = await orchestrator.create_group_payment(
        payers=[("agent_a", Decimal("5.00"))],
        recipient_id="agent_b",
        token="USDC",
        chain="base",
    )

    with pytest.raises(
        ValueError,
        match="Live chain execution required but chain_executor/wallet_repo are not configured",
    ):
        await orchestrator.execute_flow(flow.id)


@pytest.mark.asyncio
async def test_simulated_path_uses_deterministic_hash_when_live_not_required(monkeypatch) -> None:
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "simulated")
    orchestrator = PaymentOrchestrator(require_chain_execution=False)
    flow = await orchestrator.create_group_payment(
        payers=[("agent_a", Decimal("2.50"))],
        recipient_id="agent_b",
        token="USDC",
        chain="base",
    )

    flow = await orchestrator.execute_flow(flow.id)

    assert flow.state == FlowState.COMPLETED
    assert flow.legs[0].state == PaymentLegState.COMPLETED
    assert flow.legs[0].tx_hash is not None
    assert len(flow.legs[0].tx_hash) == 66


@pytest.mark.asyncio
async def test_cascade_stops_after_executor_failure() -> None:
    repo = WalletRepository()
    await _seed_wallet(repo, agent_id="agent_1", seed=11)
    await _seed_wallet(repo, agent_id="agent_2", seed=12)
    await _seed_wallet(repo, agent_id="agent_3", seed=13)
    await _seed_wallet(repo, agent_id="merchant", seed=14)
    executor = _FakeChainExecutor(fail_on_calls={2})
    orchestrator = PaymentOrchestrator(
        chain_executor=executor,
        wallet_repo=repo,
        require_chain_execution=True,
    )
    flow = await orchestrator.create_cascade_payment(
        steps=[
            {"payer_id": "agent_1", "recipient_id": "merchant", "amount": "1.00"},
            {"payer_id": "agent_2", "recipient_id": "merchant", "amount": "1.00"},
            {"payer_id": "agent_3", "recipient_id": "merchant", "amount": "1.00"},
        ],
        token="USDC",
        chain="base",
    )

    flow = await orchestrator.execute_flow(flow.id)

    assert flow.state == FlowState.PARTIAL
    assert flow.legs[0].state == PaymentLegState.COMPLETED
    assert flow.legs[1].state == PaymentLegState.FAILED
    assert flow.legs[2].state == PaymentLegState.PENDING
    assert len(executor.calls) == 2

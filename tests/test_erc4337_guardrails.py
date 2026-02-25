from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from sardis_chain.erc4337.proof_artifact import write_erc4337_proof_artifact
from sardis_chain.erc4337.sponsor_caps import SponsorCapExceeded, SponsorCapGuard
from sardis_chain.erc4337.user_operation import UserOperation, zero_hex
from sardis_chain.executor import ChainExecutor
from sardis_v2_core import SardisSettings


def _sample_user_op() -> UserOperation:
    return UserOperation(
        sender="0x1111111111111111111111111111111111111111",
        nonce=1,
        init_code=zero_hex(),
        call_data="0xdeadbeef",
        call_gas_limit=200_000,
        verification_gas_limit=250_000,
        pre_verification_gas=60_000,
        max_fee_per_gas=2_000_000_000,
        max_priority_fee_per_gas=1_000_000_000,
        paymaster_and_data=zero_hex(),
        signature=zero_hex(),
    )


def test_sponsor_cap_guard_enforces_per_op_limit() -> None:
    guard = SponsorCapGuard(stage="pilot")
    estimated_cost = guard.current_caps().per_op_wei + 1

    with pytest.raises(SponsorCapExceeded):
        guard.reserve(chain="base_sepolia", estimated_cost_wei=estimated_cost)


def test_sponsor_cap_guard_accepts_stage_override_json() -> None:
    guard = SponsorCapGuard(
        stage="pilot",
        stage_caps_json='{"pilot":{"per_op_wei":2000000000000000000,"daily_wei":3000000000000000000}}',
    )
    guard.reserve(chain="base_sepolia", estimated_cost_wei=1_000_000_000_000_000_000)
    snapshot = guard.snapshot_usage()

    assert snapshot["stage"] == "pilot"
    assert snapshot["caps"]["per_op_wei"] == 2_000_000_000_000_000_000


def test_write_erc4337_proof_artifact(tmp_path: Path) -> None:
    artifact = write_erc4337_proof_artifact(
        base_dir=str(tmp_path),
        mandate_id="mandate_123",
        chain="base_sepolia",
        wallet_id="wallet_123",
        smart_account="0x2222222222222222222222222222222222222222",
        entrypoint="0x0000000071727De22E5E9d8BAf0edAc6f37da032",
        user_operation={"sender": "0x2222"},
        user_op_hash="0xaaaabbbbccccdddd",
        tx_hash="0xfeedface",
        receipt={"receipt": {"transactionHash": "0xfeedface"}},
    )

    assert artifact.sha256
    output_path = Path(artifact.path)
    assert output_path.exists()
    assert "base_sepolia" in artifact.path
    payload = output_path.read_text(encoding="utf-8")
    assert "mandate_123" in payload


@pytest.mark.asyncio
async def test_chain_executor_sign_user_op_uses_signer() -> None:
    settings = SardisSettings(chain_mode="simulated", environment="dev")
    executor = ChainExecutor(settings)
    signer = SimpleNamespace(sign_user_operation_hash=lambda wallet_id, user_op_hash: None)

    async def _sign(wallet_id: str, user_op_hash: str) -> str:
        assert wallet_id == "wallet_abc"
        assert user_op_hash == "0x1234"
        return "abcd"

    signer.sign_user_operation_hash = _sign
    executor._mpc_signer = signer  # type: ignore[assignment]

    signature = await executor._sign_user_operation_hash("wallet_abc", "0x1234")
    assert signature == "0xabcd"

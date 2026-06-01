"""Tests for fail-closed agent wallet provisioning.

Agent-create used to swallow Turnkey failures and create an address-less wallet
labelled mpc_provider="turnkey", returning a green 201 over a dead wallet. It is
now fail-closed: in live mode a provisioning failure raises (caller 503s); in
simulated/dev it returns an honestly-labelled "simulated" wallet with an address.
"""
from __future__ import annotations

from decimal import Decimal

import pytest

from server.routes.agents.lifecycle import AgentDependencies, _provision_agent_wallet


class _StubWallet:
    def __init__(self, wallet_id, mpc_provider, addresses):
        self.wallet_id = wallet_id
        self.mpc_provider = mpc_provider
        self.addresses = addresses or {}


class _StubWalletRepo:
    def __init__(self):
        self.created = None

    async def create(self, *, agent_id, wallet_id, mpc_provider, currency,
                     limit_per_tx, limit_total, addresses):
        self.created = _StubWallet(wallet_id or "wal_stub", mpc_provider, addresses)
        return self.created


class _FailingWalletManager:
    """Simulates Turnkey unavailable (no turnkey_client configured)."""

    async def create_turnkey_wallet(self, *, wallet_name, agent_id):
        raise RuntimeError("Turnkey client is not configured.")


class _WorkingWalletManager:
    async def create_turnkey_wallet(self, *, wallet_name, agent_id):
        return {
            "wallet_id": "wal_turnkey_real",
            "addresses": [{"address": "0xabc0000000000000000000000000000000000def"}],
            "provider": "turnkey",
        }


def _deps(wallet_manager):
    return AgentDependencies(
        agent_repo=None,
        wallet_repo=_StubWalletRepo(),
        wallet_manager=wallet_manager,
    )


@pytest.mark.asyncio
async def test_simulated_mode_makes_honest_simulated_wallet(monkeypatch):
    """Test/dev environment: no Turnkey -> honestly labelled simulated wallet w/ address."""
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "simulated")
    monkeypatch.delenv("SARDIS_EXECUTION_MODE", raising=False)
    deps = _deps(_FailingWalletManager())
    wallet = await _provision_agent_wallet(
        deps, agent_id="agent_x", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"),
    )
    assert wallet.mpc_provider == "simulated"  # NOT "turnkey"
    assert wallet.addresses  # has an address, not None
    assert all(a.startswith("0x") for a in wallet.addresses.values())


@pytest.mark.asyncio
async def test_live_mode_fails_closed(monkeypatch):
    """Live mode: no real custody -> raise, so the caller rolls back and 503s."""
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "live")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.delenv("SARDIS_EXECUTION_MODE", raising=False)
    deps = _deps(_FailingWalletManager())
    with pytest.raises(RuntimeError, match="wallet_provisioning_unavailable"):
        await _provision_agent_wallet(
            deps, agent_id="agent_y", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"),
        )
    assert deps.wallet_repo.created is None  # no dead wallet written


@pytest.mark.asyncio
async def test_turnkey_success_makes_real_wallet(monkeypatch):
    """When Turnkey provisions a real address, we get a turnkey-labelled wallet."""
    monkeypatch.setenv("SARDIS_CHAIN_MODE", "live")
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    monkeypatch.delenv("SARDIS_EXECUTION_MODE", raising=False)
    deps = _deps(_WorkingWalletManager())
    wallet = await _provision_agent_wallet(
        deps, agent_id="agent_z", limit_per_tx=Decimal("100"), limit_total=Decimal("1000"),
    )
    assert wallet.mpc_provider == "turnkey"
    assert wallet.wallet_id == "wal_turnkey_real"
    assert wallet.addresses["base"] == "0xabc0000000000000000000000000000000000def"

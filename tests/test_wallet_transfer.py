"""Tests for wallet transfer endpoint."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis_api.routers.wallets import WalletDependencies, get_deps
from sardis_api.routers.wallets import router as wallets_router


@pytest.fixture
def mock_wallet_repo():
    repo = AsyncMock()
    wallet = MagicMock()
    wallet.wallet_id = "wallet_1"
    wallet.agent_id = "agent_1"
    wallet.mpc_provider = "turnkey"
    wallet.addresses = {"base_sepolia": "0xsender123"}
    wallet.currency = "USDC"
    wallet.limit_per_tx = 100
    wallet.limit_total = 1000
    wallet.is_active = True
    wallet.is_frozen = False
    wallet.frozen_by = None
    wallet.freeze_reason = None
    wallet.get_address.return_value = "0xsender123"
    wallet.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00Z")
    wallet.updated_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00Z")
    repo.get.return_value = wallet
    return repo


@pytest.fixture
def mock_agent_repo():
    repo = AsyncMock()
    agent = MagicMock()
    agent.agent_id = "agent_1"
    agent.owner_id = "org_demo"
    repo.get.return_value = agent
    return repo


@pytest.fixture
def mock_chain_executor():
    executor = AsyncMock()
    receipt = MagicMock(spec=[
        "tx_hash", "audit_anchor", "fee_tx_hash",
        "execution_path", "user_op_hash",
        "proof_artifact_path", "proof_artifact_sha256",
    ])
    receipt.tx_hash = "0xtxhash123"
    receipt.audit_anchor = None
    receipt.fee_tx_hash = None
    receipt.execution_path = "legacy_tx"
    receipt.user_op_hash = None
    receipt.proof_artifact_path = None
    receipt.proof_artifact_sha256 = None
    executor.dispatch_payment.return_value = receipt
    return executor


@pytest.fixture
def mock_wallet_manager():
    manager = AsyncMock()
    policy_result = MagicMock()
    policy_result.allowed = True
    policy_result.reason = None
    manager.async_validate_policies.return_value = policy_result
    manager.async_record_spend.return_value = None
    return manager


@pytest.fixture
def mock_compliance():
    compliance = AsyncMock()
    result = MagicMock()
    result.allowed = True
    result.reason = None
    compliance.preflight.return_value = result
    return compliance


@pytest.fixture
def mock_payment_orchestrator():
    orchestrator = AsyncMock()
    result = MagicMock()
    result.chain_tx_hash = "0xtxhash123"
    result.chain = "base_sepolia"
    result.ledger_tx_id = "ledger_1"
    result.status = "submitted"
    result.audit_anchor = None
    result.execution_path = "legacy_tx"
    result.user_op_hash = None
    result.proof_artifact_path = None
    result.proof_artifact_sha256 = None
    orchestrator.execute_chain.return_value = result
    return orchestrator


@pytest.fixture
def app_with_wallets(mock_wallet_repo, mock_agent_repo, mock_chain_executor, mock_wallet_manager, mock_compliance, mock_payment_orchestrator):
    app = FastAPI()
    deps = WalletDependencies(
        wallet_repo=mock_wallet_repo,
        agent_repo=mock_agent_repo,
        chain_executor=mock_chain_executor,
        wallet_manager=mock_wallet_manager,
        compliance=mock_compliance,
        payment_orchestrator=mock_payment_orchestrator,
    )
    app.dependency_overrides[get_deps] = lambda: deps
    app.include_router(wallets_router, prefix="/api/v2/wallets")
    return app


class TestWalletTransfer:
    def test_transfer_success(self, app_with_wallets, mock_payment_orchestrator):
        client = TestClient(app_with_wallets)
        resp = client.post("/api/v2/wallets/wallet_1/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.5,
            "token": "USDC",
            "chain": "base_sepolia",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["tx_hash"] == "0xtxhash123"
        assert data["status"] == "submitted"
        assert data["from_address"] == "0xsender123"
        assert data["to_address"] == "0xrecipient456"
        assert data["amount"] == "10.5"
        mock_payment_orchestrator.execute_chain.assert_called_once()

    def test_transfer_wallet_not_found(self, app_with_wallets, mock_wallet_repo):
        mock_wallet_repo.get.return_value = None
        client = TestClient(app_with_wallets)
        resp = client.post("/api/v2/wallets/nonexistent/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.0,
        })
        assert resp.status_code == 404

    def test_transfer_inactive_wallet(self, app_with_wallets, mock_wallet_repo):
        mock_wallet_repo.get.return_value.is_active = False
        client = TestClient(app_with_wallets)
        resp = client.post("/api/v2/wallets/wallet_1/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.0,
        })
        assert resp.status_code == 400
        assert "inactive" in resp.json()["detail"]

    def test_transfer_no_address_for_chain(self, app_with_wallets, mock_wallet_repo):
        mock_wallet_repo.get.return_value.get_address.return_value = None
        client = TestClient(app_with_wallets)
        resp = client.post("/api/v2/wallets/wallet_1/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.0,
            "chain": "polygon",
        })
        assert resp.status_code == 400

    def test_transfer_no_chain_executor(self, mock_wallet_repo):
        app = FastAPI()
        agent_repo = AsyncMock()
        agent = MagicMock()
        agent.agent_id = "agent_1"
        agent.owner_id = "org_demo"
        agent_repo.get.return_value = agent
        deps = WalletDependencies(wallet_repo=mock_wallet_repo, agent_repo=agent_repo, chain_executor=None)
        app.dependency_overrides[get_deps] = lambda: deps
        app.include_router(wallets_router, prefix="/api/v2/wallets")
        client = TestClient(app)
        resp = client.post("/api/v2/wallets/wallet_1/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.0,
        })
        assert resp.status_code == 503

    def test_transfer_chain_error(self, app_with_wallets, mock_payment_orchestrator):
        from sardis_v2_core.orchestrator import ChainExecutionError
        mock_payment_orchestrator.execute_chain.side_effect = ChainExecutionError("nonce too low")
        client = TestClient(app_with_wallets)
        resp = client.post("/api/v2/wallets/wallet_1/transfer", json={
            "destination": "0xrecipient456",
            "amount": 10.0,
        })
        assert resp.status_code == 500
        assert "nonce too low" in resp.json()["detail"]

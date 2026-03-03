from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers import wallets
from sardis_v2_core.database import Database
from sardis_v2_core.wallets import Wallet


class _StubWalletRepo:
    def __init__(self, wallet: Wallet):
        self._wallet = wallet

    async def get(self, wallet_id: str) -> Wallet | None:
        if wallet_id == self._wallet.wallet_id:
            return self._wallet
        return None


class _StubAgentRepo:
    async def get(self, agent_id: str) -> Any:
        return SimpleNamespace(agent_id=agent_id, owner_id="org_test")


class _StubChainExecutor:
    async def dispatch_payment(self, _mandate: Any) -> Any:
        return SimpleNamespace(tx_hash="0xsettled")


def _build_app(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    wallet = Wallet(
        wallet_id="wallet_1",
        agent_id="agent_1",
        mpc_provider="turnkey",
        addresses={"base": "0x1111111111111111111111111111111111111111"},
        limit_per_tx="1000.00",
        limit_total="5000.00",
    )
    deps = wallets.WalletDependencies(
        wallet_repo=_StubWalletRepo(wallet),
        agent_repo=_StubAgentRepo(),
        chain_executor=_StubChainExecutor(),
    )

    challenges: dict[str, dict[str, Any]] = {}
    settlements: dict[str, dict[str, Any]] = {}

    async def _execute(query: str, *args: Any) -> Any:
        normalized = " ".join(query.split()).lower()

        if "insert into x402_challenges" in normalized:
            payment_id, wallet_id, challenge_json, expires_at = args
            challenges[payment_id] = {
                "payment_id": payment_id,
                "wallet_id": wallet_id,
                "challenge": challenge_json,
                "expires_at": expires_at,
            }
            return "INSERT 0 1"

        if "delete from x402_challenges where expires_at < now()" in normalized:
            now = datetime.now(timezone.utc)
            expired = [key for key, row in challenges.items() if row["expires_at"] < now]
            for key in expired:
                challenges.pop(key, None)
            return f"DELETE {len(expired)}"

        if "delete from x402_challenges where payment_id = $1" in normalized:
            payment_id = args[0]
            challenges.pop(payment_id, None)
            return "DELETE 1"

        if "insert into x402_settlements" in normalized:
            payment_id, status, challenge_json, payload_json, tx_hash, settled_at, error = args
            settlements[payment_id] = {
                "payment_id": payment_id,
                "status": status,
                "challenge": challenge_json,
                "payload": payload_json,
                "tx_hash": tx_hash,
                "settled_at": settled_at,
                "error": error,
            }
            return "INSERT 0 1"

        if "update x402_settlements set" in normalized:
            payment_id = args[0]
            row = settlements.get(payment_id)
            if row is None:
                return "UPDATE 0"
            row["status"] = args[1]
            arg_idx = 2
            if "tx_hash = $3" in normalized:
                row["tx_hash"] = args[arg_idx]
                arg_idx += 1
            if "settled_at = $4" in normalized or "settled_at = $3" in normalized:
                row["settled_at"] = args[arg_idx]
                arg_idx += 1
            if "error = $3" in normalized or "error = $4" in normalized or "error = $5" in normalized:
                row["error"] = args[arg_idx]
            return "UPDATE 1"

        return "OK"

    async def _fetchrow(query: str, *args: Any) -> Any:
        normalized = " ".join(query.split()).lower()

        if "select challenge from x402_challenges" in normalized:
            payment_id, wallet_id = args
            row = challenges.get(payment_id)
            if row is None:
                return None
            if row["wallet_id"] != wallet_id:
                return None
            if row["expires_at"] < datetime.now(timezone.utc):
                return None
            return {"challenge": row["challenge"]}

        if "select * from x402_settlements where payment_id = $1" in normalized:
            payment_id = args[0]
            return settlements.get(payment_id)

        return None

    monkeypatch.setattr(Database, "execute", _execute)
    monkeypatch.setattr(Database, "fetchrow", _fetchrow)

    async def _principal() -> Principal:
        return Principal(kind="api_key", organization_id="org_test", scopes=["admin"])

    app = FastAPI()
    app.dependency_overrides[wallets.get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = _principal
    app.include_router(wallets.router, prefix="/api/v2/wallets")
    return TestClient(app), challenges, settlements


def test_x402_challenge_verify_settle_happy_path(monkeypatch: pytest.MonkeyPatch) -> None:
    client, challenges, settlements = _build_app(monkeypatch)

    challenge_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/challenge",
        json={
            "resource_uri": "https://api.vendor.dev/v1/data",
            "amount": "100",
            "currency": "USDC",
            "network": "base",
            "ttl_seconds": 300,
        },
    )
    assert challenge_resp.status_code == 200
    challenge = challenge_resp.json()
    assert challenge["token_address"] == "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
    assert challenge["payment_id"] in challenges

    verify_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/verify",
        json={
            "payment_id": challenge["payment_id"],
            "payer_address": "0x2222222222222222222222222222222222222222",
            "amount": "100",
            "nonce": challenge["nonce"],
            "signature": "0xsig",
            "authorization": {},
        },
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["accepted"] is True
    assert body["reason"] is None
    assert settlements[challenge["payment_id"]]["status"] == "verified"
    assert challenge["payment_id"] not in challenges

    settle_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/settle",
        json={"payment_id": challenge["payment_id"]},
    )
    assert settle_resp.status_code == 200
    settled = settle_resp.json()
    assert settled["status"] == "settled"
    assert settled["tx_hash"] == "0xsettled"


def test_x402_verify_amount_mismatch_records_failed_settlement(monkeypatch: pytest.MonkeyPatch) -> None:
    client, _challenges, settlements = _build_app(monkeypatch)

    challenge_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/challenge",
        json={
            "resource_uri": "https://api.vendor.dev/v1/data",
            "amount": "100",
            "currency": "USDC",
            "network": "base",
            "ttl_seconds": 300,
        },
    )
    assert challenge_resp.status_code == 200
    challenge = challenge_resp.json()

    verify_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/verify",
        json={
            "payment_id": challenge["payment_id"],
            "payer_address": "0x2222222222222222222222222222222222222222",
            "amount": "101",
            "nonce": challenge["nonce"],
            "signature": "0xsig",
            "authorization": {},
        },
    )
    assert verify_resp.status_code == 200
    body = verify_resp.json()
    assert body["accepted"] is False
    assert body["reason"] == "x402_amount_mismatch"
    assert settlements[challenge["payment_id"]]["status"] == "failed"

    settle_resp = client.post(
        "/api/v2/wallets/wallet_1/x402/settle",
        json={"payment_id": challenge["payment_id"]},
    )
    assert settle_resp.status_code == 400
    assert "expected 'verified'" in settle_resp.json()["detail"]

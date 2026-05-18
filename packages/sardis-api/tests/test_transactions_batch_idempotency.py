from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import require_principal
from sardis_api.routers import transactions


class FakeCache:
    def __init__(self):
        self.values: dict[str, str] = {}
        self.locks: set[str] = set()

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str, ttl: int | None = None) -> None:
        self.values[key] = value

    async def acquire_lock(self, key: str, ttl_seconds: int) -> str | None:
        if key in self.locks:
            return None
        self.locks.add(key)
        return f"owner:{key}"

    async def release_lock(self, key: str, owner: str) -> None:
        self.locks.discard(key)


class FakePrincipal:
    organization_id = "org_test"
    org_id = "org_test"
    scopes = ["pay"]

    @property
    def user_id(self) -> str:
        return "agent_test"


def _client(chain_executor: MagicMock) -> TestClient:
    app = FastAPI()
    app.state.cache_service = FakeCache()
    app.include_router(transactions.router, prefix="/api/v2/transactions")
    app.dependency_overrides[transactions.get_deps] = lambda: transactions.TransactionDependencies(
        chain_executor=chain_executor,
    )
    app.dependency_overrides[require_principal] = lambda: FakePrincipal()
    return TestClient(app)


def _payload(amount: str = "1250") -> dict:
    return {
        "wallet_id": "wallet_test",
        "chain": "base",
        "token": "USDC",
        "transfers": [
            {
                "destination": "0x0000000000000000000000000000000000000001",
                "amount": amount,
                "reference": "invoice_1",
            }
        ],
    }


def _executor() -> MagicMock:
    receipt = MagicMock()
    receipt.tx_hash = "0xtx_batch"
    executor = MagicMock()
    executor.execute_mandate = AsyncMock(return_value=receipt)
    return executor


def test_transactions_batch_idempotency_replays_same_payload_without_reexecution():
    executor = _executor()
    client = _client(executor)

    first = client.post(
        "/api/v2/transactions/batch",
        json=_payload(),
        headers={"Idempotency-Key": "tx_batch_same_payload"},
    )
    second = client.post(
        "/api/v2/transactions/batch",
        json=_payload(),
        headers={"Idempotency-Key": "tx_batch_same_payload"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert executor.execute_mandate.await_count == 1


def test_transactions_batch_idempotency_rejects_same_key_with_different_payload():
    executor = _executor()
    client = _client(executor)

    first = client.post(
        "/api/v2/transactions/batch",
        json=_payload("1250"),
        headers={"Idempotency-Key": "tx_batch_changed_payload"},
    )
    replay = client.post(
        "/api/v2/transactions/batch",
        json=_payload("1300"),
        headers={"Idempotency-Key": "tx_batch_changed_payload"},
    )

    assert first.status_code == 200
    assert replay.status_code == 409
    assert replay.json()["detail"] == "idempotency_key_reuse_different_payload"
    assert executor.execute_mandate.await_count == 1

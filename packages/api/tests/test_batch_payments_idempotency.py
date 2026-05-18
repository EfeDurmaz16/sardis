from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis.authz import require_principal
from sardis.routes.money_movement.batch_payments import router


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


def _client() -> TestClient:
    app = FastAPI()
    app.state.cache_service = FakeCache()
    app.include_router(router, prefix="/api/v2")
    app.dependency_overrides[require_principal] = lambda: FakePrincipal()
    return TestClient(app)


def _payload(amount: str = "12.50") -> dict:
    return {
        "chain": "tempo",
        "transfers": [
            {
                "to": "0x0000000000000000000000000000000000000001",
                "amount": amount,
                "token": "USDC",
            }
        ],
    }


def _executor_patch() -> tuple[MagicMock, object]:
    receipt = MagicMock()
    receipt.tx_hash = "0xbatch_tx"
    receipt.status = True
    executor = MagicMock()
    executor.execute_batch_transfers = AsyncMock(return_value=receipt)
    return executor, patch("sardis_chain.tempo.executor.TempoExecutor", return_value=executor)


def test_batch_payment_idempotency_replays_same_payload_without_reexecution():
    client = _client()
    executor, executor_patch = _executor_patch()

    with executor_patch:
        first = client.post(
            "/api/v2/payments/batch",
            json=_payload(),
            headers={"Idempotency-Key": "batch_same_payload"},
        )
        second = client.post(
            "/api/v2/payments/batch",
            json=_payload(),
            headers={"Idempotency-Key": "batch_same_payload"},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json() == second.json()
    assert executor.execute_batch_transfers.await_count == 1


def test_batch_payment_idempotency_rejects_same_key_with_different_payload():
    client = _client()
    executor, executor_patch = _executor_patch()

    with executor_patch:
        first = client.post(
            "/api/v2/payments/batch",
            json=_payload("12.50"),
            headers={"Idempotency-Key": "batch_changed_payload"},
        )
        replay = client.post(
            "/api/v2/payments/batch",
            json=_payload("13.00"),
            headers={"Idempotency-Key": "batch_changed_payload"},
        )

    assert first.status_code == 201
    assert replay.status_code == 409
    assert replay.json()["detail"] == "idempotency_key_reuse_different_payload"
    assert executor.execute_batch_transfers.await_count == 1

from __future__ import annotations

import pytest
from fastapi import HTTPException
from fastapi.requests import Request

from sardis_server import idempotency
from sardis_server.authz import Principal


class _AppState:
    cache_service = None


class _App:
    state = _AppState()


def _request_without_cache() -> Request:
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [],
        "app": _App(),
    }
    return Request(scope)


def _principal() -> Principal:
    return Principal(
        kind="api_key",
        organization_id="org_test",
        scopes=["developer"],
    )


@pytest.mark.asyncio
async def test_db_fallback_rejects_same_key_with_different_payload(monkeypatch):
    async def fake_db_get(key: str) -> dict:
        assert key == "org_test:payments:idem_1"
        return {
            "status_code": 200,
            "body": {"payment_id": "pay_original"},
            "request_hash": "different-request-hash",
        }

    async def should_not_execute() -> tuple[int, dict]:
        raise AssertionError("idempotent function should not execute on mismatched DB record")

    monkeypatch.setattr(idempotency, "_db_get_idempotency", fake_db_get)

    with pytest.raises(HTTPException) as exc_info:
        await idempotency.run_idempotent(
            request=_request_without_cache(),
            principal=_principal(),
            operation="payments",
            key="idem_1",
            payload={"amount": "2.00", "currency": "USDC"},
            fn=should_not_execute,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "idempotency_key_reuse_different_payload"


@pytest.mark.asyncio
async def test_db_fallback_writes_request_hash(monkeypatch):
    writes: list[tuple[str, str, int, dict]] = []

    async def fake_db_get(key: str) -> None:
        return None

    async def fake_db_set(key: str, request_hash: str, status_code: int, body: dict) -> None:
        writes.append((key, request_hash, status_code, body))

    async def execute() -> tuple[int, dict]:
        return 201, {"payment_id": "pay_new"}

    monkeypatch.setattr(idempotency, "_db_get_idempotency", fake_db_get)
    monkeypatch.setattr(idempotency, "_db_set_idempotency", fake_db_set)

    response = await idempotency.run_idempotent(
        request=_request_without_cache(),
        principal=_principal(),
        operation="payments",
        key="idem_2",
        payload={"amount": "1.00", "currency": "USDC"},
        fn=execute,
    )

    assert response.status_code == 201
    assert writes == [
        (
            "org_test:payments:idem_2",
            idempotency._hash_payload({"amount": "1.00", "currency": "USDC"}),
            201,
            {"payment_id": "pay_new"},
        )
    ]

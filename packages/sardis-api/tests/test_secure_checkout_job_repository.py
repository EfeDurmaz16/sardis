from __future__ import annotations

from datetime import datetime, timezone
from datetime import timedelta
from decimal import Decimal

from sardis_v2_core.cache import create_cache_service
from sardis_api.repositories.secure_checkout_job_repository import SecureCheckoutJobRepository
from sardis_api.routers.secure_checkout import RepositoryBackedSecureCheckoutStore


def _sample_job(intent_id: str = "intent_repo_1") -> dict:
    now = datetime.now(timezone.utc)
    return {
        "job_id": "scj_repo_1",
        "intent_id": intent_id,
        "wallet_id": "wallet_1",
        "card_id": "card_1",
        "merchant_origin": "https://example.com",
        "merchant_mode": "tokenized_api",
        "status": "ready",
        "amount": Decimal("10.00"),
        "currency": "USD",
        "purpose": "agent_checkout",
        "approval_required": False,
        "approval_id": None,
        "policy_reason": "OK",
        "executor_ref": None,
        "secret_ref": None,
        "secret_expires_at": None,
        "redacted_card": {"last4": "4242"},
        "options": {"trace": False},
        "error_code": None,
        "error": None,
        "created_at": now,
        "updated_at": now,
    }


async def test_repository_memory_upsert_get_update():
    repo = SecureCheckoutJobRepository(dsn="memory://")
    created = await repo.upsert_job(_sample_job())
    assert created["job_id"] == "scj_repo_1"
    assert created["amount"] == Decimal("10.00")

    fetched = await repo.get_job("scj_repo_1")
    assert fetched is not None
    assert fetched["intent_id"] == "intent_repo_1"

    updated = await repo.update_job("scj_repo_1", status="dispatched", executor_ref="exec_1")
    assert updated is not None
    assert updated["status"] == "dispatched"
    assert updated["executor_ref"] == "exec_1"


async def test_repository_memory_upsert_idempotent_by_intent():
    repo = SecureCheckoutJobRepository(dsn="memory://")
    first = await repo.upsert_job(_sample_job(intent_id="intent_same"))
    second_payload = _sample_job(intent_id="intent_same")
    second_payload["job_id"] = "scj_repo_2"
    second = await repo.upsert_job(second_payload)

    assert first["job_id"] == second["job_id"]


async def test_repository_backed_store_shares_secret_refs_across_instances():
    repo = SecureCheckoutJobRepository(dsn="memory://")
    cache = create_cache_service(redis_url=None)
    store_a = RepositoryBackedSecureCheckoutStore(repo, cache_service=cache)
    store_b = RepositoryBackedSecureCheckoutStore(repo, cache_service=cache)

    secret_ref = "sec_shared_1"
    await store_a.put_secret(
        secret_ref,
        {
            "pan": "4111111111111111",
            "cvv": "123",
            "exp_month": 12,
            "exp_year": 2030,
            "merchant_origin": "https://example.com",
            "amount": "5.00",
            "currency": "USD",
            "purpose": "agent_checkout",
        },
        expires_at=datetime.now(timezone.utc) + timedelta(seconds=30),
    )

    consumed_first = await store_b.consume_secret(secret_ref)
    assert consumed_first is not None
    assert consumed_first["pan"] == "4111111111111111"

    consumed_second = await store_a.consume_secret(secret_ref)
    assert consumed_second is None

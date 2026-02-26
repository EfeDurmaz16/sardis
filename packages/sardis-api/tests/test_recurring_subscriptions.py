from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from sardis_api.authz import Principal, require_principal
from sardis_api.routers.subscriptions import (
    SubscriptionDependencies,
    get_deps,
    router,
)
from sardis_api.services.recurring_billing import RecurringBillingService, compute_next_billing


@dataclass
class _Wallet:
    wallet_id: str
    agent_id: str
    account_type: str = "mpc_v1"
    smart_account_address: str | None = None
    is_active: bool = True

    def get_address(self, chain: str) -> str:  # noqa: ARG002
        return "0x1234567890123456789012345678901234567890"


class _FakeWalletRepo:
    def __init__(self, wallet: _Wallet):
        self.wallet = wallet

    async def get(self, wallet_id: str):
        if wallet_id == self.wallet.wallet_id:
            return self.wallet
        return None


class _FakeAgentRepo:
    async def get(self, agent_id: str):
        if agent_id == "agent_1":
            return SimpleNamespace(agent_id="agent_1", owner_id="org_demo")
        return None


class _FakeSubscriptionRepo:
    def __init__(self):
        self.items: dict[str, dict] = {}
        self.billing_events: dict[str, dict] = {}

    async def create_subscription(self, **kwargs):
        sub_id = "sub_1"
        now = datetime.now(timezone.utc)
        row = {
            "id": sub_id,
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "failure_count": 0,
            "max_failures": kwargs.get("max_failures", 3),
            **kwargs,
        }
        self.items[sub_id] = row
        return row

    async def list_subscriptions(self, **kwargs):
        owner_id = kwargs.get("owner_id")
        rows = list(self.items.values())
        if owner_id:
            rows = [item for item in rows if item.get("owner_id") == owner_id]
        return rows

    async def get_subscription(self, subscription_id: str):
        return self.items.get(subscription_id)

    async def cancel_subscription(self, subscription_id: str):
        row = self.items.get(subscription_id)
        if not row:
            return False
        row["status"] = "cancelled"
        return True

    async def list_due_subscriptions(self, *, now: datetime, limit: int = 50):
        rows = [r for r in self.items.values() if r.get("status") == "active" and r.get("next_billing") <= now]
        return rows[:limit]

    async def create_billing_event(self, **kwargs):
        event = {"id": "bill_evt_1", **kwargs}
        self.billing_events[event["id"]] = event
        return event

    async def update_billing_event(self, event_id: str, **kwargs):
        event = self.billing_events[event_id]
        event.update(kwargs)
        return event

    async def mark_subscription_charged(self, subscription_id: str, **kwargs):
        row = self.items[subscription_id]
        row.update(
            {
                "last_charged_at": kwargs["charged_at"],
                "next_billing": kwargs["next_billing"],
                "failure_count": 0,
            }
        )
        return row

    async def mark_subscription_failed(self, subscription_id: str, **kwargs):
        row = self.items[subscription_id]
        row["failure_count"] = int(row.get("failure_count", 0)) + 1
        return row


class _FakeRPC:
    async def _call(self, method: str, params):  # noqa: ARG002
        # 100 USDC with 6 decimals.
        return hex(100_000_000)


class _FakeChainExecutor:
    def _get_rpc_client(self, chain: str):  # noqa: ARG002
        return _FakeRPC()

    async def dispatch_payment(self, mandate):  # noqa: ARG002
        return SimpleNamespace(tx_hash="0xabc123")


class _FakeWalletManager:
    async def async_validate_policies(self, mandate):  # noqa: ARG002
        return SimpleNamespace(allowed=True)

    async def async_record_spend(self, mandate):  # noqa: ARG002
        return None


class _FakeCompliance:
    async def preflight(self, mandate):  # noqa: ARG002
        return SimpleNamespace(allowed=True, reason=None)


def _admin_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["*"], api_key=None)


def _viewer_principal() -> Principal:
    return Principal(kind="api_key", organization_id="org_demo", scopes=["read"], api_key=None)


def _build_app(*, deps: SubscriptionDependencies, principal_fn) -> FastAPI:
    app = FastAPI()
    app.dependency_overrides[get_deps] = lambda: deps
    app.dependency_overrides[require_principal] = principal_fn
    app.include_router(router, prefix="/api/v2/subscriptions")
    return app


def test_compute_next_billing_monthly_rolls_month_boundary():
    dt = datetime(2026, 1, 31, 12, 0, tzinfo=timezone.utc)
    nxt = compute_next_billing(dt, "monthly", 31)
    assert nxt.month == 2
    assert nxt.day in {28, 29}


def test_subscriptions_router_create_and_list_scoped():
    wallet_repo = _FakeWalletRepo(_Wallet(wallet_id="wallet_1", agent_id="agent_1"))
    agent_repo = _FakeAgentRepo()
    sub_repo = _FakeSubscriptionRepo()
    recurring = RecurringBillingService(
        subscription_repo=sub_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=_FakeChainExecutor(),
        wallet_manager=_FakeWalletManager(),
        compliance=_FakeCompliance(),
    )
    deps = SubscriptionDependencies(
        subscription_repo=sub_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        recurring_service=recurring,
    )
    app = _build_app(deps=deps, principal_fn=_admin_principal)
    client = TestClient(app)

    create_resp = client.post(
        "/api/v2/subscriptions",
        json={
            "wallet_id": "wallet_1",
            "merchant": "notion.com",
            "amount": "15.00",
            "billing_cycle": "monthly",
            "billing_day": 1,
            "destination_address": "0x9999999999999999999999999999999999999999",
            "token": "USDC",
            "chain": "base_sepolia",
        },
    )
    assert create_resp.status_code == 201
    payload = create_resp.json()
    assert payload["owner_id"] == "org_demo"
    assert payload["amount_cents"] == 1500

    list_resp = client.get("/api/v2/subscriptions")
    assert list_resp.status_code == 200
    rows = list_resp.json()
    assert len(rows) == 1
    assert rows[0]["merchant"] == "notion.com"


def test_subscriptions_run_due_requires_admin():
    wallet_repo = _FakeWalletRepo(_Wallet(wallet_id="wallet_1", agent_id="agent_1"))
    agent_repo = _FakeAgentRepo()
    sub_repo = _FakeSubscriptionRepo()
    recurring = RecurringBillingService(
        subscription_repo=sub_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=_FakeChainExecutor(),
        wallet_manager=_FakeWalletManager(),
        compliance=_FakeCompliance(),
    )
    deps = SubscriptionDependencies(
        subscription_repo=sub_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        recurring_service=recurring,
    )
    app = _build_app(deps=deps, principal_fn=_viewer_principal)
    client = TestClient(app)
    resp = client.post("/api/v2/subscriptions/ops/run-due")
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_recurring_service_processes_due_subscription():
    wallet_repo = _FakeWalletRepo(_Wallet(wallet_id="wallet_1", agent_id="agent_1"))
    agent_repo = _FakeAgentRepo()
    sub_repo = _FakeSubscriptionRepo()
    now = datetime.now(timezone.utc)
    sub_repo.items["sub_1"] = {
        "id": "sub_1",
        "wallet_id": "wallet_1",
        "owner_id": "org_demo",
        "merchant": "notion.com",
        "amount_cents": 1500,
        "currency": "USD",
        "billing_cycle": "monthly",
        "billing_day": 1,
        "next_billing": now,
        "status": "active",
        "token": "USDC",
        "chain": "base_sepolia",
        "destination_address": "0x9999999999999999999999999999999999999999",
        "autofund_enabled": False,
        "failure_count": 0,
        "max_failures": 3,
    }
    recurring = RecurringBillingService(
        subscription_repo=sub_repo,
        wallet_repo=wallet_repo,
        agent_repo=agent_repo,
        chain_executor=_FakeChainExecutor(),
        wallet_manager=_FakeWalletManager(),
        compliance=_FakeCompliance(),
    )
    processed = await recurring.process_due_subscriptions(limit=10)
    assert len(processed) == 1
    assert processed[0].status == "charged"
    assert sub_repo.items["sub_1"]["failure_count"] == 0


@pytest.mark.asyncio
async def test_autofund_simulated_fallback_enabled_for_dev():
    recurring = RecurringBillingService(
        subscription_repo=_FakeSubscriptionRepo(),
        wallet_repo=_FakeWalletRepo(_Wallet(wallet_id="wallet_1", agent_id="agent_1")),
        agent_repo=_FakeAgentRepo(),
        chain_executor=_FakeChainExecutor(),
        wallet_manager=_FakeWalletManager(),
        compliance=_FakeCompliance(),
        allow_simulated_autofund=True,
    )
    tx_ref = await recurring._maybe_autofund({"id": "sub_dev", "autofund_enabled": True}, 1_250_000)  # noqa: SLF001
    assert tx_ref is not None
    assert tx_ref.startswith("autofund_sim_")


@pytest.mark.asyncio
async def test_autofund_live_mode_requires_handler():
    recurring = RecurringBillingService(
        subscription_repo=_FakeSubscriptionRepo(),
        wallet_repo=_FakeWalletRepo(_Wallet(wallet_id="wallet_1", agent_id="agent_1")),
        agent_repo=_FakeAgentRepo(),
        chain_executor=_FakeChainExecutor(),
        wallet_manager=_FakeWalletManager(),
        compliance=_FakeCompliance(),
        allow_simulated_autofund=False,
    )
    with pytest.raises(RuntimeError, match="autofund_handler_not_configured"):
        await recurring._maybe_autofund({"id": "sub_live", "autofund_enabled": True}, 2_500_000)  # noqa: SLF001

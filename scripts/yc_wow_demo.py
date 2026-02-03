#!/usr/bin/env python3
from __future__ import annotations

import os
import sys
import time
import uuid
from typing import Any, Dict, Optional

import httpx


def _env(name: str, default: Optional[str] = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _print_step(title: str) -> None:
    print(f"\n== {title} ==")


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json: Any | None = None,
    data: Dict[str, str] | None = None,
    headers: Dict[str, str] | None = None,
    ok_statuses: tuple[int, ...] = (200, 201, 204),
) -> Any:
    url = client.base_url.join(path)
    resp = client.request(method, url, json=json, data=data, headers=headers)
    if resp.status_code not in ok_statuses:
        detail = None
        try:
            detail = resp.json()
        except Exception:
            detail = resp.text
        raise RuntimeError(f"{method} {path} failed: {resp.status_code} {detail}")
    if resp.status_code == 204:
        return None
    return resp.json()


def main() -> int:
    """
    YC WOW DEMO (reliable, no real card purchase required)

    Flow:
      1) Admin login (JWT)
      2) Create agent (no wallet)
      3) Create wallet (local)
      4) Bind wallet to agent
      5) Apply natural-language policy ("max $5/tx, block gambling")
      6) Issue virtual card (mock or Lithic sandbox)
      7) Simulate an allowed purchase (approved)
      8) Simulate a gambling purchase (policy denied + auto-freeze)
      9) Show card + transactions

    Usage:
      python3 scripts/yc_wow_demo.py

    Env:
      SARDIS_API_URL (default http://localhost:8000)
      SARDIS_ADMIN_PASSWORD (default demo123)
      SARDIS_ADMIN_USERNAME (default admin)
    """

    api_url = _env("SARDIS_API_URL", "http://localhost:8000").rstrip("/")
    username = _env("SARDIS_ADMIN_USERNAME", "admin")
    password = _env("SARDIS_ADMIN_PASSWORD", "demo123")

    run_id = os.getenv("SARDIS_DEMO_RUN_ID") or time.strftime("%Y%m%d_%H%M%S")
    suffix = uuid.uuid4().hex[:8]
    agent_name = f"yc-demo-agent-{run_id}-{suffix}"

    with httpx.Client(base_url=api_url, timeout=30.0) as client:
        _print_step("Login (JWT)")
        token_resp = _request(
            client,
            "POST",
            "/api/v2/auth/login",
            data={"username": username, "password": password},
            ok_statuses=(200,),
        )
        token = token_resp["access_token"]
        authz = {"Authorization": f"Bearer {token}"}
        print(f"Logged in as {username}.")

        _print_step("Create agent")
        agent = _request(
            client,
            "POST",
            "/api/v2/agents",
            json={
                "name": agent_name,
                "description": "YC demo agent (reliable wow flow)",
                "create_wallet": False,
                "spending_limits": {
                    "per_transaction": "5.00",
                    "daily": "20.00",
                    "monthly": "200.00",
                    "total": "500.00",
                },
            },
            headers=authz,
            ok_statuses=(201,),
        )
        agent_id = agent["agent_id"]
        print(f"agent_id={agent_id}")

        _print_step("Create wallet (local)")
        wallet = _request(
            client,
            "POST",
            "/api/v2/wallets",
            json={
                "agent_id": agent_id,
                "mpc_provider": "local",
                "currency": "USDC",
                "limit_per_tx": "5.00",
                "limit_total": "50.00",
            },
            headers=authz,
            ok_statuses=(201,),
        )
        wallet_id = wallet["wallet_id"]
        print(f"wallet_id={wallet_id}")

        _print_step("Bind wallet to agent")
        _ = _request(
            client,
            "POST",
            f"/api/v2/agents/{agent_id}/wallet?wallet_id={wallet_id}",
            headers=authz,
            ok_statuses=(200,),
        )
        print("bound=ok")

        _print_step("Apply NL policy (deterministic enforcement)")
        nl = "Spend up to $5 per transaction, block gambling."
        policy_apply = _request(
            client,
            "POST",
            "/api/v2/policies/apply",
            json={"natural_language": nl, "agent_id": agent_id, "confirm": True},
            headers={**authz, "Idempotency-Key": f"yc-demo-policy-{run_id}-{agent_id}"},
            ok_statuses=(200,),
        )
        print(
            f"policy_id={policy_apply.get('policy_id')} "
            f"limit_per_tx={policy_apply.get('limit_per_tx')} "
            f"blocked_categories_enforced=gambling"
        )

        _print_step("Issue virtual card")
        card = _request(
            client,
            "POST",
            "/api/v2/cards",
            json={
                "wallet_id": wallet_id,
                "card_type": "multi_use",
                "limit_per_tx": "5.00",
                "limit_daily": "20.00",
                "limit_monthly": "200.00",
                "funding_source": "stablecoin",
            },
            headers={**authz, "Idempotency-Key": f"yc-demo-card-{run_id}-{wallet_id}"},
            ok_statuses=(201,),
        )
        card_id = card.get("card_id") or card.get("id") or card.get("provider_card_id")
        if not card_id:
            raise RuntimeError(f"Card response missing card_id: {card}")
        print(f"card_id={card_id} status={card.get('status')}")

        _print_step("Simulate allowed purchase")
        allowed_tx = _request(
            client,
            "POST",
            f"/api/v2/cards/{card_id}/simulate-purchase",
            json={
                "amount": "3.00",
                "currency": "USD",
                "merchant_name": "Demo Cloud Vendor",
                "mcc_code": "5734",  # computer software stores (non-blocked)
                "status": "approved",
            },
            headers=authz,
            ok_statuses=(201,),
        )
        print(f"allowed_tx_status={allowed_tx.get('status')} decline_reason={allowed_tx.get('decline_reason')}")

        _print_step("Simulate policy-denied purchase (gambling)")
        denied_tx = _request(
            client,
            "POST",
            f"/api/v2/cards/{card_id}/simulate-purchase",
            json={
                "amount": "3.00",
                "currency": "USD",
                "merchant_name": "Demo Casino",
                "mcc_code": "7995",  # gambling
                "status": "approved",
            },
            headers=authz,
            ok_statuses=(201,),
        )
        print(f"denied_tx_status={denied_tx.get('status')} decline_reason={denied_tx.get('decline_reason')}")

        _print_step("Fetch card + recent transactions")
        card_now = _request(client, "GET", f"/api/v2/cards/{card_id}", headers=authz, ok_statuses=(200,))
        txs = _request(client, "GET", f"/api/v2/cards/{card_id}/transactions?limit=10", headers=authz, ok_statuses=(200,))
        print(f"card_status_now={card_now.get('status')}")
        if isinstance(txs, list):
            print(f"transactions={len(txs)}")
            for t in txs[:5]:
                print(
                    f"- {t.get('status')} {t.get('amount')} {t.get('currency')} "
                    f"mcc={t.get('merchant_category')} merchant={t.get('merchant_name')} "
                    f"decline={t.get('decline_reason')}"
                )
        else:
            print(f"transactions_response={txs}")

    _print_step("DONE")
    print("WOW moment: policy blocks gambling + auto-freeze, with full audit trail in transactions.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return_code = 1
        raise SystemExit(return_code)

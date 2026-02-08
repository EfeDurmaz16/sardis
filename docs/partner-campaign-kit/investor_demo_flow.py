#!/usr/bin/env python3
"""Investor demo orchestrator for Sardis (YC / VC 2-3 min flow).

Hybrid-live design:
- Uses real staging/local API for the core path.
- Falls back gracefully on unstable external edges (only in hybrid mode).
- Produces machine + human artifacts for video editing.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


@dataclass
class DemoStep:
    name: str
    status: str
    started_at: str
    completed_at: str
    details: dict[str, Any] = field(default_factory=dict)


class DemoRun:
    def __init__(self) -> None:
        self.run_id = time.strftime("%Y%m%d_%H%M%S")
        self.steps: list[DemoStep] = []
        self.context: dict[str, Any] = {}

    def add_step(self, *, name: str, status: str, started: float, details: dict[str, Any]) -> None:
        self.steps.append(
            DemoStep(
                name=name,
                status=status,
                started_at=datetime.fromtimestamp(started, tz=timezone.utc).isoformat(),
                completed_at=datetime.now(timezone.utc).isoformat(),
                details=details,
            )
        )


def _env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if value is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _print_header(title: str) -> None:
    print(f"\n== {title} ==")


def _request(
    client: httpx.Client,
    method: str,
    path: str,
    *,
    json_body: Any | None = None,
    data: dict[str, str] | None = None,
    headers: dict[str, str] | None = None,
    ok_statuses: tuple[int, ...] = (200, 201, 204),
) -> Any:
    response = client.request(method, path, json=json_body, data=data, headers=headers)
    if response.status_code not in ok_statuses:
        try:
            detail = response.json()
        except Exception:
            detail = response.text
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {detail}")
    if response.status_code == 204:
        return None
    return response.json()


def write_artifacts(run: DemoRun, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"investor-demo-{run.run_id}.json"
    md_path = output_dir / f"investor-demo-{run.run_id}.md"

    payload = {
        "run_id": run.run_id,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "context": run.context,
        "steps": [step.__dict__ for step in run.steps],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"# Sardis Investor Demo Transcript ({run.run_id})",
        "",
        "## Context",
        f"- API URL: {run.context.get('api_url', '')}",
        f"- Mode: {run.context.get('mode', '')}",
        f"- Agent ID: {run.context.get('agent_id', '')}",
        f"- Wallet ID: {run.context.get('wallet_id', '')}",
        f"- Card ID: {run.context.get('card_id', '')}",
        "",
        "## Timeline",
    ]

    for idx, step in enumerate(run.steps, start=1):
        lines.extend(
            [
                f"{idx}. **{step.name}** — `{step.status}`",
                f"   - Started: {step.started_at}",
                f"   - Completed: {step.completed_at}",
                f"   - Details: `{json.dumps(step.details, ensure_ascii=True)}`",
            ]
        )
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"\nArtifacts written:\n- {json_path}\n- {md_path}")


def run_demo(args: argparse.Namespace) -> DemoRun:
    run = DemoRun()
    run.context["api_url"] = args.api_url
    run.context["mode"] = args.mode

    with httpx.Client(base_url=args.api_url, timeout=30.0) as client:
        # 1) Login
        started = time.time()
        _print_header("1) Admin login")
        token_resp = _request(
            client,
            "POST",
            "/api/v2/auth/login",
            data={"username": args.username, "password": args.password},
            ok_statuses=(200,),
        )
        token = token_resp["access_token"]
        jwt_headers = {"Authorization": f"Bearer {token}"}
        run.add_step(name="admin_login", status="ok", started=started, details={"username": args.username})

        # 2) Bootstrap API key
        started = time.time()
        _print_header("2) Bootstrap API key")
        key_resp = _request(
            client,
            "POST",
            "/api/v2/auth/bootstrap-api-key",
            json_body={"name": f"Investor Demo Key {run.run_id}", "scopes": ["*"]},
            headers=jwt_headers,
            ok_statuses=(200, 201),
        )
        api_key = key_resp["key"]
        key_headers = {"X-API-Key": api_key}
        run.add_step(name="bootstrap_api_key", status="ok", started=started, details={"key_prefix": api_key[:12]})

        # 3) Create agent
        started = time.time()
        _print_header("3) Create agent (no wallet)")
        agent_name = f"investor-demo-agent-{run.run_id}-{uuid.uuid4().hex[:6]}"
        agent_resp = _request(
            client,
            "POST",
            "/api/v2/agents",
            json_body={"name": agent_name, "description": "Investor demo agent", "create_wallet": False},
            headers=jwt_headers,
            ok_statuses=(201,),
        )
        agent_id = agent_resp["agent_id"]
        run.context["agent_id"] = agent_id
        run.add_step(name="create_agent", status="ok", started=started, details={"agent_id": agent_id})

        # 4) One-click payment identity (ensures wallet)
        started = time.time()
        _print_header("4) Create payment identity")
        payment_identity = _request(
            client,
            "POST",
            f"/api/v2/agents/{agent_id}/payment-identity",
            json_body={
                "ttl_seconds": args.identity_ttl_seconds,
                "mode": "live",
                "chain": args.chain,
                "ensure_wallet": True,
            },
            headers=jwt_headers,
            ok_statuses=(200,),
        )
        wallet_id = payment_identity["wallet_id"]
        run.context["wallet_id"] = wallet_id
        run.context["payment_identity_id"] = payment_identity["payment_identity_id"]
        run.add_step(
            name="create_payment_identity",
            status="ok",
            started=started,
            details={
                "wallet_id": wallet_id,
                "payment_identity_id_prefix": payment_identity["payment_identity_id"][:24],
                "mcp_init_snippet": payment_identity["mcp_init_snippet"],
            },
        )

        # 5) Apply natural language policy
        started = time.time()
        _print_header("5) Apply natural language policy")
        policy_resp = _request(
            client,
            "POST",
            "/api/v2/policies/apply",
            json_body={
                "agent_id": agent_id,
                "natural_language": (
                    "Allow OpenAI and AWS software purchases up to $5 per transaction, "
                    "block gambling, require approval above $3."
                ),
                "confirm": True,
            },
            headers=jwt_headers,
            ok_statuses=(200,),
        )
        run.add_step(
            name="apply_policy",
            status="ok",
            started=started,
            details={"policy_id": policy_resp.get("policy_id"), "limit_per_tx": policy_resp.get("limit_per_tx")},
        )

        # 6) Policy check (blocked)
        started = time.time()
        _print_header("6) Policy check blocked branch")
        blocked = _request(
            client,
            "POST",
            "/api/v2/policies/check",
            json_body={
                "agent_id": agent_id,
                "amount": "3.00",
                "currency": "USD",
                "merchant_category": "gambling",
                "mcc_code": "7995",
            },
            headers=jwt_headers,
            ok_statuses=(200,),
        )
        run.add_step(name="policy_check_blocked", status="ok", started=started, details=blocked)

        # 7) Issue virtual card
        started = time.time()
        _print_header("7) Issue virtual card")
        card_resp = _request(
            client,
            "POST",
            "/api/v2/cards",
            json_body={
                "wallet_id": wallet_id,
                "card_type": "multi_use",
                "limit_per_tx": "5.00",
                "limit_daily": "20.00",
                "limit_monthly": "200.00",
                "funding_source": "stablecoin",
            },
            headers=jwt_headers,
            ok_statuses=(201,),
        )
        card_id = card_resp.get("card_id") or card_resp.get("id")
        if not card_id:
            raise RuntimeError(f"Card response missing id: {card_resp}")
        run.context["card_id"] = card_id
        run.add_step(name="issue_card", status="ok", started=started, details={"card_id": card_id})

        # 8) Simulate denied purchase (policy freeze path)
        started = time.time()
        _print_header("8) Simulate denied purchase")
        denied = _request(
            client,
            "POST",
            f"/api/v2/cards/{card_id}/simulate-purchase",
            json_body={
                "amount": "3.00",
                "currency": "USD",
                "merchant_name": "Demo Casino",
                "mcc_code": "7995",
                "status": "approved",
            },
            headers=jwt_headers,
            ok_statuses=(201,),
        )
        run.add_step(
            name="simulate_denied_purchase",
            status="ok",
            started=started,
            details={"policy": denied.get("policy"), "transaction": denied.get("transaction")},
        )

        # Optional unfreeze to demonstrate operator control
        started = time.time()
        _print_header("9) Unfreeze card")
        unfreeze = _request(
            client,
            "POST",
            f"/api/v2/cards/{card_id}/unfreeze",
            headers=jwt_headers,
            ok_statuses=(200,),
        )
        run.add_step(name="unfreeze_card", status="ok", started=started, details={"status": unfreeze.get("status")})

        # 10) Simulate allowed purchase
        started = time.time()
        _print_header("10) Simulate allowed purchase")
        allowed = _request(
            client,
            "POST",
            f"/api/v2/cards/{card_id}/simulate-purchase",
            json_body={
                "amount": "2.50",
                "currency": "USD",
                "merchant_name": "OpenAI",
                "mcc_code": "5734",
                "status": "approved",
            },
            headers=jwt_headers,
            ok_statuses=(201,),
        )
        run.add_step(
            name="simulate_allowed_purchase",
            status="ok",
            started=started,
            details={"policy": allowed.get("policy"), "transaction": allowed.get("transaction")},
        )

        # 11) Agent-initiated wallet transfer (real path / fallback)
        started = time.time()
        _print_header("11) Agent-initiated stablecoin transfer")
        transfer_status = "ok"
        transfer_details: dict[str, Any]
        try:
            transfer = _request(
                client,
                "POST",
                f"/api/v2/wallets/{wallet_id}/transfer",
                json_body={
                    "destination": args.transfer_destination,
                    "amount": args.transfer_amount,
                    "token": "USDC",
                    "chain": args.chain,
                    "domain": "OpenAI",
                    "memo": "Investor demo transfer",
                },
                headers=key_headers,
                ok_statuses=(200, 201),
            )
            transfer_details = transfer
        except Exception as exc:
            if args.mode == "hybrid-live":
                transfer_status = "fallback"
                transfer_details = {
                    "fallback": "chain_transfer_unavailable",
                    "error": str(exc),
                    "note": "Core flow continued under hybrid-live mode.",
                }
            else:
                raise
        run.add_step(
            name="wallet_transfer",
            status=transfer_status,
            started=started,
            details=transfer_details,
        )

        # 12) Card cancellation decision
        started = time.time()
        _print_header("12) Cancel card decision")
        cancel = _request(
            client,
            "DELETE",
            f"/api/v2/cards/{card_id}",
            headers=jwt_headers,
            ok_statuses=(200,),
        )
        run.add_step(name="cancel_card", status="ok", started=started, details={"status": cancel.get("status")})

    return run


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Sardis investor demo flow orchestrator")
    parser.add_argument("--api-url", default=_env("SARDIS_API_URL", "http://localhost:8000"))
    parser.add_argument("--username", default=_env("SARDIS_ADMIN_USERNAME", "admin"))
    parser.add_argument("--password", default=_env("SARDIS_ADMIN_PASSWORD", "demo123"))
    parser.add_argument("--mode", choices=("hybrid-live", "fully-live", "scripted"), default="hybrid-live")
    parser.add_argument("--chain", default="base_sepolia")
    parser.add_argument("--identity-ttl-seconds", type=int, default=86400)
    parser.add_argument("--transfer-amount", default="0.10")
    parser.add_argument("--transfer-destination", default="0x000000000000000000000000000000000000dEaD")
    parser.add_argument("--output-dir", default="artifacts/investor-demo")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.mode == "scripted":
        print("scripted mode is reserved for future UI-only demos; use hybrid-live for now.", file=sys.stderr)
        return 2

    run = run_demo(args)
    write_artifacts(run, Path(args.output_dir))

    print("\nDemo run complete.")
    print(f"Run ID: {run.run_id}")
    print(f"Agent ID: {run.context.get('agent_id')}")
    print(f"Wallet ID: {run.context.get('wallet_id')}")
    print(f"Card ID: {run.context.get('card_id')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

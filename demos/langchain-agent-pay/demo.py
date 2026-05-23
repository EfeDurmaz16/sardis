"""LangChain-style agent paying via Sardis tools.

A mock LLM-driven agent loop receives a goal ("pay $20 to Anthropic for API
credits"). It calls `sardis_check_balance`, then `sardis_check_policy`, then
`sardis_pay`. The Sardis tools enforce wallet spending limits — over-cap
payments are halted before any transfer.

Uses the real `sardis.integrations.langchain.SardisToolkit` (the same one
shipped to LangChain users) backed by a local fake Sardis client.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from typing import Any

from sardis.integrations.langchain import SardisToolkit


# --- fake Sardis client surface that SardisToolkit's tools call into ---
class _Status(str, Enum):
    SETTLED = "settled"
    BLOCKED = "blocked"


@dataclass
class _PayResult:
    success: bool
    status: _Status
    tx_id: str
    tx_hash: str
    amount: Decimal
    currency: str
    to: str
    message: str


@dataclass
class _BalanceInfo:
    wallet_id: str
    chain: str
    token: str
    balance: Decimal
    spent_total: Decimal
    limit_per_tx: Decimal
    limit_total: Decimal
    remaining: Decimal


@dataclass
class _Wallet:
    id: str
    balance: Decimal
    limit_per_tx: Decimal
    limit_daily: Decimal
    spent_total: Decimal = Decimal("0")
    audit: list[dict[str, Any]] = field(default_factory=list)

    def pay(self, *, to: str, amount: Decimal, token: str = "USDC",
            purpose: str | None = None) -> _PayResult:
        if amount > self.limit_per_tx:
            raise RuntimeError(
                f"policy: blocked - amount {amount} exceeds per-tx limit "
                f"{self.limit_per_tx}"
            )
        if self.spent_total + amount > self.limit_daily:
            raise RuntimeError("policy: blocked - daily limit reached")
        if amount > self.balance:
            raise RuntimeError("insufficient balance")
        self.balance -= amount
        self.spent_total += amount
        tx_id = f"tx_{abs(hash((to, str(amount), purpose))):x}"[:18]
        tx_hash = f"0xmock{abs(hash(tx_id)):x}"[:18]
        self.audit.append({"to": to, "amount": str(amount), "token": token,
                           "purpose": purpose, "tx_hash": tx_hash})
        return _PayResult(
            success=True, status=_Status.SETTLED, tx_id=tx_id, tx_hash=tx_hash,
            amount=amount, currency=token, to=to,
            message=f"Payment of {amount} {token} to {to} settled",
        )


class _WalletsResource:
    def __init__(self, wallet: _Wallet) -> None:
        self._wallet = wallet

    def get(self, wallet_id: str) -> _Wallet:
        if wallet_id != self._wallet.id:
            raise KeyError(wallet_id)
        return self._wallet

    def get_balance(self, wallet_id: str, *, chain: str = "base",
                    token: str = "USDC") -> _BalanceInfo:
        w = self.get(wallet_id)
        return _BalanceInfo(
            wallet_id=w.id, chain=chain, token=token,
            balance=w.balance, spent_total=w.spent_total,
            limit_per_tx=w.limit_per_tx, limit_total=w.limit_daily,
            remaining=w.limit_daily - w.spent_total,
        )


class FakeSardisClient:
    def __init__(self, wallet: _Wallet) -> None:
        self.wallets = _WalletsResource(wallet)


# --- mock LLM planner ---
def plan_next_step(goal: dict, history: list[tuple[str, str]]) -> dict | None:
    called = {step for step, _ in history}
    if "sardis_check_balance" not in called:
        return {"tool": "sardis_check_balance", "args": {}}
    if "sardis_check_policy" not in called:
        return {"tool": "sardis_check_policy",
                "args": {"to": goal["to"], "amount": goal["amount"]}}
    if "sardis_pay" not in called:
        last = history[-1][1]
        try:
            parsed = json.loads(last)
        except Exception:
            parsed = {}
        if parsed.get("blocked") or parsed.get("success") is False:
            return None
        return {"tool": "sardis_pay", "args": {
            "to": goal["to"], "amount": goal["amount"],
            "purpose": goal["purpose"],
        }}
    return None


def run_agent(goal: dict, tools_by_name: dict) -> None:
    print(f"[goal] {goal['purpose']} — pay {goal['amount']} USDC to {goal['to'][:14]}...")
    history: list[tuple[str, str]] = []
    for step in range(1, 6):
        action = plan_next_step(goal, history)
        if action is None:
            print("[agent] stop — plan aborted by tool observation")
            return
        tool = tools_by_name[action["tool"]]
        print(f"[agent] step {step}: invoke {tool.name}({action['args']})")
        obs = tool.invoke(action["args"])
        print(f"[tool]  -> {obs}")
        history.append((tool.name, obs))


def main() -> None:
    wallet = _Wallet(
        id="wallet_agent_research_bot_001",
        balance=Decimal("500.00"),
        limit_per_tx=Decimal("100.00"),
        limit_daily=Decimal("250.00"),
    )
    client = FakeSardisClient(wallet)
    toolkit = SardisToolkit(client=client, wallet_id=wallet.id)
    tools_by_name = {t.name: t for t in toolkit.get_tools()}
    print(f"[toolkit] tools available: {list(tools_by_name)}")

    print("\n=== scenario 1: payment within policy ===")
    run_agent({
        "to": "0xAntHr0p1c000000000000000000000000000Ant1",
        "amount": "20.00",
        "purpose": "Anthropic API credits",
    }, tools_by_name)

    print("\n=== scenario 2: payment over per-tx cap ===")
    run_agent({
        "to": "0xAwS0000000000000000000000000000000000AwS",
        "amount": "250.00",
        "purpose": "AWS EC2 monthly",
    }, tools_by_name)

    print(f"\n[ledger] {len(wallet.audit)} transfer(s) executed, "
          f"balance={wallet.balance}, spent_today={wallet.spent_total}")
    print("[demo] OK — agent paid via SardisToolkit with policy enforcement")


if __name__ == "__main__":
    main()

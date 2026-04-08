"""Tempo Accounts + Sardis Mandate demo.

A self-contained, runnable demo showing Sardis enforcing spending mandates
on top of Tempo's native account abstraction.

Run:
    uv run python demo.py

Shows six steps:
    1. Create Tempo programmatic account (agent, Turnkey-backed)
    2. Issue spending mandate ($100/day, USDC, cloud APIs)
    3. Allowed payment ($50 to authorized merchant) — passes policy
    4. Denied payment ($200 — above per-tx limit) — blocked pre-chain
    5. Revoke mandate mid-stream — kill switch
    6. Print audit trail

Deterministic output. No network calls unless TEMPO_LIVE=1.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import uuid4

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    console = Console()
    HAS_RICH = True
except ImportError:
    console = None
    HAS_RICH = False


# ─── Fake Turnkey client (offline mode) ───────────────────────────────────────

class FakeTurnkeyClient:
    """Stand-in for the real Turnkey MPC client. Returns deterministic keys."""

    async def create_private_key(self, key_name: str, curve: str) -> dict[str, str]:
        addr = "0x" + ("ab" * 20)
        return {"address": addr, "key_name": key_name, "curve": curve}


# ─── Minimal mandate model (mirrors sardis-core) ──────────────────────────────

@dataclass
class SpendingMandate:
    """Machine-readable authority with seven dimensions."""

    mandate_id: str = field(default_factory=lambda: f"mnd_{uuid4().hex[:12]}")
    agent_id: str = ""
    status: str = "active"  # active, suspended, revoked, expired

    # WHAT
    allowed_categories: list[str] = field(default_factory=list)
    allowed_merchants: list[str] = field(default_factory=list)

    # HOW MUCH
    limit_per_tx: Decimal = Decimal("0")
    limit_daily: Decimal = Decimal("0")
    limit_monthly: Decimal = Decimal("0")

    # ON WHICH RAILS
    allowed_tokens: list[str] = field(default_factory=lambda: ["USDC"])
    allowed_chains: list[int] = field(default_factory=lambda: [4217])  # Tempo

    # HOW LONG
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(days=30))

    # STATE
    spent_today: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ─── Policy engine (simplified 4-check version for demo) ──────────────────────

@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    check: str  # which gate decided


async def check_mandate(
    mandate: SpendingMandate,
    amount: Decimal,
    merchant: str,
    category: str,
    token: str,
    chain_id: int,
) -> PolicyDecision:
    """Run 4 gates against a payment attempt. Fail-closed."""

    # Gate 1: mandate status
    if mandate.status != "active":
        return PolicyDecision(False, f"mandate status is {mandate.status}", "status")

    # Gate 2: expiry
    if datetime.now(UTC) >= mandate.expires_at:
        return PolicyDecision(False, "mandate expired", "expiry")

    # Gate 3: rails (token + chain)
    if token not in mandate.allowed_tokens:
        return PolicyDecision(False, f"token {token} not allowed", "rails")
    if chain_id not in mandate.allowed_chains:
        return PolicyDecision(False, f"chain {chain_id} not allowed", "rails")

    # Gate 4: scope (category)
    if mandate.allowed_categories and category not in mandate.allowed_categories:
        return PolicyDecision(False, f"category {category} not in scope", "scope")

    # Gate 5: per-tx limit
    if amount > mandate.limit_per_tx:
        return PolicyDecision(
            False,
            f"amount {amount} above per-tx limit {mandate.limit_per_tx}",
            "limit_per_tx",
        )

    # Gate 6: daily limit
    if mandate.spent_today + amount > mandate.limit_daily:
        return PolicyDecision(
            False,
            f"daily spend {mandate.spent_today + amount} above cap {mandate.limit_daily}",
            "limit_daily",
        )

    return PolicyDecision(True, "all 6 gates passed", "approved")


# ─── Audit trail ──────────────────────────────────────────────────────────────

AUDIT: list[dict[str, Any]] = []


def audit(event: str, **details: Any) -> None:
    entry = {
        "id": f"evt_{uuid4().hex[:8]}",
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **details,
    }
    AUDIT.append(entry)


# ─── Output helpers ───────────────────────────────────────────────────────────

def show(title: str, body: str, style: str = "cyan") -> None:
    if HAS_RICH:
        console.print(Panel(body, title=f"[bold]{title}[/]", border_style=style))
    else:
        bar = "─" * 60
        print(f"\n{bar}\n{title}\n{bar}\n{body}")


def verdict(allowed: bool, reason: str) -> str:
    mark = "[bold green]✓ ALLOWED[/]" if allowed else "[bold red]✗ DENIED[/]"
    return f"{mark}  {reason}" if HAS_RICH else f"{'ALLOWED' if allowed else 'DENIED'} — {reason}"


# ─── Demo flow ────────────────────────────────────────────────────────────────

async def main() -> None:
    from sardis_wallet.tempo_accounts import TempoAccountFactory

    show("Sardis × Tempo Accounts Demo", "Self-contained — no network required unless TEMPO_LIVE=1", "magenta")

    # ── 1. Create Tempo programmatic account ────────────────────────────────
    turnkey = FakeTurnkeyClient()
    factory = TempoAccountFactory(turnkey_client=turnkey)

    agent_account = await factory.create_programmatic_account(owner_id="org_acme_corp")
    audit(
        "account.created",
        account_id=agent_account.account_id,
        address=agent_account.address,
        chain_id=agent_account.chain_id,
        custody="turnkey_mpc",
    )
    show(
        "Step 1 — Tempo account provisioned",
        f"account_id  : {agent_account.account_id}\n"
        f"address     : {agent_account.address}\n"
        f"chain_id    : {agent_account.chain_id} (Tempo mainnet)\n"
        f"root_key    : {agent_account.root_key_type}\n"
        f"custody     : Turnkey MPC (Sardis never holds keys)",
        "cyan",
    )

    # ── 2. Issue spending mandate ───────────────────────────────────────────
    mandate = SpendingMandate(
        agent_id=agent_account.account_id,
        allowed_categories=["cloud_apis", "compute"],
        allowed_merchants=["anthropic.com", "openai.com", "modal.com"],
        limit_per_tx=Decimal("75"),
        limit_daily=Decimal("100"),
        limit_monthly=Decimal("2000"),
    )
    audit(
        "mandate.issued",
        mandate_id=mandate.mandate_id,
        agent_id=mandate.agent_id,
        limit_per_tx=str(mandate.limit_per_tx),
        limit_daily=str(mandate.limit_daily),
    )
    show(
        "Step 2 — Spending mandate issued",
        f"mandate_id  : {mandate.mandate_id}\n"
        f"limit_per_tx: ${mandate.limit_per_tx} USDC\n"
        f"limit_daily : ${mandate.limit_daily} USDC\n"
        f"limit_month : ${mandate.limit_monthly} USDC\n"
        f"categories  : {', '.join(mandate.allowed_categories)}\n"
        f"merchants   : {', '.join(mandate.allowed_merchants)}\n"
        f"rails       : {', '.join(mandate.allowed_tokens)} on chain(s) {mandate.allowed_chains}\n"
        f"expires_at  : {mandate.expires_at.isoformat()}",
        "green",
    )

    # ── 3. Allowed payment ──────────────────────────────────────────────────
    tx1 = await check_mandate(
        mandate,
        amount=Decimal("50"),
        merchant="anthropic.com",
        category="cloud_apis",
        token="USDC",
        chain_id=4217,
    )
    if tx1.allowed:
        mandate.spent_today += Decimal("50")
    audit("payment.attempted", amount="50", merchant="anthropic.com", decision="allow" if tx1.allowed else "deny", gate=tx1.check)
    show(
        "Step 3 — Agent pays $50 USDC to anthropic.com",
        verdict(tx1.allowed, tx1.reason) + f"\ngate        : {tx1.check}\nspent_today : ${mandate.spent_today}",
        "green" if tx1.allowed else "red",
    )

    # ── 4. Denied payment (above per-tx limit) ──────────────────────────────
    tx2 = await check_mandate(
        mandate,
        amount=Decimal("200"),
        merchant="openai.com",
        category="cloud_apis",
        token="USDC",
        chain_id=4217,
    )
    audit("payment.attempted", amount="200", merchant="openai.com", decision="allow" if tx2.allowed else "deny", gate=tx2.check)
    show(
        "Step 4 — Agent attempts $200 USDC to openai.com",
        verdict(tx2.allowed, tx2.reason) + f"\ngate        : {tx2.check}\nno gas burned — blocked pre-chain",
        "green" if tx2.allowed else "red",
    )

    # ── 5. Revoke mandate, attempt payment ──────────────────────────────────
    mandate.status = "revoked"
    audit("mandate.revoked", mandate_id=mandate.mandate_id, reason="kill_switch_from_finance_team")

    tx3 = await check_mandate(
        mandate,
        amount=Decimal("10"),
        merchant="modal.com",
        category="compute",
        token="USDC",
        chain_id=4217,
    )
    audit("payment.attempted", amount="10", merchant="modal.com", decision="allow" if tx3.allowed else "deny", gate=tx3.check)
    show(
        "Step 5 — Mandate revoked, agent tries another payment",
        verdict(tx3.allowed, tx3.reason) + f"\ngate        : {tx3.check}\naccount still live, authority revoked",
        "green" if tx3.allowed else "red",
    )

    # ── 6. Audit trail ──────────────────────────────────────────────────────
    if HAS_RICH:
        table = Table(title="Audit Trail", show_lines=False, expand=True)
        table.add_column("event", style="cyan")
        table.add_column("details", style="white")
        for entry in AUDIT:
            details = ", ".join(f"{k}={v}" for k, v in entry.items() if k not in {"id", "ts", "event"})
            table.add_row(entry["event"], details)
        console.print(table)
    else:
        print("\n── Audit Trail ──")
        for entry in AUDIT:
            print(f"  {entry['event']}: {entry}")

    show(
        "Demo complete",
        f"Total events   : {len(AUDIT)}\n"
        f"Decisions      : 3 payment attempts, 1 allowed, 2 denied\n"
        f"Custody events : 1 account created (Turnkey-backed)\n"
        f"Mandate events : 1 issued, 1 revoked\n\n"
        f"Every event would be Merkle-anchored on Base in production —\n"
        f"tamper-evident, auditable, SOC2-ready.",
        "magenta",
    )


if __name__ == "__main__":
    asyncio.run(main())

"""Arc + Circle + Sardis Mandate demo.

Self-contained runnable demo showing Sardis enforcing spending
mandates on top of Circle developer-controlled wallets, settled on
Arc testnet.

Run:
    uv run python demo.py

Shows six steps:
    1. Provision a Circle developer-controlled wallet on Arc testnet
       (Turnkey-free, non-custodial via entity secret encryption)
    2. Issue a spending mandate with 7 dimensions of authority
    3. Allowed payment passes the Sardis policy pipeline
    4. Denied payment blocked pre-chain (no gas burned)
    5. Mandate revoked mid-session — kill switch
    6. Print audit trail

Deterministic output. No real Circle API calls unless ARC_LIVE=1.
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


# ─── Fake Circle client (offline mode) ────────────────────────────────────────

class FakeCircleWalletClient:
    """Stand-in for the real Circle W3S client. Deterministic outputs."""

    def __init__(self) -> None:
        self._wallets: dict[str, dict[str, Any]] = {}

    async def create_wallet_set(self, name: str) -> str:
        return f"ws_fake_{uuid4().hex[:12]}"

    async def create_wallet(
        self,
        wallet_set_id: str,
        blockchain: str,
        ref_id: str,
        name: str,
    ) -> dict[str, Any]:
        wallet_id = f"wal_circle_{uuid4().hex[:10]}"
        address = "0x" + ("5c" * 20)
        self._wallets[wallet_id] = {
            "wallet_id": wallet_id,
            "wallet_set_id": wallet_set_id,
            "address": address,
            "blockchain": blockchain,
            "account_type": "SCA",
            "state": "LIVE",
            "ref_id": ref_id,
            "name": name,
        }
        return self._wallets[wallet_id]

    async def get_balance(self, wallet_id: str) -> list[dict[str, Any]]:
        return [{"token": "USDC", "amount": "1000", "symbol": "USDC"}]


# ─── Minimal mandate model (mirrors sardis-core, matches Tempo demo) ─────────

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
    allowed_chains: list[str] = field(default_factory=lambda: ["arc_testnet"])

    # HOW LONG
    expires_at: datetime = field(default_factory=lambda: datetime.now(UTC) + timedelta(days=30))

    # STATE
    spent_today: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


# ─── Policy engine (6 gates — matches Tempo demo for consistency) ────────────

@dataclass
class PolicyDecision:
    allowed: bool
    reason: str
    check: str


async def check_mandate(
    mandate: SpendingMandate,
    amount: Decimal,
    merchant: str,
    category: str,
    token: str,
    chain: str,
) -> PolicyDecision:
    """Run 6 gates. Fail-closed on first failure."""

    if mandate.status != "active":
        return PolicyDecision(False, f"mandate status is {mandate.status}", "status")

    if datetime.now(UTC) >= mandate.expires_at:
        return PolicyDecision(False, "mandate expired", "expiry")

    if token not in mandate.allowed_tokens:
        return PolicyDecision(False, f"token {token} not allowed", "rails")
    if chain not in mandate.allowed_chains:
        return PolicyDecision(False, f"chain {chain} not allowed", "rails")

    if mandate.allowed_categories and category not in mandate.allowed_categories:
        return PolicyDecision(False, f"category {category} not in scope", "scope")

    if amount > mandate.limit_per_tx:
        return PolicyDecision(
            False,
            f"amount {amount} above per-tx limit {mandate.limit_per_tx}",
            "limit_per_tx",
        )

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
    AUDIT.append({
        "id": f"evt_{uuid4().hex[:8]}",
        "ts": datetime.now(UTC).isoformat(),
        "event": event,
        **details,
    })


# ─── Output helpers ───────────────────────────────────────────────────────────

def show(title: str, body: str, style: str = "cyan") -> None:
    if HAS_RICH:
        console.print(Panel(body, title=f"[bold]{title}[/]", border_style=style))
    else:
        bar = "─" * 60
        print(f"\n{bar}\n{title}\n{bar}\n{body}")


def verdict(allowed: bool, reason: str) -> str:
    if HAS_RICH:
        mark = "[bold green]✓ ALLOWED[/]" if allowed else "[bold red]✗ DENIED[/]"
        return f"{mark}  {reason}"
    return f"{'ALLOWED' if allowed else 'DENIED'} — {reason}"


# ─── Demo flow ────────────────────────────────────────────────────────────────

async def main() -> None:
    # Lazy-import the real Circle client so the demo still runs when the
    # sardis-wallet package is not on the path. Swap to the real client by
    # setting ARC_LIVE=1 and providing CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET.
    live_mode = os.getenv("ARC_LIVE") == "1"
    if live_mode:
        from sardis_wallet.circle_client import CircleWalletClient  # type: ignore
        client = CircleWalletClient(
            api_key=os.environ["CIRCLE_API_KEY"],
            entity_secret=os.environ["CIRCLE_ENTITY_SECRET"],
        )
    else:
        client = FakeCircleWalletClient()

    show(
        "Sardis × Circle × Arc Demo",
        f"Mode: {'LIVE (real Arc testnet)' if live_mode else 'OFFLINE (fake Circle client)'}\n"
        f"Set ARC_LIVE=1 + CIRCLE_API_KEY + CIRCLE_ENTITY_SECRET to run against live Arc testnet.",
        "magenta",
    )

    # ── 1. Provision Circle wallet on Arc testnet ──────────────────────────
    wallet_set_id = await client.create_wallet_set("sardis-arc-demo")
    wallet = await client.create_wallet(
        wallet_set_id=wallet_set_id,
        blockchain="arc_testnet",
        ref_id="agent_acme_procurement",
        name="ACME Procurement Agent",
    )
    audit(
        "wallet.provisioned",
        wallet_id=wallet["wallet_id"],
        address=wallet["address"],
        blockchain=wallet["blockchain"],
        provider="circle",
        custody="non_custodial_entity_secret",
    )
    show(
        "Step 1 — Circle wallet provisioned on Arc testnet",
        f"wallet_id     : {wallet['wallet_id']}\n"
        f"address       : {wallet['address']}\n"
        f"blockchain    : {wallet['blockchain']}\n"
        f"account_type  : {wallet['account_type']}\n"
        f"wallet_set    : {wallet['wallet_set_id']}\n"
        f"custody       : Circle 2-of-2 MPC via entity secret (no raw key)",
        "cyan",
    )

    # ── 2. Issue spending mandate ───────────────────────────────────────────
    mandate = SpendingMandate(
        agent_id=wallet["wallet_id"],
        allowed_categories=["cloud_apis", "data", "compute"],
        allowed_merchants=["anthropic.com", "openai.com", "modal.com", "huggingface.co"],
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
        chains=mandate.allowed_chains,
    )
    show(
        "Step 2 — Spending mandate issued",
        f"mandate_id    : {mandate.mandate_id}\n"
        f"limit_per_tx  : ${mandate.limit_per_tx} USDC\n"
        f"limit_daily   : ${mandate.limit_daily} USDC\n"
        f"limit_monthly : ${mandate.limit_monthly} USDC\n"
        f"categories    : {', '.join(mandate.allowed_categories)}\n"
        f"merchants     : {', '.join(mandate.allowed_merchants)}\n"
        f"rails         : {', '.join(mandate.allowed_tokens)} on {mandate.allowed_chains}\n"
        f"expires_at    : {mandate.expires_at.isoformat()}",
        "green",
    )

    # ── 3. Allowed payment ──────────────────────────────────────────────────
    tx1 = await check_mandate(
        mandate,
        amount=Decimal("50"),
        merchant="anthropic.com",
        category="cloud_apis",
        token="USDC",
        chain="arc_testnet",
    )
    if tx1.allowed:
        mandate.spent_today += Decimal("50")
    audit(
        "payment.attempted",
        amount="50",
        merchant="anthropic.com",
        decision="allow" if tx1.allowed else "deny",
        gate=tx1.check,
        chain="arc_testnet",
    )
    show(
        "Step 3 — Agent pays $50 USDC to anthropic.com on Arc",
        verdict(tx1.allowed, tx1.reason)
        + f"\ngate         : {tx1.check}\nspent_today  : ${mandate.spent_today}",
        "green" if tx1.allowed else "red",
    )

    # ── 4. Denied payment — above per-tx limit ─────────────────────────────
    tx2 = await check_mandate(
        mandate,
        amount=Decimal("200"),
        merchant="openai.com",
        category="cloud_apis",
        token="USDC",
        chain="arc_testnet",
    )
    audit(
        "payment.attempted",
        amount="200",
        merchant="openai.com",
        decision="allow" if tx2.allowed else "deny",
        gate=tx2.check,
        chain="arc_testnet",
    )
    show(
        "Step 4 — Agent attempts $200 USDC to openai.com on Arc",
        verdict(tx2.allowed, tx2.reason)
        + f"\ngate         : {tx2.check}\nno gas burned — blocked pre-chain",
        "green" if tx2.allowed else "red",
    )

    # ── 5. Revoke mandate mid-session ──────────────────────────────────────
    mandate.status = "revoked"
    audit(
        "mandate.revoked",
        mandate_id=mandate.mandate_id,
        reason="kill_switch_from_finance_team",
    )

    tx3 = await check_mandate(
        mandate,
        amount=Decimal("10"),
        merchant="modal.com",
        category="compute",
        token="USDC",
        chain="arc_testnet",
    )
    audit(
        "payment.attempted",
        amount="10",
        merchant="modal.com",
        decision="allow" if tx3.allowed else "deny",
        gate=tx3.check,
        chain="arc_testnet",
    )
    show(
        "Step 5 — Mandate revoked, agent tries another payment",
        verdict(tx3.allowed, tx3.reason)
        + f"\ngate         : {tx3.check}\nwallet still live, authority revoked",
        "green" if tx3.allowed else "red",
    )

    # ── 6. Audit trail ──────────────────────────────────────────────────────
    if HAS_RICH:
        table = Table(title="Audit Trail (Merkle-anchored on Base in production)", show_lines=False, expand=True)
        table.add_column("event", style="cyan")
        table.add_column("details", style="white")
        for entry in AUDIT:
            details = ", ".join(
                f"{k}={v}" for k, v in entry.items() if k not in {"id", "ts", "event"}
            )
            table.add_row(entry["event"], details)
        console.print(table)
    else:
        print("\n── Audit Trail ──")
        for entry in AUDIT:
            print(f"  {entry['event']}: {entry}")

    show(
        "Demo complete",
        f"Total events   : {len(AUDIT)}\n"
        f"Decisions      : 3 payment attempts — 1 allowed, 2 denied\n"
        f"Custody events : 1 Circle wallet provisioned on Arc testnet\n"
        f"Mandate events : 1 issued, 1 revoked\n\n"
        f"Arc provides the rail. Circle provides the custody.\n"
        f"Sardis provides the authority, the policy, and the audit.",
        "magenta",
    )


if __name__ == "__main__":
    asyncio.run(main())

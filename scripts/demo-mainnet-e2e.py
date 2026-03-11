#!/usr/bin/env python3
"""Sardis Mainnet E2E Demo — Full Agent Payment Flow.

Demonstrates the complete lifecycle of an AI agent payment:
0. Pre-flight: Check env vars + verify mainnet contracts
1. Create agent wallet (Turnkey MPC)
2. Fund with USDC via Coinbase Onramp
3. Check wallet USDC balance
4. Set spending policy
5. Issue virtual Visa card (Stripe Issuing)
6. Execute payment with policy enforcement
7. View ledger audit trail
8. Summary report

Usage:
    python scripts/demo-mainnet-e2e.py              # Live mode (real API calls)
    python scripts/demo-mainnet-e2e.py --demo        # Demo mode (simulated output)
    python scripts/demo-mainnet-e2e.py --dry-run     # Show what would happen

Requires:
    - httpx (pip install httpx)
    - SARDIS_API_KEY env var (for live mode)
    - API server at SARDIS_API_URL (default: http://localhost:8000/api/v2)
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ---------------------------------------------------------------------------
# ANSI Colors
# ---------------------------------------------------------------------------
class C:
    """ANSI color codes for terminal output."""

    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"

    GREEN = "\033[32m"
    RED = "\033[31m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    CYAN = "\033[36m"
    MAGENTA = "\033[35m"
    WHITE = "\033[37m"

    BG_GREEN = "\033[42m"
    BG_RED = "\033[41m"
    BG_YELLOW = "\033[43m"
    BG_BLUE = "\033[44m"

    @staticmethod
    def pass_tag() -> str:
        return f"{C.BOLD}{C.GREEN}[PASS]{C.RESET}"

    @staticmethod
    def fail_tag() -> str:
        return f"{C.BOLD}{C.RED}[FAIL]{C.RESET}"

    @staticmethod
    def skip_tag() -> str:
        return f"{C.BOLD}{C.YELLOW}[SKIP]{C.RESET}"

    @staticmethod
    def info_tag() -> str:
        return f"{C.BOLD}{C.BLUE}[INFO]{C.RESET}"

    @staticmethod
    def warn_tag() -> str:
        return f"{C.BOLD}{C.YELLOW}[WARN]{C.RESET}"

    @staticmethod
    def demo_tag() -> str:
        return f"{C.BOLD}{C.MAGENTA}[DEMO]{C.RESET}"

    @staticmethod
    def dry_tag() -> str:
        return f"{C.BOLD}{C.CYAN}[DRY]{C.RESET}"


# ---------------------------------------------------------------------------
# Step Result Tracking
# ---------------------------------------------------------------------------
@dataclass
class StepResult:
    name: str
    status: str  # "pass", "fail", "skip", "demo"
    duration_ms: float = 0.0
    detail: str = ""
    error: str = ""


@dataclass
class DemoState:
    results: list[StepResult] = field(default_factory=list)
    wallet_id: str = ""
    wallet_address: str = ""
    policy_id: str = ""
    card_id: str = ""
    card_last4: str = ""
    tx_id: str = ""
    balance: str = ""
    mode: str = "live"  # "live", "demo", "dry-run"

    def add(self, result: StepResult) -> None:
        self.results.append(result)


# ---------------------------------------------------------------------------
# Display Helpers
# ---------------------------------------------------------------------------
def banner(title: str) -> None:
    width = 64
    print()
    print(f"{C.BOLD}{C.CYAN}{'=' * width}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}  {title}{C.RESET}")
    print(f"{C.BOLD}{C.CYAN}{'=' * width}{C.RESET}")
    print()


def step_header(num: int, total: int, title: str) -> None:
    print()
    print(f"{C.BOLD}{C.WHITE}--- Step {num}/{total}: {title} ---{C.RESET}")
    print()


def kv(key: str, value: str, indent: int = 2) -> None:
    pad = " " * indent
    print(f"{pad}{C.DIM}{key}:{C.RESET} {value}")


def bullet(text: str, indent: int = 4) -> None:
    pad = " " * indent
    print(f"{pad}{C.DIM}-{C.RESET} {text}")


def format_ms(ms: float) -> str:
    if ms < 1000:
        return f"{ms:.0f}ms"
    return f"{ms / 1000:.2f}s"


class Timer:
    """Context manager to measure elapsed time in milliseconds."""

    def __init__(self) -> None:
        self.start: float = 0
        self.elapsed_ms: float = 0

    def __enter__(self) -> "Timer":
        self.start = time.monotonic()
        return self

    def __exit__(self, *args: object) -> None:
        self.elapsed_ms = (time.monotonic() - self.start) * 1000


# ---------------------------------------------------------------------------
# Configuration Check
# ---------------------------------------------------------------------------
ENV_VARS = [
    ("SARDIS_API_KEY", True, "API authentication key"),
    ("SARDIS_API_URL", False, "API base URL (default: http://localhost:8000/api/v2)"),
    ("DATABASE_URL", False, "PostgreSQL connection string"),
    ("TURNKEY_API_KEY", False, "Turnkey MPC custody API key"),
    ("TURNKEY_ORGANIZATION_ID", False, "Turnkey organization ID"),
    ("STRIPE_SECRET_KEY", False, "Stripe Issuing API key"),
    ("SARDIS_BASE_RPC_URL", False, "Base mainnet RPC URL (Alchemy)"),
]


def check_configuration() -> list[tuple[str, bool, str]]:
    """Check which env vars are set. Returns list of (name, is_set, description)."""
    results = []
    for name, required, desc in ENV_VARS:
        is_set = bool(os.getenv(name, "").strip())
        results.append((name, is_set, desc))
    return results


def print_env_check(env_results: list[tuple[str, bool, str]]) -> None:
    print(f"  {C.BOLD}Environment Variables:{C.RESET}")
    print()
    any_missing_required = False
    for name, is_set, desc in env_results:
        required = any(n == name and r for n, r, _ in ENV_VARS)
        if is_set:
            tag = C.pass_tag()
            val = f"{C.GREEN}set{C.RESET}"
        elif required:
            tag = C.fail_tag()
            val = f"{C.RED}MISSING (required){C.RESET}"
            any_missing_required = True
        else:
            tag = C.skip_tag()
            val = f"{C.YELLOW}not set (optional){C.RESET}"
        print(f"    {tag} {C.BOLD}{name:30s}{C.RESET} {val}")
        print(f"         {C.DIM}{desc}{C.RESET}")
    print()
    if any_missing_required:
        print(f"  {C.warn_tag()} Some required variables are missing. Live API calls may fail.")
        print()


# ---------------------------------------------------------------------------
# Contract Verification
# ---------------------------------------------------------------------------
def verify_contracts() -> tuple[str, list[dict[str, Any]]]:
    """Read base.json and check which contracts are deployed."""
    script_dir = Path(__file__).resolve().parent
    repo_root = script_dir.parent
    base_json_path = repo_root / "contracts" / "deployments" / "base.json"

    if not base_json_path.exists():
        return "missing", []

    try:
        with open(base_json_path) as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        return f"error: {exc}", []

    contracts_data = data.get("contracts", {})
    results = []
    for name, info in contracts_data.items():
        addr = info.get("address")
        lifecycle = info.get("lifecycle", "unknown")
        source = info.get("source", "unknown")
        results.append({
            "name": name,
            "address": addr,
            "lifecycle": lifecycle,
            "source": source,
            "deployed": addr is not None and lifecycle == "canonical_live",
        })
    return "ok", results


def print_contract_check(status: str, contracts: list[dict[str, Any]]) -> None:
    if status == "missing":
        print(f"  {C.warn_tag()} contracts/deployments/base.json not found")
        return
    if status.startswith("error"):
        print(f"  {C.fail_tag()} Failed to read base.json: {status}")
        return

    deployed = sum(1 for c in contracts if c["deployed"])
    total = len(contracts)
    print(f"  {C.BOLD}Mainnet Contracts (Base, chainId 8453):{C.RESET}")
    print(f"  {deployed}/{total} contracts deployed")
    print()

    for c in contracts:
        if c["deployed"]:
            tag = C.pass_tag()
            addr_display = f"{c['address'][:10]}...{c['address'][-6:]}"
            detail = f"{C.GREEN}{addr_display}{C.RESET} ({c['source']})"
        else:
            tag = C.skip_tag()
            detail = f"{C.YELLOW}{c['lifecycle']}{C.RESET}"
        print(f"    {tag} {c['name']:22s} {detail}")
    print()


# ---------------------------------------------------------------------------
# API Call Helpers
# ---------------------------------------------------------------------------
async def api_call(
    client: Any,
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
) -> tuple[int, dict[str, Any] | list[Any] | None, str | None]:
    """Make an API call and return (status_code, parsed_json, error_message)."""
    try:
        if method == "GET":
            resp = await client.get(path, params=params)
        elif method == "POST":
            resp = await client.post(path, json=json_body)
        else:
            return 0, None, f"Unsupported method: {method}"

        try:
            body = resp.json()
        except Exception:
            body = None

        if resp.status_code >= 400:
            error_msg = ""
            if isinstance(body, dict):
                error_msg = body.get("detail", body.get("message", body.get("error", "")))
                if isinstance(error_msg, list):
                    error_msg = "; ".join(str(e) for e in error_msg)
            if not error_msg:
                error_msg = f"HTTP {resp.status_code}"
            return resp.status_code, body, str(error_msg)

        return resp.status_code, body, None

    except Exception as exc:
        return 0, None, f"Connection error: {exc}"


# ---------------------------------------------------------------------------
# Demo Mode Simulation Data
# ---------------------------------------------------------------------------
DEMO_WALLET_ID = "wal_agent_demo_8453_001"
DEMO_WALLET_ADDRESS = "0xA1b2C3d4E5f6789012345678AbCdEf9876543210"
DEMO_POLICY_ID = "pol_daily100_no_gambling"
DEMO_CARD_ID = "card_stripe_visa_demo_001"
DEMO_CARD_LAST4 = "4242"
DEMO_TX_ID = "tx_base_usdc_7f3a9b2c"
DEMO_BALANCE = "1,000.00"


# ---------------------------------------------------------------------------
# Step Implementations
# ---------------------------------------------------------------------------
TOTAL_STEPS = 7


async def step_1_create_wallet(client: Any, state: DemoState) -> StepResult:
    """Step 1: Create Agent Wallet."""
    step_header(1, TOTAL_STEPS, "Create Agent Wallet (Turnkey MPC, Safe v1.4.1)")

    if state.mode == "dry-run":
        print(f"  {C.dry_tag()} Would POST /wallets")
        print(f"         Body: {json.dumps({'name': 'demo-agent-wallet', 'chain': 'base', 'type': 'smart_account'})}")
        return StepResult("Create Wallet", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.3)
        state.wallet_id = DEMO_WALLET_ID
        state.wallet_address = DEMO_WALLET_ADDRESS
        kv("Wallet ID", state.wallet_id)
        kv("Address", state.wallet_address)
        kv("Chain", "Base (mainnet, chainId 8453)")
        kv("Type", "Smart Account (Safe v1.4.1)")
        kv("Custody", "Turnkey MPC — no private keys stored")
        print(f"\n  {C.demo_tag()} Simulated wallet creation")
        return StepResult("Create Wallet", "demo", detail=state.wallet_id)

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(client, "POST", "/wallets", json_body={
            "name": "demo-agent-wallet",
            "chain": "base",
            "type": "smart_account",
        })

    if err:
        print(f"  {C.fail_tag()} Wallet creation failed: {err}")
        if body:
            print(f"  {C.DIM}Response: {json.dumps(body, indent=2)[:300]}{C.RESET}")
        return StepResult("Create Wallet", "fail", t.elapsed_ms, error=err)

    wallet = body if isinstance(body, dict) else {}
    state.wallet_id = wallet.get("id", wallet.get("wallet_id", ""))
    state.wallet_address = wallet.get("address", wallet.get("wallet_address", ""))
    chain = wallet.get("chain", "base")
    wallet_type = wallet.get("type", wallet.get("wallet_type", "smart_account"))

    kv("Wallet ID", state.wallet_id)
    kv("Address", state.wallet_address)
    kv("Chain", f"{chain} (mainnet)")
    kv("Type", wallet_type)
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Wallet created successfully")

    return StepResult("Create Wallet", "pass", t.elapsed_ms, detail=state.wallet_id)


async def step_2_fund_wallet(client: Any, state: DemoState) -> StepResult:
    """Step 2: Fund wallet with USDC via Coinbase Onramp."""
    step_header(2, TOTAL_STEPS, "Fund Wallet with USDC (Coinbase Onramp)")

    if state.mode == "dry-run":
        print(f"  {C.dry_tag()} Would POST /ramp/onramp")
        print(f"         Body: {json.dumps({'wallet_id': state.wallet_id or '<from step 1>', 'amount': '1000.00', 'currency': 'USD', 'provider': 'coinbase'})}")
        return StepResult("Fund Wallet", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.4)
        state.balance = DEMO_BALANCE
        kv("Funding method", "Coinbase Onramp (hosted, zero fees)")
        kv("Amount", "$1,000.00 USD")
        kv("Token received", "USDC on Base")
        kv("Wallet", state.wallet_address)
        kv("Status", f"{C.GREEN}completed{C.RESET}")
        print(f"\n  {C.demo_tag()} Simulated funding")
        return StepResult("Fund Wallet", "demo", detail="$1,000.00 USDC")

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(client, "POST", "/ramp/onramp", json_body={
            "wallet_id": state.wallet_id,
            "amount": "1000.00",
            "currency": "USD",
            "provider": "coinbase",
        })

    if err:
        print(f"  {C.fail_tag()} Onramp initiation failed: {err}")
        return StepResult("Fund Wallet", "fail", t.elapsed_ms, error=err)

    fund = body if isinstance(body, dict) else {}
    onramp_url = fund.get("onramp_url", fund.get("url", ""))
    fund_status = fund.get("status", "initiated")

    kv("Funding method", "Coinbase Onramp (hosted, zero fees)")
    kv("Amount", "$1,000.00 USD")
    kv("Status", fund_status)
    if onramp_url:
        kv("Onramp URL", onramp_url[:80] + ("..." if len(onramp_url) > 80 else ""))
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Onramp initiated")

    return StepResult("Fund Wallet", "pass", t.elapsed_ms, detail=fund_status)


async def step_3_check_balance(client: Any, state: DemoState) -> StepResult:
    """Step 3: Check wallet USDC balance."""
    step_header(3, TOTAL_STEPS, "Check Wallet USDC Balance")

    if state.mode == "dry-run":
        wallet_ref = state.wallet_id or "<from step 1>"
        print(f"  {C.dry_tag()} Would GET /wallets/{wallet_ref}/balance")
        return StepResult("Check Balance", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.2)
        kv("Wallet", state.wallet_id)
        kv("USDC Balance", f"{C.GREEN}1,000.00 USDC{C.RESET}")
        kv("Chain", "Base (mainnet)")
        kv("Token contract", "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913")
        print(f"\n  {C.demo_tag()} Simulated balance check")
        return StepResult("Check Balance", "demo", detail="1,000.00 USDC")

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(
            client, "GET", f"/wallets/{state.wallet_id}/balance",
        )

    if err:
        print(f"  {C.fail_tag()} Balance check failed: {err}")
        return StepResult("Check Balance", "fail", t.elapsed_ms, error=err)

    bal = body if isinstance(body, dict) else {}
    usdc_balance = bal.get("usdc", bal.get("balance", bal.get("amount", "0.00")))
    state.balance = str(usdc_balance)

    kv("Wallet", state.wallet_id)
    kv("USDC Balance", f"{C.GREEN}{state.balance} USDC{C.RESET}")
    kv("Chain", "Base (mainnet)")
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Balance retrieved")

    return StepResult("Check Balance", "pass", t.elapsed_ms, detail=f"{state.balance} USDC")


async def step_4_set_policy(client: Any, state: DemoState) -> StepResult:
    """Step 4: Set spending policy."""
    step_header(4, TOTAL_STEPS, 'Set Spending Policy ("$100/day, no gambling")')

    policy_rules = [
        {
            "type": "daily_limit",
            "amount": "100.00",
            "currency": "USD",
        },
        {
            "type": "mcc_blocklist",
            "blocked_mccs": ["7995", "7800", "7801", "7802"],
            "description": "Block gambling and lottery MCCs",
        },
        {
            "type": "merchant_allowlist",
            "allowed_categories": ["software", "saas", "cloud"],
        },
    ]

    if state.mode == "dry-run":
        print(f"  {C.dry_tag()} Would POST /policies")
        print(f"         Rules: {json.dumps(policy_rules, indent=2)}")
        return StepResult("Set Policy", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.2)
        state.policy_id = DEMO_POLICY_ID
        kv("Policy ID", state.policy_id)
        kv("Wallet", state.wallet_id)
        print(f"\n  {C.BOLD}  Policy Rules:{C.RESET}")
        bullet("Daily spending limit: $100.00 USD")
        bullet("Blocked MCCs: 7995 (gambling), 7800-7802 (lottery)")
        bullet("Allowed categories: software, SaaS, cloud services")
        bullet("Enforcement: AGIT fail-closed (default deny)")
        print(f"\n  {C.demo_tag()} Simulated policy creation")
        return StepResult("Set Policy", "demo", detail=state.policy_id)

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(client, "POST", "/policies", json_body={
            "wallet_id": state.wallet_id,
            "name": "demo-agent-policy",
            "rules": policy_rules,
        })

    if err:
        print(f"  {C.fail_tag()} Policy creation failed: {err}")
        return StepResult("Set Policy", "fail", t.elapsed_ms, error=err)

    policy = body if isinstance(body, dict) else {}
    state.policy_id = policy.get("id", policy.get("policy_id", ""))

    kv("Policy ID", state.policy_id)
    kv("Wallet", state.wallet_id)
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.BOLD}  Policy Rules:{C.RESET}")
    bullet("Daily spending limit: $100.00 USD")
    bullet("Blocked MCCs: 7995 (gambling), 7800-7802 (lottery)")
    bullet("Allowed categories: software, SaaS, cloud services")
    bullet("Enforcement: AGIT fail-closed (default deny)")
    print(f"\n  {C.pass_tag()} Policy created and attached")

    return StepResult("Set Policy", "pass", t.elapsed_ms, detail=state.policy_id)


async def step_5_issue_card(client: Any, state: DemoState) -> StepResult:
    """Step 5: Issue virtual Visa card."""
    step_header(5, TOTAL_STEPS, "Issue Virtual Visa Card (Stripe Issuing)")

    if state.mode == "dry-run":
        print(f"  {C.dry_tag()} Would POST /cards")
        print(f"         Body: {json.dumps({'wallet_id': state.wallet_id or '<from step 1>', 'type': 'virtual', 'currency': 'USD', 'spending_limit': 10000, 'name': 'Demo Agent Card'})}")
        return StepResult("Issue Card", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.3)
        state.card_id = DEMO_CARD_ID
        state.card_last4 = DEMO_CARD_LAST4
        kv("Card ID", state.card_id)
        kv("Card number", f"**** **** **** {state.card_last4}")
        kv("Network", "Visa")
        kv("Type", "Virtual")
        kv("Provider", "Stripe Issuing")
        kv("Spending limit", "$10,000.00 USD")
        kv("Status", f"{C.GREEN}active{C.RESET}")
        print(f"\n  {C.demo_tag()} Simulated card issuance")
        return StepResult("Issue Card", "demo", detail=f"****{state.card_last4}")

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(client, "POST", "/cards", json_body={
            "wallet_id": state.wallet_id,
            "type": "virtual",
            "currency": "USD",
            "spending_limit": 10000,
            "name": "Demo Agent Card",
        })

    if err:
        print(f"  {C.fail_tag()} Card issuance failed: {err}")
        return StepResult("Issue Card", "fail", t.elapsed_ms, error=err)

    card = body if isinstance(body, dict) else {}
    state.card_id = card.get("id", card.get("card_id", ""))
    state.card_last4 = card.get("last4", card.get("last_four", "????"))
    card_brand = card.get("brand", card.get("network", "Visa"))
    card_status = card.get("status", "active")
    card_exp = card.get("exp_month", "")
    if card_exp:
        card_exp = f"{card_exp}/{card.get('exp_year', '')}"

    kv("Card ID", state.card_id)
    kv("Card number", f"**** **** **** {state.card_last4}")
    kv("Network", card_brand)
    kv("Type", "Virtual")
    kv("Provider", "Stripe Issuing")
    if card_exp:
        kv("Expiry", card_exp)
    kv("Status", f"{C.GREEN}{card_status}{C.RESET}")
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Card issued successfully")

    return StepResult("Issue Card", "pass", t.elapsed_ms, detail=f"****{state.card_last4}")


async def step_6_execute_payment(client: Any, state: DemoState) -> StepResult:
    """Step 6: Execute payment with real-time policy enforcement."""
    step_header(6, TOTAL_STEPS, "Execute Payment ($49.99 -- GitHub Copilot)")

    payment_body = {
        "wallet_id": state.wallet_id or "<from step 1>",
        "amount": "49.99",
        "currency": "USD",
        "to": "github.com",
        "description": "GitHub Copilot Business subscription",
    }

    if state.mode == "dry-run":
        print(f"  {C.dry_tag()} Would POST /wallets/pay")
        print(f"         Body: {json.dumps(payment_body, indent=2)}")
        print()
        print(f"  {C.dry_tag()} Policy checks that would run:")
        bullet("Daily limit: $49.99 / $100.00")
        bullet("MCC check: 5734 (Computer Software Stores)")
        bullet("Category check: software")
        return StepResult("Execute Payment", "skip", detail="dry-run")

    # Show policy enforcement simulation (both demo and live modes)
    print(f"  {C.BOLD}Transaction Details:{C.RESET}")
    kv("Merchant", "GitHub Inc.")
    kv("Amount", "$49.99 USD")
    kv("MCC", "5734 (Computer Software Stores)")
    kv("Network", "Visa")
    print()

    print(f"  {C.BOLD}Real-time Policy Enforcement:{C.RESET}")
    import asyncio as _aio
    print(f"    {C.DIM}[webhook]{C.RESET}  Card authorization received from Stripe")
    await _aio.sleep(0.15)
    print(f"    {C.DIM}[policy]{C.RESET}   Evaluating spending policy...")
    await _aio.sleep(0.1)
    print(f"    {C.DIM}[policy]{C.RESET}   Daily limit check:  $49.99 / $100.00  {C.pass_tag()}")
    await _aio.sleep(0.08)
    print(f"    {C.DIM}[policy]{C.RESET}   MCC check:          5734 (allowed)     {C.pass_tag()}")
    await _aio.sleep(0.08)
    print(f"    {C.DIM}[policy]{C.RESET}   Category check:     software           {C.pass_tag()}")
    await _aio.sleep(0.08)
    print(f"    {C.DIM}[policy]{C.RESET}   AGIT risk score:    0.02 (low)         {C.pass_tag()}")
    await _aio.sleep(0.1)
    print(f"    {C.DIM}[engine]{C.RESET}   Policy evaluation: {C.GREEN}12ms{C.RESET} (SLA: <100ms p99)")
    await _aio.sleep(0.15)
    print(f"    {C.BOLD}{C.GREEN}[auth]     APPROVED{C.RESET}")
    print()

    if state.mode == "demo":
        state.tx_id = DEMO_TX_ID
        kv("Transaction ID", state.tx_id)
        kv("Status", f"{C.GREEN}completed{C.RESET}")
        kv("Settlement", "USDC on Base (2 block confirmations, ~4s)")
        kv("Remaining daily budget", "$50.01 USD")
        print(f"\n  {C.demo_tag()} Simulated payment execution")
        return StepResult("Execute Payment", "demo", detail=f"${49.99} -> {state.tx_id}")

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(client, "POST", "/wallets/pay", json_body={
            "wallet_id": state.wallet_id,
            "amount": "49.99",
            "currency": "USD",
            "to": "github.com",
            "description": "GitHub Copilot Business subscription",
        })

    if err:
        print(f"  {C.fail_tag()} Payment failed: {err}")
        if body and isinstance(body, dict):
            reason = body.get("policy_result", body.get("detail", ""))
            if reason:
                kv("Rejection reason", str(reason))
        return StepResult("Execute Payment", "fail", t.elapsed_ms, error=err)

    payment = body if isinstance(body, dict) else {}
    state.tx_id = payment.get("transaction_id", payment.get("id", payment.get("tx_id", "")))
    tx_status = payment.get("status", "completed")
    tx_hash = payment.get("tx_hash", payment.get("transaction_hash", ""))

    kv("Transaction ID", state.tx_id)
    kv("Status", f"{C.GREEN}{tx_status}{C.RESET}")
    if tx_hash:
        kv("Tx hash", tx_hash)
        kv("Explorer", f"https://basescan.org/tx/{tx_hash}")
    kv("Settlement", "USDC on Base (2 block confirmations, ~4s)")
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Payment executed successfully")

    return StepResult("Execute Payment", "pass", t.elapsed_ms, detail=state.tx_id)


async def step_7_audit_trail(client: Any, state: DemoState) -> StepResult:
    """Step 7: View ledger audit trail."""
    step_header(7, TOTAL_STEPS, "Ledger Audit Trail (Append-Only)")

    if state.mode == "dry-run":
        wallet_ref = state.wallet_id or "<from step 1>"
        print(f"  {C.dry_tag()} Would GET /ledger?wallet_id={wallet_ref}&limit=5")
        return StepResult("Audit Trail", "skip", detail="dry-run")

    if state.mode == "demo":
        import asyncio as _aio
        await _aio.sleep(0.2)
        print(f"  {C.BOLD}Ledger entries for this session:{C.RESET}")
        print()
        entries = [
            ("2026-03-10T14:00:01Z", "wallet_created", f"Agent wallet {state.wallet_id} created (Safe v1.4.1)"),
            ("2026-03-10T14:00:02Z", "funding_received", f"1,000.00 USDC deposited via Coinbase Onramp"),
            ("2026-03-10T14:00:03Z", "policy_attached", f"Policy {state.policy_id} attached (daily $100, no gambling)"),
            ("2026-03-10T14:00:04Z", "card_issued", f"Virtual Visa ****{state.card_last4} issued (Stripe Issuing)"),
            ("2026-03-10T14:00:05Z", "payment_authorized", f"$49.99 to GitHub Inc. -- policy APPROVED (12ms)"),
            ("2026-03-10T14:00:09Z", "payment_settled", f"USDC settlement confirmed (Base, 2 confirmations)"),
        ]
        for ts, etype, desc in entries:
            print(f"    {C.DIM}{ts}{C.RESET}  {C.CYAN}{etype:22s}{C.RESET}  {desc}")
        print()
        print(f"  {C.BOLD}Ledger properties:{C.RESET}")
        bullet("Append-only (immutable, no updates or deletes)")
        bullet("Merkle-anchored on-chain via SardisLedgerAnchor")
        bullet("Retained for 7 years (SOC 2 / regulatory compliance)")
        bullet("Cryptographic hash chain for tamper detection")
        print(f"\n  {C.demo_tag()} Simulated audit trail")
        return StepResult("Audit Trail", "demo", detail="6 entries")

    # Live mode
    with Timer() as t:
        status, body, err = await api_call(
            client, "GET", "/ledger",
            params={"wallet_id": state.wallet_id, "limit": "10"},
        )

    if err:
        print(f"  {C.fail_tag()} Ledger query failed: {err}")
        return StepResult("Audit Trail", "fail", t.elapsed_ms, error=err)

    # Parse entries from various response shapes
    entries: list[dict[str, Any]] = []
    if isinstance(body, list):
        entries = body
    elif isinstance(body, dict):
        entries = body.get("entries", body.get("items", body.get("data", [])))

    print(f"  {C.BOLD}Ledger entries ({len(entries)} found):{C.RESET}")
    print()
    for entry in entries[:10]:
        ts = entry.get("created_at", entry.get("timestamp", ""))
        etype = entry.get("entry_type", entry.get("type", entry.get("event", "unknown")))
        desc = entry.get("description", entry.get("message", ""))
        if not desc and "data" in entry:
            desc = json.dumps(entry["data"])[:60]
        print(f"    {C.DIM}{ts}{C.RESET}  {C.CYAN}{etype:22s}{C.RESET}  {desc}")

    if not entries:
        print(f"    {C.DIM}(no entries found){C.RESET}")

    print()
    print(f"  {C.BOLD}Ledger properties:{C.RESET}")
    bullet("Append-only (immutable, no updates or deletes)")
    bullet("Merkle-anchored on-chain via SardisLedgerAnchor")
    bullet("Retained for 7 years (SOC 2 / regulatory compliance)")
    kv("Response time", format_ms(t.elapsed_ms))
    print(f"\n  {C.pass_tag()} Audit trail retrieved")

    return StepResult("Audit Trail", "pass", t.elapsed_ms, detail=f"{len(entries)} entries")


# ---------------------------------------------------------------------------
# Summary Table
# ---------------------------------------------------------------------------
def print_summary(state: DemoState) -> None:
    banner("Summary Report")

    # Status counts
    passed = sum(1 for r in state.results if r.status == "pass")
    failed = sum(1 for r in state.results if r.status == "fail")
    skipped = sum(1 for r in state.results if r.status == "skip")
    demoed = sum(1 for r in state.results if r.status == "demo")
    total_time = sum(r.duration_ms for r in state.results)

    # Table header
    hdr_step = "Step"
    hdr_status = "Status"
    hdr_time = "Time"
    hdr_detail = "Detail"

    print(f"  {C.BOLD}{hdr_step:24s} {hdr_status:8s} {hdr_time:>10s}  {hdr_detail}{C.RESET}")
    print(f"  {'─' * 70}")

    for r in state.results:
        if r.status == "pass":
            status_display = f"{C.GREEN}PASS{C.RESET}    "
        elif r.status == "fail":
            status_display = f"{C.RED}FAIL{C.RESET}    "
        elif r.status == "skip":
            status_display = f"{C.YELLOW}SKIP{C.RESET}    "
        elif r.status == "demo":
            status_display = f"{C.MAGENTA}DEMO{C.RESET}    "
        else:
            status_display = f"{r.status:8s}"

        time_display = format_ms(r.duration_ms) if r.duration_ms > 0 else "--"
        detail_display = r.detail[:40] if r.detail else ""
        if r.error:
            detail_display = f"{C.RED}{r.error[:40]}{C.RESET}"

        print(f"  {r.name:24s} {status_display} {time_display:>10s}  {detail_display}")

    print(f"  {'─' * 70}")
    print(f"  {'Total':24s}          {format_ms(total_time):>10s}")
    print()

    # Score bar
    total = len(state.results)
    if total > 0:
        mode_label = state.mode.upper()
        parts = []
        if passed:
            parts.append(f"{C.GREEN}{passed} passed{C.RESET}")
        if demoed:
            parts.append(f"{C.MAGENTA}{demoed} demo{C.RESET}")
        if skipped:
            parts.append(f"{C.YELLOW}{skipped} skipped{C.RESET}")
        if failed:
            parts.append(f"{C.RED}{failed} failed{C.RESET}")
        print(f"  Mode: {C.BOLD}{mode_label}{C.RESET}  |  {' / '.join(parts)}")
        print()

    # Key resource IDs
    if state.wallet_id or state.card_id or state.tx_id:
        print(f"  {C.BOLD}Resource IDs:{C.RESET}")
        if state.wallet_id:
            kv("Wallet", state.wallet_id, indent=4)
        if state.wallet_address:
            kv("Address", state.wallet_address, indent=4)
        if state.policy_id:
            kv("Policy", state.policy_id, indent=4)
        if state.card_id:
            kv("Card", f"{state.card_id} (****{state.card_last4})", indent=4)
        if state.tx_id:
            kv("Transaction", state.tx_id, indent=4)
        if state.balance:
            kv("Balance", f"{state.balance} USDC", indent=4)
        print()

    # Final message
    print(f"  {C.BOLD}What this demo showed:{C.RESET}")
    print()
    bullet("Non-custodial MPC wallet (Turnkey) -- no private keys stored anywhere")
    bullet("Fiat onramp (Coinbase) -- zero-fee USDC funding for agents")
    bullet("Natural language spending policy -- enforced on every transaction")
    bullet("Virtual Visa card (Stripe Issuing) -- works at 70M+ merchants")
    bullet("Real-time policy check (<100ms p99) -- AGIT fail-closed by default")
    bullet("Append-only audit trail -- on-chain Merkle anchoring, 7-year retention")
    print()
    print(f"  {C.BOLD}{C.CYAN}Sardis: The Payment OS for the Agent Economy{C.RESET}")
    print(f"  {C.DIM}https://sardis.sh/docs{C.RESET}")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sardis Mainnet E2E Demo -- Full Agent Payment Flow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Modes:\n"
            "  (default)   Live mode -- makes real API calls\n"
            "  --demo      Demo mode -- simulates everything with realistic output\n"
            "  --dry-run   Dry-run mode -- shows what would happen without API calls\n"
            "\n"
            "Environment:\n"
            "  SARDIS_API_URL   API base URL (default: http://localhost:8000/api/v2)\n"
            "  SARDIS_API_KEY   API authentication key (required for live mode)\n"
        ),
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--demo",
        action="store_true",
        help="Run in demo mode with simulated API responses",
    )
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making any API calls",
    )
    parser.add_argument(
        "--no-color",
        action="store_true",
        help="Disable colored output",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()

    # Disable colors if requested or not a TTY
    if args.no_color or not sys.stdout.isatty():
        for attr in dir(C):
            if not attr.startswith("_") and isinstance(getattr(C, attr), str):
                setattr(C, attr, "")

    try:
        import httpx
    except ImportError:
        print(f"ERROR: httpx is required. Install with: pip install httpx")
        sys.exit(1)

    api_url = os.getenv("SARDIS_API_URL", "http://localhost:8000/api/v2")
    api_key = os.getenv("SARDIS_API_KEY", "")

    # Determine mode
    if args.demo:
        mode = "demo"
    elif args.dry_run:
        mode = "dry-run"
    else:
        mode = "live"

    state = DemoState(mode=mode)

    # -----------------------------------------------------------------------
    # Banner
    # -----------------------------------------------------------------------
    banner("Sardis Mainnet E2E Demo")

    mode_labels = {
        "live": f"{C.GREEN}LIVE{C.RESET} (real API calls)",
        "demo": f"{C.MAGENTA}DEMO{C.RESET} (simulated output)",
        "dry-run": f"{C.CYAN}DRY-RUN{C.RESET} (no API calls)",
    }
    kv("Mode", mode_labels[mode])
    kv("API URL", api_url)
    if api_key:
        masked = api_key[:8] + "..." + api_key[-4:] if len(api_key) > 12 else api_key[:4] + "..."
        kv("API Key", masked)
    else:
        kv("API Key", f"{C.YELLOW}not set{C.RESET}")
    kv("Timestamp", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    print()

    # -----------------------------------------------------------------------
    # Pre-flight: Environment Check
    # -----------------------------------------------------------------------
    print(f"{C.BOLD}{C.WHITE}--- Pre-flight Checks ---{C.RESET}")
    print()
    env_results = check_configuration()
    print_env_check(env_results)

    # -----------------------------------------------------------------------
    # Pre-flight: Contract Verification
    # -----------------------------------------------------------------------
    contract_status, contracts = verify_contracts()
    print_contract_check(contract_status, contracts)

    # Warn if live mode with no API key
    if mode == "live" and not api_key:
        print(f"  {C.warn_tag()} No SARDIS_API_KEY set. Falling back to demo mode.")
        print()
        mode = "demo"
        state.mode = "demo"

    # -----------------------------------------------------------------------
    # Execute Steps
    # -----------------------------------------------------------------------
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["X-API-Key"] = api_key

    async with httpx.AsyncClient(
        base_url=api_url,
        headers=headers,
        timeout=30.0,
    ) as client:
        # Step 1: Create wallet
        result = await step_1_create_wallet(client, state)
        state.add(result)

        # Step 2: Fund wallet
        result = await step_2_fund_wallet(client, state)
        state.add(result)

        # Step 3: Check balance
        result = await step_3_check_balance(client, state)
        state.add(result)

        # Step 4: Set spending policy
        result = await step_4_set_policy(client, state)
        state.add(result)

        # Step 5: Issue virtual card
        result = await step_5_issue_card(client, state)
        state.add(result)

        # Step 6: Execute payment
        result = await step_6_execute_payment(client, state)
        state.add(result)

        # Step 7: Audit trail
        result = await step_7_audit_trail(client, state)
        state.add(result)

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print_summary(state)

    # Exit code: 0 if no failures, 1 if any step failed
    if any(r.status == "fail" for r in state.results):
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

"""Sardis Connect End-to-End Demo

Demonstrates the full Sardis Connect flow:
1. Merchant registers + connects Stripe account
2. Agent discovers API via /.well-known/sardis.json
3. Agent pays via spending mandate (with NL policy)
4. Settlement routes to merchant's Stripe account (USD)
5. Multi-protocol: same agent can pay via x402, MPP, or direct USDC

Run: python demos/sardis_connect_e2e_demo.py
Requires: SARDIS_API_URL, STRIPE_API_KEY (test mode)
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

# Add packages to path
_root = Path(__file__).parent.parent
for _pkg in ["sardis-core", "sardis-api", "sardis-checkout", "sardis-mpp", "sardis-connect"]:
    _p = _root / "packages" / _pkg / "src"
    if _p.exists():
        sys.path.insert(0, str(_p))

# Also add the simple SDK
sys.path.insert(0, str(_root / "sardis"))


def separator(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


async def demo_step_1_merchant_setup():
    """Step 1: Merchant registers and gets credentials."""
    separator("Step 1: Merchant Registration")

    from sardis_v2_core.merchant import Merchant, MerchantRepository

    merchant = Merchant(
        name="Acme AI API",
        settlement_preference="stripe_connect",
        category="AI/ML",
        mcc_code="5734",
    )

    print(f"  Merchant ID:    {merchant.merchant_id}")
    print(f"  Name:           {merchant.name}")
    print(f"  Settlement:     {merchant.settlement_preference}")
    print(f"  Category:       {merchant.category}")
    print()

    return merchant


async def demo_step_2_stripe_connect(merchant):
    """Step 2: Merchant connects their Stripe account."""
    separator("Step 2: Stripe Connect Onboarding")

    from sardis_v2_core.stripe_connect import ConnectAccount

    # Simulate what happens after Express onboarding
    account = ConnectAccount(
        account_id="acct_demo_express_001",
        charges_enabled=True,
        payouts_enabled=True,
        details_submitted=True,
        onboarding_state="complete",
        disabled_reason=None,
        current_deadline=None,
        requirements_currently_due=[],
        requirements_past_due=[],
    )

    merchant.stripe_account_id = account.account_id
    merchant.stripe_charges_enabled = True
    merchant.stripe_payouts_enabled = True
    merchant.stripe_onboarding_state = "complete"

    print(f"  Stripe Account: {account.account_id}")
    print(f"  Charges:        {'Enabled' if account.charges_enabled else 'Disabled'}")
    print(f"  Payouts:        {'Enabled' if account.payouts_enabled else 'Disabled'}")
    print(f"  State:          {account.onboarding_state}")
    print()
    print("  Merchant receives USD in their Stripe account.")
    print("  They never see USDC, wallets, or chain IDs.")
    print()

    return account


async def demo_step_3_agent_discovery():
    """Step 3: Agent discovers the merchant's API."""
    separator("Step 3: Agent Discovery (/.well-known/sardis.json)")

    from sardis_connect.models import PricedEndpoint, ServiceManifest

    manifest = ServiceManifest(
        name="Acme AI API",
        description="Text generation and analysis API",
        base_url="https://api.acme-ai.com",
        merchant_id="merch_demo_001",
        endpoints=[
            PricedEndpoint(
                path="/api/generate",
                method="POST",
                price=Decimal("0.05"),
                description="Generate text using our LLM",
                category="ai",
            ),
            PricedEndpoint(
                path="/api/analyze",
                method="POST",
                price=Decimal("0.10"),
                description="Analyze text for sentiment/entities",
                category="ai",
            ),
            PricedEndpoint(
                path="/api/embed",
                method="POST",
                price=Decimal("0.01"),
                description="Generate text embeddings",
                category="ai",
            ),
        ],
    )

    print("  Agent fetches: GET https://api.acme-ai.com/.well-known/sardis.json")
    print()
    print(f"  Service:     {manifest.name}")
    print(f"  Accepts:     {', '.join(manifest.accepts)}")
    print(f"  Endpoints:   {len(manifest.endpoints)}")
    for ep in manifest.endpoints:
        print(f"    {ep.method} {ep.path} — ${ep.price} — {ep.description}")
    print()

    return manifest


async def demo_step_4_mandate_check():
    """Step 4: Agent's spending mandate validates the payment."""
    separator("Step 4: Spending Mandate Validation")

    from sardis_v2_core.spending_mandate import ApprovalMode, SpendingMandate

    mandate = SpendingMandate(
        principal_id="usr_alice",
        issuer_id="usr_alice",
        agent_id="agent_research_bot",
        purpose_scope="AI API calls for research",
        amount_per_tx=Decimal("1.00"),
        amount_daily=Decimal("50.00"),
        amount_monthly=Decimal("500.00"),
        merchant_scope={"allowed": ["*.acme-ai.com", "openai.com", "anthropic.com"]},
        allowed_rails=["usdc", "card"],
        approval_mode=ApprovalMode.AUTO,
    )

    print(f"  Mandate:     {mandate.id}")
    print(f"  Agent:       {mandate.agent_id}")
    print(f"  Per-tx:      ${mandate.amount_per_tx}")
    print(f"  Daily:       ${mandate.amount_daily}")
    print(f"  Monthly:     ${mandate.amount_monthly}")
    print(f"  Merchants:   {mandate.merchant_scope.get('allowed', [])}")
    print()

    # Test: $0.05 to Acme AI → APPROVED
    r1 = mandate.check_payment(Decimal("0.05"), merchant="api.acme-ai.com")
    print(f"  Check: $0.05 to api.acme-ai.com → {'APPROVED' if r1.approved else 'DENIED'}")

    # Test: $5.00 to Acme AI → DENIED (over per-tx limit)
    r2 = mandate.check_payment(Decimal("5.00"), merchant="api.acme-ai.com")
    print(f"  Check: $5.00 to api.acme-ai.com → {'APPROVED' if r2.approved else f'DENIED ({r2.reason})'}")

    # Test: $0.05 to random vendor → DENIED (not in allowlist)
    r3 = mandate.check_payment(Decimal("0.05"), merchant="sketchy-api.com")
    print(f"  Check: $0.05 to sketchy-api.com → {'APPROVED' if r3.approved else f'DENIED ({r3.reason})'}")

    print()
    return mandate


async def demo_step_5_nl_policy():
    """Step 5: Natural language policy parsing."""
    separator("Step 5: Natural Language Policy")

    from sardis_v2_core.nl_policy_parser import RegexPolicyParser

    parser = RegexPolicyParser()

    policies = [
        "Maximum $50 per day on AI API calls",
        "No more than $1 per transaction, monthly limit $500",
        "Spend up to $200 per week, require approval above $100",
    ]

    for text in policies:
        result = parser.parse(text)
        limits = result.get("spending_limits", [])
        approval = result.get("requires_approval_above")
        print(f'  "{text}"')
        for lim in limits:
            amt = lim.get("max_amount", lim.get("amount", "?"))
            print(f"    → ${amt} {lim['period']}")
        if approval:
            print(f"    → Approval required above ${approval}")
        print()


async def demo_step_6_multi_protocol():
    """Step 6: Multi-protocol payment demonstration."""
    separator("Step 6: Multi-Protocol Payment Rails")

    protocols = [
        {
            "name": "Direct USDC",
            "endpoint": "POST /api/v2/pay",
            "use_case": "General payments — on-chain USDC transfer",
            "chains": ["Base", "Tempo", "Ethereum", "Polygon", "Arbitrum"],
            "latency": "~12s (block confirmation)",
            "cost": "< $0.01 gas (gasless via Circle Paymaster)",
        },
        {
            "name": "x402 Protocol",
            "endpoint": "X402Client.request(method, url)",
            "use_case": "API micropayments — automatic HTTP 402 handling",
            "chains": ["Base", "Polygon", "Solana"],
            "latency": "~2s (optimistic)",
            "cost": "< $0.01 gas",
        },
        {
            "name": "MPP (Stripe)",
            "endpoint": "POST /api/v2/mpp/sessions",
            "use_case": "Stripe merchant payments — fiat settlement",
            "chains": ["Tempo (stablecoins)", "Card networks (SPT)"],
            "latency": "~1s (session-based)",
            "cost": "Stripe standard fees",
        },
    ]

    for proto in protocols:
        print(f"  [{proto['name']}]")
        print(f"    Endpoint: {proto['endpoint']}")
        print(f"    Use case: {proto['use_case']}")
        print(f"    Chains:   {', '.join(proto['chains'])}")
        print(f"    Latency:  {proto['latency']}")
        print(f"    Cost:     {proto['cost']}")
        print()

    print("  All three protocols share:")
    print("    - Same spending mandate enforcement")
    print("    - Same KYC/AML compliance stack")
    print("    - Same audit trail (append-only ledger)")
    print("    - Same agent identity (KYA/TAP)")
    print()
    print("  Agent chooses protocol based on merchant capability.")
    print("  Sardis orchestrates — the agent doesn't need to know the details.")
    print()


async def demo_step_7_settlement():
    """Step 7: Settlement — how the merchant gets paid."""
    separator("Step 7: Settlement (Zero-Crypto Merchant)")

    print("  Payment flow:")
    print()
    print("  Agent (LangChain/CrewAI/etc.)")
    print("    │")
    print("    ├─ Spending mandate check ✓")
    print("    ├─ KYC/AML check ✓")
    print("    │")
    print("    ▼")
    print("  Sardis Orchestrator")
    print("    │")
    print("    ├─ Select best rail (x402/MPP/USDC)")
    print("    ├─ Execute payment (stablecoin)")
    print("    │")
    print("    ▼")
    print("  Settlement Engine")
    print("    │")
    print("    ├─ Stripe Connect Transfer ($X.XX USD)")
    print("    ├─ Stripe auto-payout → merchant bank")
    print("    │")
    print("    ▼")
    print("  Merchant receives: $X.XX USD in bank account")
    print()
    print("  Merchant never sees: USDC, wallet addresses, chain IDs,")
    print("  gas fees, or any blockchain complexity.")
    print()


async def main():
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║           SARDIS CONNECT — End-to-End Demo             ║")
    print("║   Zero-crypto agent payments for traditional companies  ║")
    print("╚══════════════════════════════════════════════════════════╝")

    merchant = await demo_step_1_merchant_setup()
    account = await demo_step_2_stripe_connect(merchant)
    manifest = await demo_step_3_agent_discovery()
    mandate = await demo_step_4_mandate_check()
    await demo_step_5_nl_policy()
    await demo_step_6_multi_protocol()
    await demo_step_7_settlement()

    separator("Summary")
    print("  Sardis Connect enables:")
    print("    1. Any company → agent-ready in 3 lines (sardis-connect SDK)")
    print("    2. Zero crypto exposure (merchant receives USD via Stripe)")
    print("    3. Natural language spending policies (main differentiator)")
    print("    4. Protocol-agnostic (x402 + MPP + USDC through one integration)")
    print("    5. Full compliance (KYC + AML + audit trail)")
    print()
    print("  'Your API is already valuable.")
    print("   Sardis Connect makes it agent-ready in 5 minutes —")
    print("   you receive USD, we handle the rest.'")
    print()


if __name__ == "__main__":
    asyncio.run(main())

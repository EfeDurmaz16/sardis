"""Issue a virtual card to an AI agent with spending policy + auth simulation.

Lifecycle exercised:
  1. Create an agent wallet identifier.
  2. Issue a multi-use virtual card via the MockProvider (no real PCI flow).
  3. Apply a spending policy (per-tx cap + blocked MCC categories).
  4. Simulate two Lithic-style ASA (Authorization Stream Access) requests:
     one within policy (APPROVE), one over the per-tx cap (DECLINE).
  5. Print decisions + audit trail.
"""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sardis.cards import CardService, CardType
from sardis.cards.providers.mock import MockProvider


AGENT_WALLET_ID = "wallet_agent_research_bot_001"


def policy_check(per_tx_cap: Decimal, blocked_mcc: set[str]):
    def _check(amount: Decimal, mcc: str, merchant: str) -> tuple[bool, str]:
        if mcc in blocked_mcc:
            return False, f"blocked_mcc:{mcc}"
        if amount > per_tx_cap:
            return False, f"over_per_tx_cap:{amount}>{per_tx_cap}"
        return True, "ok"
    return _check


async def main() -> None:
    service = CardService(provider=MockProvider())
    print(f"[provider] {service.provider_name}")

    card = await service.issue_card(
        wallet_id=AGENT_WALLET_ID,
        card_type=CardType.MULTI_USE,
        limit_per_tx=Decimal("250.00"),
        limit_daily=Decimal("1000.00"),
        limit_monthly=Decimal("5000.00"),
        auto_activate=True,
    )
    print(
        f"[card.issued] id={card.card_id} last4={card.card_number_last4} "
        f"status={card.status.value} per_tx={card.limit_per_tx} "
        f"daily={card.limit_daily} monthly={card.limit_monthly}"
    )

    check = policy_check(
        per_tx_cap=Decimal("250.00"),
        blocked_mcc={"7995", "5933"},  # gambling, pawn shops
    )

    auth_requests = [
        ("Anthropic API",          "7372", Decimal("42.50")),   # software -> approve
        ("Lottery House",          "7995", Decimal("10.00")),   # gambling -> decline
        ("AWS EC2",                "7399", Decimal("310.00")),  # over per-tx -> decline
        ("Vercel Pro",             "7372", Decimal("20.00")),   # approve
    ]

    print("\n--- ASA auth simulation ---")
    audit: list[dict] = []
    for merchant, mcc, amount in auth_requests:
        allowed, reason = check(amount, mcc, merchant)
        decision = "APPROVE" if allowed else "DECLINE"
        print(f"[asa] {decision:7} {merchant:18} mcc={mcc} amount=${amount:>7} -> {reason}")
        audit.append({
            "merchant": merchant, "mcc": mcc, "amount": str(amount),
            "decision": decision, "reason": reason,
        })

    approved = sum(1 for e in audit if e["decision"] == "APPROVE")
    declined = len(audit) - approved
    print(f"\n[summary] card={card.card_id} approved={approved} declined={declined}")
    print("[demo] OK — virtual card lifecycle complete (issue -> policy -> auth -> decision)")


if __name__ == "__main__":
    asyncio.run(main())

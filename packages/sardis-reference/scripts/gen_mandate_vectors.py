#!/usr/bin/env python3
"""Generate golden mandate-check vectors from the Python SpendingMandate.

GITIGNORED tooling (run once; output committed). Drives
`SpendingMandate.check_payment` over a fixed matrix and dumps {mandate, spend,
expected} in the TS-facing shape (minor units at 2 decimals) so
`@sardis/reference` `checkMandate` is asserted identical (approved + errorCode +
requiresApproval).

Usage:
    python3 scripts/gen_mandate_vectors.py > __tests__/vectors/mandate-checks.json
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from sardis.core.spending_mandate import (  # noqa: E402
    ApprovalMode,
    MandateStatus,
    SpendingMandate,
)

CURRENCY = "USDC"
# A fixed "now" expressed both as the wall clock (Python uses datetime.now) and
# epoch ms (TS uses injectable now). We bound validity windows generously around
# the present so Python's is_active (wall clock) agrees with TS now=NOW_MS.
NOW = datetime.now(UTC)
NOW_MS = int(NOW.timestamp() * 1000)


def minor(amount) -> int:
    return int((Decimal(str(amount)) * 100).to_integral_value())


def money(amount) -> dict:
    return {"minor": str(minor(amount)), "currency": CURRENCY}


VECTORS: list[dict] = []


def emit(name: str, mandate: SpendingMandate, mandate_json: dict, spend_kw: dict, ts_spend: dict):
    res = mandate.check_payment(**spend_kw)
    VECTORS.append(
        {
            "name": name,
            "mandate": mandate_json,
            "spend": ts_spend,
            "now": NOW_MS,
            "expected": {
                "approved": res.approved,
                "errorCode": res.error_code,
                "requiresApproval": res.requires_approval,
            },
        }
    )


def base_mandate_json(**overrides) -> dict:
    d = {
        "id": "mandate_test",
        "status": "active",
        "validFromMs": NOW_MS - 60_000,
        "expiresAtMs": NOW_MS + 3_600_000,
        "merchantScope": {},
        "amountPerTx": money("500"),
        "amountTotal": money("1000"),
        "spentTotal": money("0"),
        "currency": CURRENCY,
        "allowedRails": ["card", "usdc", "bank"],
        "approvalMode": "auto",
    }
    d.update(overrides)
    return d


def make_mandate(**kw) -> SpendingMandate:
    m = SpendingMandate(
        principal_id="p",
        issuer_id="p",
        agent_id="a",
        amount_per_tx=Decimal("500"),
        amount_total=Decimal("1000"),
        currency=CURRENCY,
        valid_from=NOW - timedelta(minutes=1),
        expires_at=NOW + timedelta(hours=1),
        approval_mode=ApprovalMode.AUTO,
    )
    for k, v in kw.items():
        setattr(m, k, v)
    return m


def main() -> None:
    # 1. approved (auto)
    m = make_mandate()
    emit("approved_auto", m, base_mandate_json(),
         {"amount": Decimal("100")}, {"amount": money("100")})

    # 2. MANDATE_NOT_ACTIVE (revoked)
    m = make_mandate(status=MandateStatus.REVOKED)
    emit("not_active_revoked", m, base_mandate_json(status="revoked"),
         {"amount": Decimal("100")}, {"amount": money("100")})

    # 3. MANDATE_AMOUNT_EXCEEDED
    m = make_mandate()
    emit("amount_exceeded", m, base_mandate_json(),
         {"amount": Decimal("600")}, {"amount": money("600")})

    # 4. MANDATE_BUDGET_EXHAUSTED (spent 950, total 1000, spend 100)
    m = make_mandate(spent_total=Decimal("950"))
    emit("budget_exhausted", m, base_mandate_json(spentTotal=money("950")),
         {"amount": Decimal("100")}, {"amount": money("100")})

    # 5. MANDATE_MERCHANT_BLOCKED
    m = make_mandate(merchant_scope={"blocked": ["evil.com"]})
    emit("merchant_blocked", m, base_mandate_json(merchantScope={"blocked": ["evil.com"]}),
         {"amount": Decimal("10"), "merchant": "evil.com"},
         {"amount": money("10"), "merchant": "evil.com"})

    # 6. MANDATE_MERCHANT_NOT_ALLOWED
    m = make_mandate(merchant_scope={"allowed": ["good.com"]})
    emit("merchant_not_allowed", m, base_mandate_json(merchantScope={"allowed": ["good.com"]}),
         {"amount": Decimal("10"), "merchant": "other.com"},
         {"amount": money("10"), "merchant": "other.com"})

    # 7. wildcard allowed (*.foo.com)
    m = make_mandate(merchant_scope={"allowed": ["*.foo.com"]})
    emit("merchant_wildcard_allowed", m, base_mandate_json(merchantScope={"allowed": ["*.foo.com"]}),
         {"amount": Decimal("10"), "merchant": "api.foo.com"},
         {"amount": money("10"), "merchant": "api.foo.com"})

    # 8. MANDATE_RAIL_NOT_ALLOWED
    m = make_mandate(allowed_rails=["usdc"])
    emit("rail_not_allowed", m, base_mandate_json(allowedRails=["usdc"]),
         {"amount": Decimal("10"), "rail": "card"},
         {"amount": money("10"), "rail": "card"})

    # 9. MANDATE_CHAIN_NOT_ALLOWED
    m = make_mandate(allowed_chains=["base"])
    emit("chain_not_allowed", m, base_mandate_json(allowedChains=["base"]),
         {"amount": Decimal("10"), "chain": "polygon"},
         {"amount": money("10"), "chain": "polygon"})

    # 10. MANDATE_TOKEN_NOT_ALLOWED
    m = make_mandate(allowed_tokens=["USDC"])
    emit("token_not_allowed", m, base_mandate_json(allowedTokens=["USDC"]),
         {"amount": Decimal("10"), "token": "USDT"},
         {"amount": money("10"), "token": "USDT"})

    # 11. requires_approval (threshold mode)
    m = make_mandate(approval_mode=ApprovalMode.THRESHOLD, approval_threshold=Decimal("50"))
    emit("requires_approval_threshold", m,
         base_mandate_json(approvalMode="threshold", approvalThreshold=money("50")),
         {"amount": Decimal("100")}, {"amount": money("100")})

    # 12. always_human → requires approval even for small amount
    m = make_mandate(approval_mode=ApprovalMode.ALWAYS_HUMAN)
    emit("always_human", m, base_mandate_json(approvalMode="always_human"),
         {"amount": Decimal("1")}, {"amount": money("1")})

    json.dump(VECTORS, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

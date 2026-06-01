#!/usr/bin/env python3
"""Generate AP2 verification vectors.

GITIGNORED tooling. The full `verify_chain` requires server-owned settings +
identity registry + replay cache; the reference package's `verifyChainStructure`
omits those layers by design. So this script:

  - authoritatively generates `_compute_drift` outputs from the Python
    MandateVerifier (the drift math is pure and server-independent), and
  - emits a fixed chain matrix with the EXPECTED structural reason codes derived
    directly from `verify_chain`'s documented check order, plus a real
    action_description_hash (sha256 of the NL description) so the origin-binding
    check is exercised with Python-computed hashes.

Usage:
    python3 scripts/gen_ap2_vectors.py > __tests__/vectors/ap2-chains.json
"""
from __future__ import annotations

import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

from sardis.protocol.verifier import MandateVerifier  # noqa: E402


@dataclass
class _Intent:
    requested_amount: int | None
    scope: list[str]


@dataclass
class _Payment:
    amount_minor: int
    merchant_domain: str | None


NOW = 1_000_000  # epoch seconds; all mandates expire after this


def base_chain(**overrides) -> dict:
    nl = "Buy cloud compute from AWS"
    desc_hash = hashlib.sha256(nl.encode()).hexdigest()
    intent = {
        "mandateId": "i1", "mandateType": "intent", "subject": "agent_x", "purpose": "intent",
        "expiresAt": NOW + 600, "scope": ["cloud"], "requestedAmount": 10_000,
        "naturalLanguageDescription": nl, "actionDescriptionHash": desc_hash,
    }
    cart = {
        "mandateId": "c1", "mandateType": "cart", "subject": "agent_x", "purpose": "cart",
        "expiresAt": NOW + 600, "merchantDomain": "aws.amazon.com",
        "subtotalMinor": 9_000, "taxesMinor": 1_000, "currency": "USD",
    }
    payment = {
        "mandateId": "p1", "mandateType": "payment", "subject": "agent_x", "purpose": "checkout",
        "expiresAt": NOW + 600, "amountMinor": 10_000, "destination": "0xabc",
        "merchantDomain": "aws.amazon.com", "aiAgentPresence": True,
        "transactionModality": "human_present",
    }
    chain = {"intent": intent, "cart": cart, "payment": payment}
    for k, v in overrides.items():
        section, field = k.split("__", 1)
        chain[section] = {**chain[section], field: v}
    return chain


def drift(intent_amount, scope, pay_amount, merchant):
    i = _Intent(requested_amount=intent_amount, scope=scope)
    p = _Payment(amount_minor=pay_amount, merchant_domain=merchant)
    score, reasons = MandateVerifier._compute_drift(i, p)
    return {"score": score, "reasons": reasons}


def main() -> None:
    vectors = []

    def add(name, chain, expected_accepted, expected_reason=None):
        vectors.append({
            "name": name, "chain": chain, "now": NOW,
            "expected": {"accepted": expected_accepted, "reason": expected_reason},
        })

    add("valid_chain", base_chain(), True)
    add("intent_invalid_type", base_chain(intent__mandateType="bogus"), False, "intent_invalid_type")
    add("cart_invalid_type", base_chain(cart__purpose="bogus"), False, "cart_invalid_type")
    add("payment_invalid_type", base_chain(payment__purpose="bogus"), False, "payment_invalid_type")
    add("agent_presence_required", base_chain(payment__aiAgentPresence=False), False, "payment_agent_presence_required")
    add("subject_mismatch", base_chain(payment__subject="other"), False, "subject_mismatch")
    add("merchant_domain_mismatch", base_chain(payment__merchantDomain="evil.com"), False, "merchant_domain_mismatch")
    add("payment_exceeds_cart_total", base_chain(payment__amountMinor=20_000), False, "payment_exceeds_cart_total")
    # high-risk merchant → drift 1.0 → goal_drift_scope_mismatch (also mismatched cart domain,
    # but drift is checked after the domain match; keep cart in sync to isolate drift)
    hr = base_chain(cart__merchantDomain="casino.com", payment__merchantDomain="casino.com")
    add("goal_drift_scope_mismatch", hr, False, "goal_drift_scope_mismatch")
    # tampered action description hash
    add("action_description_hash_mismatch", base_chain(intent__actionDescriptionHash="deadbeef"), False, "action_description_hash_mismatch")
    # expired
    add("mandate_expired", base_chain(intent__expiresAt=NOW - 1), False, "mandate_expired")

    out = {
        "chains": vectors,
        # Authoritative drift outputs from the Python _compute_drift.
        "drift": [
            {"name": "in_scope", "intentAmount": 10_000, "scope": ["cloud"], "payAmount": 10_000, "merchant": "aws.amazon.com",
             "expected": drift(10_000, ["cloud"], 10_000, "aws.amazon.com")},
            {"name": "scope_mismatch", "intentAmount": 10_000, "scope": ["cloud"], "payAmount": 10_000, "merchant": "randomshop.com",
             "expected": drift(10_000, ["cloud"], 10_000, "randomshop.com")},
            {"name": "amount_deviation", "intentAmount": 10_000, "scope": ["cloud"], "payAmount": 15_000, "merchant": "aws.amazon.com",
             "expected": drift(10_000, ["cloud"], 15_000, "aws.amazon.com")},
            {"name": "high_risk", "intentAmount": 10_000, "scope": ["cloud"], "payAmount": 10_000, "merchant": "casino.com",
             "expected": drift(10_000, ["cloud"], 10_000, "casino.com")},
        ],
    }
    json.dump(out, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()

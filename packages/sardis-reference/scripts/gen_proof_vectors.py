#!/usr/bin/env python3
"""Generate golden proof vectors from the Python authority primitives.

GITIGNORED tooling (run once; output committed). Produces:
  - authority-proof.json: a JWS + base64url public key + tampered variants
    (the moat: a proof signed in Python verifies offline in TS with only the
    published key; any tamper fails).
  - delegation-evidence.json: a signed DelegationEvidence + one-byte tamper.
  - revocation-proof.json: a signed RevocationProof (mixed kill statuses) +
    tamper + a compute_outcome matrix.

Uses the deterministic dev signing paths (dev ed25519 seed; explicit HMAC
secret) — test-only keys, never production secrets.

Usage:
    python3 scripts/gen_proof_vectors.py
"""
from __future__ import annotations

import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

_SARDIS_SRC = Path(__file__).resolve().parents[2] / "sardis" / "src"
sys.path.insert(0, str(_SARDIS_SRC))

_OUT = Path(__file__).resolve().parent.parent / "__tests__" / "vectors"

from sardis.core.authority_proof import (  # noqa: E402
    build_authority_proof,
    public_key_b64url,
)
from sardis.core.delegation import (  # noqa: E402
    Delegation,
    DelegationScope,
    DelegatorKind,
)
from sardis.core.revocation import (  # noqa: E402
    KillStatus,
    PropagationKind,
    PropagationTarget,
    RevocationStatus,
    RevocationTargetKind,
    build_revocation,
)

ISSUED = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
HMAC_SECRET = "dev-test-secret-do-not-use-in-prod"


def gen_authority_proof() -> None:
    proof = build_authority_proof(
        action_id="act_123",
        agent="agent_b",
        amount_minor=5_000_000,  # 5 USDC (6 decimals)
        currency="USDC",
        counterparty="merchant.example",
        policy_hash="ph_abc",
        mandate_hash="mh_def",
        spending_mandate_id="mandate_root",
        amount="5.0",
        inputs={"rail": "usdc", "chain": "base", "token": "USDC", "category": "cloud"},
        delegation_chain=None,
        issued_at=ISSUED,
    )
    jws = proof.to_jws()
    pub = public_key_b64url()
    claim = proof.to_dict()

    out = {
        "publicKeyB64u": pub,
        "valid": {"jws": jws, "expectValid": True},
        # Tampered: flip the amount in the claim, keep the original signature.
        "tampered_amount": _tamper_claim(claim, jws, {"amount_minor": 9_999_999}),
        "tampered_counterparty": _tamper_claim(claim, jws, {"counterparty": "attacker.example"}),
        "wrong_key": {
            "jws": jws,
            "publicKeyB64u": "A" * 43,  # 32-byte all-ones-ish wrong key (base64url, 43 chars)
            "expectValid": False,
        },
    }
    _write("authority-proof.json", out)


def _tamper_claim(claim: dict, original_jws: str, patch: dict) -> dict:
    """Build a tampered JWS by patching the canonical claim payload but keeping
    the ORIGINAL signature — verification must fail."""
    import base64

    tampered = dict(claim)
    tampered.pop("content_hash", None)
    tampered.pop("signature", None)
    tampered.update(patch)
    # Re-encode the claim WITHOUT re-signing, reusing the original signature.
    canonical = json.dumps(tampered, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    payload_b64 = base64.urlsafe_b64encode(canonical.encode()).rstrip(b"=").decode("ascii")
    _, sig = original_jws.split(".", 1)
    return {"jws": f"{payload_b64}.{sig}", "expectValid": False}


def gen_delegation_evidence() -> None:
    scope = DelegationScope(counterparties=["aws.com"], categories=["cloud"], rails=["usdc"])
    dlg = Delegation(
        delegator_kind=DelegatorKind.MANDATE,
        delegator_ref="mandate_root",
        delegator_principal="agent_a",
        delegatee="agent_b",
        root_mandate_id="mandate_root",
        amount_cap=Decimal("50"),
        currency="USDC",
        scope=scope,
        depth=1,
        created_at=ISSUED,
        id="dlg_fixed_1",
    )
    ev = dlg.build_evidence(secret=HMAC_SECRET)
    d = ev.to_dict()
    ts = {
        "delegationId": d["delegation_id"],
        "delegatorKind": d["delegator_kind"],
        "delegatorRef": d["delegator_ref"],
        "delegatorPrincipal": d["delegator_principal"],
        "delegatee": d["delegatee"],
        "rootMandateId": d["root_mandate_id"],
        "depth": d["depth"],
        "amountCap": d["amount_cap"],
        "currency": d["currency"],
        "expiresAt": d["expires_at"],
        "scopeHash": d["scope_hash"],
        "createdAt": d["created_at"],
        "decisionHash": d["decision_hash"],
        "signature": d["signature"],
    }
    out = {"secret": HMAC_SECRET, "valid": ts, "expectValid": True}
    _write("delegation-evidence.json", out)


def gen_revocation_proof() -> None:
    rev = build_revocation(
        target_kind=RevocationTargetKind.AGENT,
        target_ref="agent_b",
        requested_by="principal_a",
        scope="all",
    )
    rev.requested_at = ISSUED
    rev.add_target(PropagationTarget(kind=PropagationKind.MANDATE, ref="mandate_root", kill_status=KillStatus.KILLED))
    rev.add_target(PropagationTarget(kind=PropagationKind.CARD, ref="card_1", kill_status=KillStatus.ALREADY_DEAD))
    rev.status = rev.compute_outcome()  # all confirmed dead -> propagated
    proof = rev.build_proof(secret=HMAC_SECRET)
    proof.revoked_at = ISSUED
    proof = proof.sign(secret=HMAC_SECRET)
    d = proof.to_dict()
    ts = {
        "revocationId": d["revocation_id"],
        "targetKind": d["target_kind"],
        "targetRef": d["target_ref"],
        "scope": d["scope"],
        "requestedBy": d["requested_by"],
        "revokedAt": d["revoked_at"],
        "outcome": d["outcome"],
        "targets": [
            {"kind": t["kind"], "ref": t["ref"], "killStatus": t["kill_status"], "detail": t.get("detail", "")}
            for t in d["targets"]
        ],
        "decisionHash": d["decision_hash"],
        "signature": d["signature"],
    }

    # compute_outcome matrix
    def outcome_for(statuses: list[str]) -> str:
        r = build_revocation(target_kind=RevocationTargetKind.AGENT, target_ref="x", requested_by="y")
        for i, s in enumerate(statuses):
            r.add_target(PropagationTarget(kind=PropagationKind.MANDATE, ref=f"m{i}", kill_status=KillStatus(s)))
        return r.compute_outcome().value

    matrix = [
        {"statuses": ["killed", "already_dead"], "expected": outcome_for(["killed", "already_dead"])},
        {"statuses": ["killed", "blocked_pending"], "expected": outcome_for(["killed", "blocked_pending"])},
        {"statuses": ["failed"], "expected": outcome_for(["failed"])},
    ]
    assert RevocationStatus.PROPAGATED.value == "propagated"
    out = {"secret": HMAC_SECRET, "valid": ts, "expectValid": True, "outcomeMatrix": matrix}
    _write("revocation-proof.json", out)


def _write(name: str, obj: dict) -> None:
    path = _OUT / name
    path.write_text(json.dumps(obj, indent=2) + "\n")
    print(f"wrote {path.relative_to(_OUT.parent.parent)}", file=sys.stderr)


def main() -> None:
    gen_authority_proof()
    gen_delegation_evidence()
    gen_revocation_proof()


if __name__ == "__main__":
    main()

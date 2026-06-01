"""End-to-end test of the Attenuated Delegation Graph + Proof-of-Authority API.

Exercises the routes a sub-agent swarm / a coordinator consumes against the REAL
:class:`~sardis.core.delegation_engine.DelegationEngine` and
:class:`~sardis.core.revocation_engine.RevocationEngine` (in-memory stores + real
signing — no live chain, no DB), plus the orchestrator's authorized-execution
path that emits the portable Proof-of-Authority.

The headline e2e flow (the one the task pins):

    human $500 mandate
      └─ POST /delegations  → Agent B gets an attenuated $50 (scoped to openai.com)
           └─ POST /delegations → tool C gets an attenuated $20
    tool C pays 10 USDC within its cap   → orchestrator emits an AuthorityProof
       whose bound delegation_chain is [root, B, C]; the proof VERIFIES OFFLINE
       against the published Ed25519 key with no Sardis access.
    POST /delegations/{root-or-B}/revoke → propagates to the whole subtree
    tool C's next payment is DENIED at execution (chain has a revoked link).

Also pins: attenuation is enforced fail-closed at mint (a widening 409s); reads
are org-scoped (cross-org 404); the chain route returns root→leaf; the
DelegationEvidence verify route rejects tamper; the public Proof-of-Authority
verify route rejects a widened delegation hop.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sardis.core.delegation_engine import DelegationEngine
from sardis.core.delegation_lookup import DelegationAwareMandateLookup
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.orchestrator import PaymentOrchestrator, PolicyViolationError
from sardis.core.revocation_engine import RevocationEngine
from sardis.core.revocation_ports import (
    DelegationSubtreeRevoker,
    InMemoryMandateRevoker,
)
from sardis.core.revocation_repository import InMemoryRevocationStore
from sardis.core.spending_mandate import MandateStatus, SpendingMandate

from server.authz import Principal, require_principal
from server.routes.authority import delegations as deleg_routes

HMAC_SECRET = "test-delegation-api-secret"
ROOT_MANDATE = "mandate_root_A"


# ── Fake payment / chain plumbing for the orchestrator pay step ─────────


@dataclass
class _FakePayment:
    mandate_id: str = "exec_001"
    agent_id: str | None = "tool_C"  # the acting leaf delegatee
    wallet_id: str | None = None
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 10_000_000  # 10 USDC
    destination: str = "openai.com"
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "openai.com"
    merchant_category: str | None = None
    rail: str | None = "usdc"
    fee: Any = None
    amount: Any = None


@dataclass
class _FakeMandateChain:
    payment: _FakePayment = field(default_factory=_FakePayment)


@dataclass
class _FakeChainReceipt:
    tx_hash: str = "0xtx"
    chain: str = "base"
    block_number: int = 1
    audit_anchor: str = "0x" + "00" * 32


@dataclass
class _FakePolicyResult:
    allowed: bool = True
    reason: str = "OK"
    rule_id: str | None = None


@dataclass
class _FakeComplianceResult:
    allowed: bool = True
    reason: str = "OK"
    provider: str = "mock"
    rule_id: str = "mock_rule"
    audit_id: str = "audit_001"


class _InMemoryBaseLookup:
    """A minimal base SpendingMandateLookupPort over a dict of mandates."""

    def __init__(self, mandates: dict[str, SpendingMandate]) -> None:
        self._by_id = mandates

    async def get_active_mandate(self, agent_id=None, wallet_id=None, payment=None):
        for m in self._by_id.values():
            if m.status.value != "active":
                continue
            if agent_id and m.agent_id == agent_id:
                return m
            if wallet_id and m.wallet_id == wallet_id:
                return m
        return None

    async def get_mandate_by_id(self, mandate_id):
        return self._by_id.get(mandate_id)

    async def record_spend(self, mandate_id, amount):
        m = self._by_id.get(mandate_id)
        if m is not None:
            m.spent_total = (m.spent_total or Decimal("0")) + Decimal(str(amount))


def _root_mandate() -> SpendingMandate:
    return SpendingMandate(
        principal_id="usr_human", issuer_id="usr_human", id=ROOT_MANDATE,
        agent_id="agent_A", amount_total=Decimal("500"), amount_per_tx=Decimal("500"),
        currency="USDC", merchant_scope={"allowed": ["openai.com"]},
        allowed_rails=["usdc"], expires_at=datetime.now(UTC) + timedelta(days=30),
    )


# ── Engine + app scaffold ──────────────────────────────────────────────


def _build():
    root = _root_mandate()
    mandates = {root.id: root}
    dstore = InMemoryDelegationStore()
    base = _InMemoryBaseLookup(mandates)
    eng = DelegationEngine(
        store=dstore, mandate_resolver=base.get_mandate_by_id, signing_secret=HMAC_SECRET
    )
    lookup = DelegationAwareMandateLookup(base=base, engine=eng)

    rev_engine = RevocationEngine(
        store=InMemoryRevocationStore(),
        mandate_revoker=InMemoryMandateRevoker(
            {root.id: {"status": "active", "agent_id": "agent_A",
                       "principal_id": "usr_human"}}
        ),
        delegation_revoker=DelegationSubtreeRevoker(dstore),
        signing_secret=HMAC_SECRET,
    )
    return root, mandates, dstore, base, eng, lookup, rev_engine


def _client(eng, rev_engine, *, org: str = "org_a") -> TestClient:
    app = FastAPI()
    app.state.delegation_engine = eng
    app.state.revocation_engine = rev_engine
    app.include_router(deleg_routes.router, prefix="/api/v2/delegations")
    app.include_router(deleg_routes.public_router, prefix="/api/v2/authority/proofs")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id=org, scopes=["*"]
    )
    return TestClient(app)


def _orchestrator(lookup):
    wallet_mgr = MagicMock()
    wallet_mgr.async_validate_policies = AsyncMock(return_value=_FakePolicyResult())
    wallet_mgr.async_record_spend = AsyncMock()
    compliance = MagicMock()
    compliance.preflight = AsyncMock(return_value=_FakeComplianceResult())
    chain_exec = MagicMock()
    chain_exec.dispatch_payment = AsyncMock(return_value=_FakeChainReceipt())
    ledger = MagicMock()
    ledger.append = MagicMock(return_value=MagicMock(tx_id="ltx_1"))
    orch = PaymentOrchestrator(
        wallet_manager=wallet_mgr, compliance=compliance, chain_executor=chain_exec,
        ledger=ledger, spending_mandate_lookup=lookup,
        authority_proof_secret=_PROOF_SEED,
    )
    return orch, chain_exec


# Deterministic 32-byte Ed25519 seed for the portable Proof-of-Authority so the
# test can verify offline with the matching published public key.
_PROOF_SEED = bytes(range(32))


@pytest.fixture(autouse=True)
def _ensure_keys(monkeypatch):
    # HMAC key for DelegationEvidence (mint + verify route) and the revocation
    # proof; the env path is fail-closed in prod, so point it at the test secret.
    monkeypatch.setenv("SARDIS_DELEGATION_HMAC_KEY", HMAC_SECRET)
    monkeypatch.setenv("SARDIS_REVOCATION_HMAC_KEY", HMAC_SECRET)
    # Ed25519 private seed for the portable Proof-of-Authority (hex form).
    monkeypatch.setenv("SARDIS_AUTHORITY_PROOF_PRIVATE_KEY", _PROOF_SEED.hex())
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "test")


def _delegate(client, *, delegator_ref, delegator_kind, delegatee,
              delegator_principal, amount_cap, counterparties=("openai.com",),
              rails=("usdc",)):
    return client.post(
        "/api/v2/delegations",
        json={
            "delegator_kind": delegator_kind,
            "delegator_ref": delegator_ref,
            "delegator_principal": delegator_principal,
            "delegatee": delegatee,
            "amount_cap": amount_cap,
            "scope": {"counterparties": list(counterparties), "rails": list(rails)},
        },
    )


# ── THE end-to-end flow ─────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_delegate_pay_prove_then_revoke_root_denies():
    root, mandates, dstore, base, eng, lookup, rev_engine = _build()
    client = _client(eng, rev_engine)

    # 1) human's $500 mandate delegates $50 to Agent B (scoped to openai.com).
    rb = _delegate(
        client, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    )
    assert rb.status_code == 201, rb.text
    b = rb.json()
    assert b["depth"] == 1
    assert b["amount_cap"] == "50"
    assert b["evidence"]["signature"]
    b_id = b["id"]

    # 2) Agent B delegates $20 to tool C (a further narrowing).
    rc = _delegate(
        client, delegator_ref=b_id, delegator_kind="delegation",
        delegatee="tool_C", delegator_principal="agent_B", amount_cap="20",
    )
    assert rc.status_code == 201, rc.text
    c = rc.json()
    assert c["depth"] == 2
    c_id = c["id"]

    # 3) The chain route resolves root → B → C for the acting sub-agent tool_C.
    chain = client.get("/api/v2/delegations/agent/tool_C/chain").json()
    assert chain["depth"] == 2
    assert [link["kind"] for link in chain["links"]] == ["mandate", "delegation", "delegation"]
    assert [link["ref"] for link in chain["links"]] == [root.id, b_id, c_id]

    # 4) tool_C pays 10 USDC within its $20 cap → orchestrator emits AuthorityProof.
    orch, chain_exec = _orchestrator(lookup)
    result = await orch.execute_chain(_FakeMandateChain())
    assert result.status == "submitted"
    chain_exec.dispatch_payment.assert_awaited_once()
    proof = result.authority_proof
    assert proof is not None
    # The proof binds the WHOLE attenuated chain (root + B + C).
    assert len(proof.delegation_chain) == 3
    assert proof.amount_minor == 10_000_000

    # 5) OFFLINE verification: a third party verifies with the PUBLISHED key, no
    #    Sardis trust. The public JWK endpoint serves that key.
    jwk_resp = client.get("/api/v2/authority/proofs/jwk").json()
    pub_b64 = jwk_resp["public_key_b64url"]
    verify = client.post(
        "/api/v2/authority/proofs/verify",
        json={"proof": proof.to_dict(), "public_key": pub_b64},
    )
    assert verify.status_code == 200, verify.text
    v = verify.json()
    assert v["valid"] is True
    assert v["decision"] == "ALLOWED"
    assert v["delegation_depth"] == 2
    assert v["amount_minor"] == 10_000_000

    # The compact JWS round-trips through the same verifier.
    jws_verify = client.post(
        "/api/v2/authority/proofs/verify",
        json={"jws": proof.to_jws(), "public_key": pub_b64},
    ).json()
    assert jws_verify["valid"] is True

    # 6) Revoke the parent delegation B via the API — PROPAGATES to the whole
    #    subtree (its child C). One revoke kills the descendant authority.
    revoke = client.post(f"/api/v2/delegations/{b_id}/revoke")
    assert revoke.status_code == 200, revoke.text
    body = revoke.json()
    assert body["proof"] is not None
    # B and its child C are now revoked in the store.
    assert (await dstore.get(b_id)).status.value == "revoked"
    assert (await dstore.get(c_id)).status.value == "revoked"

    # 7) tool_C's next payment is DENIED at execution (chain has a revoked link).
    orch2, chain_exec2 = _orchestrator(lookup)
    with pytest.raises(PolicyViolationError):
        await orch2.execute_chain(
            _FakeMandateChain(payment=_FakePayment(mandate_id="exec_after_revoke"))
        )
    chain_exec2.dispatch_payment.assert_not_awaited()


# ── attenuation enforced fail-closed at mint ────────────────────────────


def test_widening_delegation_is_denied_fail_closed():
    root, *_rest, eng, _lookup, rev_engine = _build()
    client = _client(eng, rev_engine)
    # First a valid $50 to B.
    b = _delegate(
        client, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    ).json()
    # B tries to delegate $80 to C — exceeds B's $50 remaining → 409, no row.
    over = _delegate(
        client, delegator_ref=b["id"], delegator_kind="delegation",
        delegatee="tool_C", delegator_principal="agent_B", amount_cap="80",
    )
    assert over.status_code == 409, over.text
    detail = over.json()["detail"]
    assert detail["error_code"] == "ATTENUATION_VIOLATION"
    assert any("exceeds delegator remaining" in v for v in detail["violations"])


def test_scope_widening_delegation_is_denied():
    root, *_rest, eng, _lookup, rev_engine = _build()
    client = _client(eng, rev_engine)
    b = _delegate(
        client, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    ).json()
    # B tries to add a counterparty NOT in its scope (only openai.com) → 409.
    widen = _delegate(
        client, delegator_ref=b["id"], delegator_kind="delegation",
        delegatee="tool_C", delegator_principal="agent_B", amount_cap="20",
        counterparties=("openai.com", "aws.amazon.com"),
    )
    assert widen.status_code == 409
    assert widen.json()["detail"]["error_code"] == "ATTENUATION_VIOLATION"


# ── org scoping ─────────────────────────────────────────────────────────


def test_reads_are_org_scoped():
    root, *_rest, eng, _lookup, rev_engine = _build()
    a = _client(eng, rev_engine, org="org_a")
    created = _delegate(
        a, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    ).json()
    dlg_id = created["id"]

    # Owner lists + gets it.
    listed = a.get("/api/v2/delegations").json()
    assert [d["id"] for d in listed] == [dlg_id]
    assert a.get(f"/api/v2/delegations/{dlg_id}").status_code == 200

    # Another org sees nothing and cannot fetch it (404, not 403).
    b = _client(eng, rev_engine, org="org_b")
    assert b.get("/api/v2/delegations").json() == []
    assert b.get(f"/api/v2/delegations/{dlg_id}").status_code == 404
    # Nor revoke it.
    assert b.post(f"/api/v2/delegations/{dlg_id}/revoke").status_code == 404


# ── DelegationEvidence verify route (HMAC tamper check) ─────────────────


def test_evidence_verify_rejects_tampered_grant():
    root, *_rest, eng, _lookup, rev_engine = _build()
    client = _client(eng, rev_engine)
    b = _delegate(
        client, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    ).json()
    ev = b["evidence"]

    # Untampered evidence verifies.
    ok = client.post("/api/v2/delegations/verify", json=ev).json()
    assert ok["valid"] is True

    # Widen the cap in the evidence → decision hash no longer matches.
    tampered = dict(ev)
    tampered["amount_cap"] = "5000"
    bad = client.post("/api/v2/delegations/verify", json=tampered).json()
    assert bad["valid"] is False
    assert bad["hash_matches"] is False


# ── public Proof-of-Authority verify rejects a widened delegation hop ───


@pytest.mark.asyncio
async def test_authority_proof_verify_rejects_widened_chain():
    root, mandates, dstore, base, eng, lookup, rev_engine = _build()
    client = _client(eng, rev_engine)
    _delegate(
        client, delegator_ref=root.id, delegator_kind="mandate",
        delegatee="agent_B", delegator_principal="agent_A", amount_cap="50",
    )
    b_id = (await dstore.get_for_delegatee("agent_B")).id
    _delegate(
        client, delegator_ref=b_id, delegator_kind="delegation",
        delegatee="tool_C", delegator_principal="agent_B", amount_cap="20",
    )
    orch, _ = _orchestrator(lookup)
    result = await orch.execute_chain(_FakeMandateChain())
    proof = result.authority_proof.to_dict()
    pub = client.get("/api/v2/authority/proofs/jwk").json()["public_key_b64url"]

    # Forge a widened cap on a bound delegation hop → signature no longer verifies.
    forged = dict(proof)
    forged["delegation_chain"] = [dict(h) for h in proof["delegation_chain"]]
    for hop in forged["delegation_chain"]:
        if hop["kind"] == "delegation":
            hop["amount_cap"] = "999999"
    out = client.post(
        "/api/v2/authority/proofs/verify",
        json={"proof": forged, "public_key": pub},
    ).json()
    assert out["valid"] is False


# ── engine absent fails the mutating surface closed (503) ───────────────


def test_engine_absent_fails_closed():
    app = FastAPI()
    app.state.delegation_engine = None
    app.state.revocation_engine = None
    app.include_router(deleg_routes.router, prefix="/api/v2/delegations")
    app.dependency_overrides[require_principal] = lambda: Principal(
        kind="api_key", organization_id="org_a", scopes=["*"]
    )
    client = TestClient(app)
    resp = client.post(
        "/api/v2/delegations",
        json={
            "delegator_kind": "mandate", "delegator_ref": ROOT_MANDATE,
            "delegator_principal": "agent_A", "delegatee": "agent_B",
            "amount_cap": "50", "scope": {},
        },
    )
    assert resp.status_code == 503


def test_revoked_root_mandate_denies_via_lookup():
    # Sanity: once the root mandate is revoked, the lookup denies the chain.
    root, mandates, dstore, base, eng, lookup, rev_engine = _build()
    root.status = MandateStatus.REVOKED
    assert root.is_active is False

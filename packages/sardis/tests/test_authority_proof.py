"""Tests for the portable Proof-of-Authority credential (offline verifiable).

Pins the primitive's contract:

* an ALLOWED execution emits an :class:`AuthorityProof` alongside the receipt;
* :meth:`verify` passes with the PUBLISHED public key (no Sardis, no DB);
* tampering ANY bound field (amount, counterparty, policy_hash, a delegation
  hop, …) fails verification;
* verifying with the WRONG key fails;
* a delegated action carries the whole attenuated delegation chain in the proof
  AND still verifies;
* export round-trips: ``to_dict``/``from_dict`` and the JWT-like
  ``to_jws``/``from_jws`` both reconstruct a verifiable proof;
* key resolution is fail-closed in production.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from sardis.core.authority_proof import (
    AuthorityProof,
    build_authority_proof,
    public_jwk,
    public_key_bytes,
    reduce_delegation_chain,
    resolve_signing_key,
)
from sardis.core.delegation import DelegationScope, DelegatorKind
from sardis.core.delegation_engine import DelegationEngine
from sardis.core.delegation_lookup import DelegationAwareMandateLookup
from sardis.core.delegation_repository import InMemoryDelegationStore
from sardis.core.orchestrator import PaymentOrchestrator
from sardis.core.spending_mandate import SpendingMandate

# A deterministic 32-byte Ed25519 seed for the tests (NEVER a prod key).
SEED = hashlib.sha256(b"test-authority-proof-seed").digest()
PRIV = Ed25519PrivateKey.from_private_bytes(SEED)
PUB = public_key_bytes(PRIV)


# ── 1) unit: build + offline verify ─────────────────────────────────────


def test_build_proof_is_allowed_and_verifies_with_published_key():
    proof = build_authority_proof(
        action_id="mandate_42",
        agent="agent_A",
        amount_minor=50_000_000,
        currency="USDC",
        counterparty="openai.com",
        policy_hash="ph_abc",
        mandate_hash="mh_def",
        spending_mandate_id="mst_1",
        amount="50",
        inputs={"rail": "usdc", "chain": "base", "token": "USDC"},
        secret=SEED,
    )
    assert proof.decision == "ALLOWED"
    assert proof.signature
    assert proof.proof_id.startswith("poauth_")
    # Offline verify with ONLY the published public key — no secret, no DB.
    assert proof.verify(PUB) is True
    # And via base64url string form of the key.
    assert proof.verify(public_jwk(private_key=PRIV)["x"]) is True


def test_tampering_any_field_fails_verification():
    base_kwargs = {
        "action_id": "mandate_42",
        "agent": "agent_A",
        "amount_minor": 50_000_000,
        "currency": "USDC",
        "counterparty": "openai.com",
        "policy_hash": "ph_abc",
        "mandate_hash": "mh_def",
        "amount": "50",
        "secret": SEED,
    }
    proof = build_authority_proof(**base_kwargs)
    assert proof.verify(PUB) is True

    # Tamper each bound field in turn -> verification must fail.
    for attr, bad in [
        ("amount_minor", 51_000_000),
        ("amount", "51"),
        ("counterparty", "evil.com"),
        ("agent", "agent_evil"),
        ("policy_hash", "ph_tampered"),
        ("mandate_hash", "mh_tampered"),
        ("currency", "EURC"),
        ("action_id", "mandate_other"),
    ]:
        p = build_authority_proof(**base_kwargs)
        setattr(p, attr, bad)
        assert p.verify(PUB) is False, f"tampering {attr} should fail verification"

    # Tampering the evaluated inputs also breaks it.
    p = build_authority_proof(inputs={"rail": "usdc"}, **base_kwargs)
    p.inputs["rail"] = "card"
    assert p.verify(PUB) is False

    # A flipped decision is never verifiable.
    p = build_authority_proof(**base_kwargs)
    p.decision = "DENIED"
    assert p.verify(PUB) is False


def test_wrong_key_fails_verification():
    proof = build_authority_proof(
        action_id="m", agent="a", amount_minor=1, currency="USDC",
        counterparty="c", secret=SEED,
    )
    assert proof.verify(PUB) is True
    other_pub = public_key_bytes(Ed25519PrivateKey.from_private_bytes(
        hashlib.sha256(b"a-totally-different-key").digest()
    ))
    assert proof.verify(other_pub) is False


def test_export_roundtrips_dict_and_jws():
    proof = build_authority_proof(
        action_id="mandate_42", agent="agent_A", amount_minor=50_000_000,
        currency="USDC", counterparty="openai.com", policy_hash="ph",
        mandate_hash="mh", amount="50", inputs={"rail": "usdc"}, secret=SEED,
    )
    # dict round-trip
    revived = AuthorityProof.from_dict(proof.to_dict())
    assert revived.verify(PUB) is True
    assert revived.signature == proof.signature

    # JWT-like detached round-trip: <payload_b64url>.<sig_b64url>
    token = proof.to_jws()
    assert token.count(".") == 1
    from_token = AuthorityProof.from_jws(token)
    assert from_token.verify(PUB) is True
    assert from_token.action_id == "mandate_42"

    # A flipped signature in the JWS envelope breaks verification.
    payload, sig = token.split(".", 1)
    bad_sig = sig[:-2] + ("AA" if sig[-2:] != "AA" else "BB")
    tampered = AuthorityProof.from_jws(f"{payload}.{bad_sig}")
    assert tampered.verify(PUB) is False


def test_production_requires_explicit_signing_key(monkeypatch):
    monkeypatch.delenv("SARDIS_AUTHORITY_PROOF_PRIVATE_KEY", raising=False)
    monkeypatch.setenv("SARDIS_ENVIRONMENT", "production")
    with pytest.raises(RuntimeError, match="SARDIS_AUTHORITY_PROOF_PRIVATE_KEY"):
        resolve_signing_key()
    # With the key set, it resolves fine.
    monkeypatch.setenv("SARDIS_AUTHORITY_PROOF_PRIVATE_KEY", SEED.hex())
    assert isinstance(resolve_signing_key(), Ed25519PrivateKey)


# ── delegation-chain binding (unit) ─────────────────────────────────────


def test_delegated_proof_binds_chain_and_tamper_breaks_it():
    chain_facts = [
        {"kind": "mandate", "ref": "mandate_root", "depth": 0,
         "amount_cap": "500", "currency": "USDC", "scope_hash": "rootsh"},
        {"kind": "delegation", "ref": "dlg_b", "depth": 1,
         "amount_cap": "50", "currency": "USDC", "scope_hash": "bsh"},
        {"kind": "delegation", "ref": "dlg_c", "depth": 2,
         "amount_cap": "20", "currency": "USDC", "scope_hash": "csh"},
    ]
    proof = AuthorityProof(
        proof_id="poauth_x", action_id="m", agent="tool_C", amount_minor=10_000_000,
        amount="10", currency="USDC", counterparty="openai.com", policy_hash="ph",
        mandate_hash="mh", spending_mandate_id="mandate_root",
        issued_at=datetime.now(UTC), inputs={}, delegation_chain=chain_facts,
    ).sign(SEED)
    assert proof.verify(PUB) is True
    assert len(proof.delegation_chain) == 3

    # Widen a delegated cap -> signature breaks (you cannot lie about authority).
    widened = AuthorityProof.from_dict(proof.to_dict())
    widened.delegation_chain[2]["amount_cap"] = "9999"
    assert widened.verify(PUB) is False

    # Truncate the chain -> breaks.
    truncated = AuthorityProof.from_dict(proof.to_dict())
    truncated.delegation_chain = truncated.delegation_chain[:2]
    assert truncated.verify(PUB) is False


# ── orchestrator integration: emitted on ALLOWED execution ──────────────


@dataclass
class _FakePayment:
    mandate_id: str = "exec_001"
    agent_id: str | None = "tool_C"
    wallet_id: str | None = None
    chain: str = "base"
    token: str = "USDC"
    amount_minor: int = 10_000_000  # 10 USDC
    destination: str = "openai.com"
    audit_hash: str = "0x" + "00" * 32
    merchant_id: str | None = "openai.com"
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

    async def record_spend(self, mandate_id, amount):
        m = self._by_id.get(mandate_id)
        if m is not None:
            m.spent_total = (m.spent_total or Decimal("0")) + Decimal(str(amount))


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
        authority_proof_secret=SEED,
    )
    return orch, chain_exec


@pytest.mark.asyncio
async def test_direct_payment_emits_verifiable_authority_proof():
    root = SpendingMandate(
        principal_id="usr", issuer_id="usr", id="mandate_direct",
        agent_id="agent_A", amount_total=Decimal("500"), amount_per_tx=Decimal("500"),
        currency="USDC", merchant_scope={"allowed": ["openai.com"]},
        allowed_rails=["usdc"], expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    base = _InMemoryBaseLookup({root.id: root})
    orch, chain_exec = _orchestrator(base)

    result = await orch.execute_chain(
        _FakeMandateChain(payment=_FakePayment(mandate_id="exec_direct", agent_id="agent_A"))
    )
    assert result.status == "submitted"
    proof = result.authority_proof
    assert proof is not None
    assert proof.decision == "ALLOWED"
    assert proof.agent == "agent_A"
    assert proof.counterparty == "openai.com"
    assert proof.spending_mandate_id == "mandate_direct"
    assert proof.delegation_chain == []  # direct payment
    # Anyone with the PUBLISHED key verifies offline.
    assert proof.verify(PUB) is True
    # Tampering after the fact fails.
    proof.amount_minor = 999
    assert proof.verify(PUB) is False


@pytest.mark.asyncio
async def test_delegated_payment_emits_proof_with_chain_and_verifies():
    root = SpendingMandate(
        principal_id="usr", issuer_id="usr", id="mandate_root_A",
        agent_id="agent_A", amount_total=Decimal("500"), amount_per_tx=Decimal("500"),
        currency="USDC", merchant_scope={"allowed": ["openai.com"]},
        allowed_rails=["usdc"], expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    dstore = InMemoryDelegationStore()
    mandates = {root.id: root}

    async def resolver(mid):
        return mandates.get(mid)

    eng = DelegationEngine(store=dstore, mandate_resolver=resolver, signing_secret="dsec")
    b = await eng.delegate(
        delegator_ref=root.id, delegator_kind=DelegatorKind.MANDATE,
        delegatee="agent_B", delegator_principal="agent_A", amount_cap=Decimal("50"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )
    c = await eng.delegate(
        delegator_ref=b.id, delegator_kind=DelegatorKind.DELEGATION,
        delegatee="tool_C", delegator_principal="agent_B", amount_cap=Decimal("20"),
        scope=DelegationScope(counterparties=["openai.com"], rails=["usdc"]),
    )
    base = _InMemoryBaseLookup(mandates)
    lookup = DelegationAwareMandateLookup(base=base, engine=eng)
    orch, chain_exec = _orchestrator(lookup)

    # tool_C (leaf delegatee) pays 10 USDC through the chain.
    result = await orch.execute_chain(
        _FakeMandateChain(payment=_FakePayment(mandate_id="exec_dlg", agent_id="tool_C"))
    )
    assert result.status == "submitted"
    proof = result.authority_proof
    assert proof is not None

    # The proof binds the WHOLE attenuated chain: root mandate + B + C.
    refs = [hop["ref"] for hop in proof.delegation_chain]
    assert refs == [root.id, b.id, c.id]
    kinds = [hop["kind"] for hop in proof.delegation_chain]
    assert kinds == ["mandate", "delegation", "delegation"]
    # The acting agent is bound as the leaf delegatee.
    assert proof.agent == "tool_C"
    assert proof.delegation_chain[1]["amount_cap"] == "50"
    assert proof.delegation_chain[2]["amount_cap"] == "20"

    # Offline verification with the published key succeeds.
    assert proof.verify(PUB) is True
    # And it survives JWS export + reconstruction.
    assert AuthorityProof.from_jws(proof.to_jws()).verify(PUB) is True

    # Widening any hop in the exported proof breaks verification (cannot forge
    # a larger delegated authority than what Sardis signed).
    forged = AuthorityProof.from_dict(proof.to_dict())
    forged.delegation_chain[2]["amount_cap"] = "1000"
    assert forged.verify(PUB) is False


def test_reduce_delegation_chain_handles_empty():
    assert reduce_delegation_chain(None) == []
    assert reduce_delegation_chain([]) == []

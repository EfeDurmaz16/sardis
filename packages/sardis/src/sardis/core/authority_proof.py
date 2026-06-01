"""AuthorityProof — Portable, offline-verifiable Proof-of-Authority.

This is the second authority primitive: a **signed, self-contained credential**
proving that a specific action *was authorized* by Sardis.  It is emitted on
every ALLOWED execution alongside the existing
:class:`~sardis.core.execution_receipt.ExecutionReceipt`.

The whole point is **offline, trustless verification**: a merchant, an auditor,
or a regulator can take an exported proof and a *published public key* and
confirm — without calling Sardis, without a DB, without any live system — that

    "this agent was authorized for this exact action, under this policy and
     mandate, through this (attenuated) delegation chain, at this time."

Signing scheme — asymmetric (Ed25519), NOT HMAC
-------------------------------------------------
The sibling proofs (:class:`~sardis.core.approval_request.DecisionEvidence`,
:class:`~sardis.core.revocation.RevocationProof`,
:class:`~sardis.core.delegation.DelegationEvidence`,
:class:`~sardis.core.execution_receipt.ExecutionReceipt`) use HMAC-SHA256.  HMAC
is a *symmetric* MAC: verifying it requires the **same secret** that signed it.
That is fine for Sardis-internal tamper-evidence, but it is fundamentally
unsuitable for a portable credential — handing a merchant the HMAC key would let
that merchant *forge* proofs, and a regulator must never need a Sardis secret to
verify authorization.

So AuthorityProof signs with **Ed25519** (the repo already ships an Ed25519
sign/verify path in :mod:`sardis.core.attestation_envelope` and the TAP JWKS
verifier in :mod:`sardis.protocol.tap_keys`).  Sardis signs with a *private*
key; anyone verifies with the *published* public key.  The public key is safe to
publish (JWKS, `.well-known`, docs) — possessing it grants verification, never
forgery.

What it binds
-------------
The signed payload is the canonical JSON of an immutable claim covering:

* ``action_id`` — the per-execution payment / action identifier;
* ``agent`` — the acting agent (the delegatee when delegated, else the agent
  that holds the mandate);
* ``amount_minor`` + ``currency`` — money in **minor units** (integer, never
  float), plus the human ``amount`` token-unit string for display;
* ``counterparty`` — the merchant id / destination;
* ``policy_hash`` — the SpendingPolicy snapshot in force at evaluation;
* ``mandate_hash`` — the governing SpendingMandate snapshot;
* ``decision`` — always ``"ALLOWED"`` (a proof is only emitted on authorization);
* ``issued_at`` — RFC3339 timestamp;
* ``inputs`` — the exact evaluated inputs (rail, chain, token, category, mcc,
  spending_mandate_id, …) so the verifier sees *what* was authorized;
* ``delegation_chain`` — when the action ran under attenuated delegation, the
  ordered chain (root mandate first, leaf delegation last) reduced to its
  authority-bearing facts per hop (kind / ref / depth / amount_cap / scope_hash).
  Binding the chain means a tampered, widened, or truncated chain invalidates the
  signature — the proof testifies to the *exact* capability path that authorized
  the spend.

The ``content_hash`` (SHA-256 of the canonical claim) is carried for convenience,
but verification does NOT trust it: :meth:`verify` *recomputes* it from the bound
fields and checks the Ed25519 signature over the canonical claim.  Tampering with
any bound field — including any delegation hop — breaks verification.

Exportable
----------
:meth:`to_jws` / :meth:`from_jws` give a compact, JWT-like detached
``<payload_b64url>.<signature_b64url>`` envelope a merchant can paste into a
verifier.  :meth:`to_dict` / :meth:`from_dict` give the structured JSON form.

No vendor SDK; money is integer minor units / :class:`~decimal.Decimal`.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

# ── Identifiers ────────────────────────────────────────────────────────


def _to_base36(num: int) -> str:
    chars = "0123456789abcdefghijklmnopqrstuvwxyz"
    if num == 0:
        return "0"
    out: list[str] = []
    while num:
        num, rem = divmod(num, 36)
        out.append(chars[rem])
    return "".join(reversed(out))


def new_proof_id() -> str:
    """``poauth_<base36 ts>_<rand>`` — the Proof-of-Authority identifier."""
    import secrets

    ts = _to_base36(int(time.time()))
    return f"poauth_{ts}_{secrets.token_hex(4)}"


# ── base64url (no padding), JWS-style ──────────────────────────────────


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * ((4 - len(value) % 4) % 4)
    return base64.urlsafe_b64decode(value + pad)


# ── Signing-key resolution (asymmetric; fail-closed in production) ─────


def _decode_seed(raw: str) -> bytes:
    """Decode a 32-byte Ed25519 private seed from hex or base64(url)."""
    raw = raw.strip()
    # hex (64 chars)
    try:
        if len(raw) == 64:
            return bytes.fromhex(raw)
    except ValueError:
        pass
    # base64 / base64url
    try:
        seed = _b64url_decode(raw)
        if len(seed) == 32:
            return seed
    except Exception:
        pass
    try:
        seed = base64.b64decode(raw)
        if len(seed) == 32:
            return seed
    except Exception:
        pass
    raise RuntimeError(
        "SARDIS_AUTHORITY_PROOF_PRIVATE_KEY must be a 32-byte Ed25519 seed "
        "encoded as hex (64 chars) or base64/base64url."
    )


def _dev_seed() -> bytes:
    """Deterministic dev-only seed.  NEVER reachable in production/staging —
    :func:`resolve_signing_key` fails closed there before this is used."""
    return hashlib.sha256(b"dev-authority-proof-key").digest()


def resolve_signing_key(secret: bytes | str | None = None) -> Ed25519PrivateKey:
    """Resolve the Ed25519 *private* key used to sign authority proofs.

    Mirrors the fail-closed key resolution of the HMAC proofs: an explicit
    secret wins; otherwise ``SARDIS_AUTHORITY_PROOF_PRIVATE_KEY``; otherwise a
    deterministic ``dev`` seed — but ONLY outside production/staging, where a
    missing key fails closed (refuses to sign an authorization credential).
    """
    if isinstance(secret, Ed25519PrivateKey):  # pragma: no cover - convenience
        return secret
    if isinstance(secret, (bytes, bytearray)):
        return Ed25519PrivateKey.from_private_bytes(bytes(secret))
    if isinstance(secret, str) and secret:
        return Ed25519PrivateKey.from_private_bytes(_decode_seed(secret))

    env_seed = os.getenv("SARDIS_AUTHORITY_PROOF_PRIVATE_KEY", "").strip()
    if env_seed:
        return Ed25519PrivateKey.from_private_bytes(_decode_seed(env_seed))

    env = os.getenv("SARDIS_ENVIRONMENT", os.getenv("SARDIS_ENV", "dev")).strip().lower()
    if env in ("prod", "production", "staging"):
        raise RuntimeError(
            "SARDIS_AUTHORITY_PROOF_PRIVATE_KEY must be set in production/staging. "
            "Refusing to sign a portable Proof-of-Authority with a default key."
        )
    return Ed25519PrivateKey.from_private_bytes(_dev_seed())


def public_key_bytes(private_key: Ed25519PrivateKey | None = None) -> bytes:
    """The raw 32-byte Ed25519 *public* key to PUBLISH for offline verifiers."""
    from cryptography.hazmat.primitives import serialization

    pk = (private_key or resolve_signing_key()).public_key()
    return pk.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )


def public_key_b64url(private_key: Ed25519PrivateKey | None = None) -> str:
    """The published public key as base64url — drop-in for a JWK ``x`` value."""
    return _b64url_encode(public_key_bytes(private_key))


def public_jwk(kid: str = "sardis-authority-proof", private_key: Ed25519PrivateKey | None = None) -> dict[str, Any]:
    """The published verification key as a JWK (kty=OKP, crv=Ed25519).

    Compatible with :func:`sardis.protocol.tap_keys.verify_signature_with_jwk`.
    """
    return {
        "kty": "OKP",
        "crv": "Ed25519",
        "x": public_key_b64url(private_key),
        "kid": kid,
        "use": "sig",
        "alg": "EdDSA",
    }


# ── Money helpers ──────────────────────────────────────────────────────


def _as_minor(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):  # pragma: no cover - defensive
        raise TypeError("bool is not a valid minor-unit amount")
    if isinstance(value, float):  # pragma: no cover - defensive
        raise TypeError("float amounts are forbidden on authority-proof money paths")
    return int(value)


# ── Delegation-chain binding ───────────────────────────────────────────


def reduce_delegation_chain(chain: list[Any] | None) -> list[dict[str, Any]]:
    """Reduce a resolved delegation chain to its bound authority facts.

    Input is the orchestrator's ``delegation_chain`` (root SpendingMandate first,
    each :class:`~sardis.core.delegation.Delegation` hop after, leaf last).  We
    bind only the immutable, authority-bearing facts of each hop so that any
    tamper — widening a cap, swapping a scope, truncating the chain, reordering —
    invalidates the signature, while keeping the proof self-contained.
    """
    if not chain:
        return []
    out: list[dict[str, Any]] = []
    for link in chain:
        # SpendingMandate root (depth 0).
        if hasattr(link, "remaining_total") and not hasattr(link, "delegatee"):
            cap = getattr(link, "amount_total", None)
            out.append(
                {
                    "kind": "mandate",
                    "ref": getattr(link, "id", ""),
                    "depth": 0,
                    "amount_cap": str(cap) if cap is not None else None,
                    "currency": getattr(link, "currency", ""),
                    "scope_hash": _mandate_scope_hash(link),
                }
            )
            continue
        # Delegation hop.
        cap = getattr(link, "amount_cap", None)
        scope = getattr(link, "scope", None)
        scope_hash = scope.scope_hash() if scope is not None and hasattr(scope, "scope_hash") else ""
        out.append(
            {
                "kind": "delegation",
                "ref": getattr(link, "id", ""),
                "depth": int(getattr(link, "depth", 0)),
                "amount_cap": str(cap) if cap is not None else None,
                "currency": getattr(link, "currency", ""),
                "scope_hash": scope_hash,
            }
        )
    return out


def _mandate_scope_hash(mandate: Any) -> str:
    payload = {
        "merchant_scope": getattr(mandate, "merchant_scope", {}) or {},
        "allowed_rails": sorted(getattr(mandate, "allowed_rails", []) or []),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


# ── The portable proof ─────────────────────────────────────────────────


_ALG = "EdDSA"
_TYP = "sardis-authority-proof+v1"


@dataclass(slots=True)
class AuthorityProof:
    """A signed, self-contained, offline-verifiable proof that an action was
    authorized by Sardis.

    Carries every field needed to recompute the canonical claim and verify the
    Ed25519 signature with a *published* public key — no DB, no live Sardis.
    """

    proof_id: str
    action_id: str
    agent: str
    amount_minor: int
    amount: str  # token (major) units, display-only, also bound
    currency: str
    counterparty: str
    policy_hash: str
    mandate_hash: str
    spending_mandate_id: str
    issued_at: datetime
    inputs: dict[str, Any] = field(default_factory=dict)
    delegation_chain: list[dict[str, Any]] = field(default_factory=list)
    decision: str = "ALLOWED"
    issuer: str = "sardis"
    alg: str = _ALG
    typ: str = _TYP
    content_hash: str = ""
    signature: str = ""  # base64url Ed25519 signature over the canonical claim

    # ----- canonicalization -----

    def _claim(self) -> dict[str, Any]:
        """The exact, immutable claim that is hashed and signed.

        Delegation hops are sorted deterministically by (depth, kind, ref) so the
        binding is independent of insertion quirks but still fixes the exact set
        and each hop's bounds.
        """
        sorted_chain = sorted(
            self.delegation_chain,
            key=lambda h: (int(h.get("depth", 0)), str(h.get("kind", "")), str(h.get("ref", ""))),
        )
        return {
            "typ": self.typ,
            "alg": self.alg,
            "issuer": self.issuer,
            "proof_id": self.proof_id,
            "action_id": self.action_id,
            "agent": self.agent,
            "amount_minor": int(self.amount_minor),
            "amount": self.amount,
            "currency": self.currency,
            "counterparty": self.counterparty,
            "policy_hash": self.policy_hash,
            "mandate_hash": self.mandate_hash,
            "spending_mandate_id": self.spending_mandate_id,
            "decision": self.decision,
            "issued_at": self.issued_at.isoformat(),
            "inputs": _canonical_inputs(self.inputs),
            "delegation_chain": [
                {
                    "kind": h.get("kind", ""),
                    "ref": h.get("ref", ""),
                    "depth": int(h.get("depth", 0)),
                    "amount_cap": h.get("amount_cap"),
                    "currency": h.get("currency", ""),
                    "scope_hash": h.get("scope_hash", ""),
                }
                for h in sorted_chain
            ],
        }

    def _canonical_bytes(self) -> bytes:
        return json.dumps(
            self._claim(), sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str
        ).encode("utf-8")

    def compute_content_hash(self) -> str:
        return hashlib.sha256(self._canonical_bytes()).hexdigest()

    # ----- signing & verification -----

    def sign(self, secret: bytes | str | None = None) -> AuthorityProof:
        """Sign the canonical claim with the Ed25519 private key (in place)."""
        if self.decision != "ALLOWED":
            raise ValueError("AuthorityProof is only emitted for ALLOWED decisions")
        self.content_hash = self.compute_content_hash()
        private_key = resolve_signing_key(secret)
        sig = private_key.sign(self._canonical_bytes())
        self.signature = _b64url_encode(sig)
        return self

    def verify(self, public_key: bytes | str | Ed25519PublicKey) -> bool:
        """Offline-verify with a PUBLISHED public key — no Sardis, no DB.

        Recomputes the canonical claim from the bound fields (so the carried
        ``content_hash`` is never trusted) and checks the Ed25519 signature.
        Returns ``False`` on any mismatch: tampered field, tampered/widened/
        truncated delegation hop, wrong key, missing signature, or a non-ALLOWED
        decision.
        """
        if not self.signature or self.decision != "ALLOWED":
            return False
        # Bind the carried content_hash to the recomputed one (defensive; the
        # signature alone is authoritative, but a mismatch is a clear tamper).
        if self.content_hash and self.content_hash != self.compute_content_hash():
            return False
        pub = _coerce_public_key(public_key)
        try:
            sig = _b64url_decode(self.signature)
            pub.verify(sig, self._canonical_bytes())
            return True
        except Exception:
            return False

    # ----- export / import -----

    def to_dict(self) -> dict[str, Any]:
        d = dict(self._claim())
        d["content_hash"] = self.content_hash
        d["signature"] = self.signature
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> AuthorityProof:
        return cls(
            proof_id=d["proof_id"],
            action_id=d["action_id"],
            agent=d["agent"],
            amount_minor=int(d.get("amount_minor", 0)),
            amount=d.get("amount", ""),
            currency=d.get("currency", ""),
            counterparty=d.get("counterparty", ""),
            policy_hash=d.get("policy_hash", ""),
            mandate_hash=d.get("mandate_hash", ""),
            spending_mandate_id=d.get("spending_mandate_id", ""),
            issued_at=datetime.fromisoformat(d["issued_at"]),
            inputs=dict(d.get("inputs", {})),
            delegation_chain=list(d.get("delegation_chain", [])),
            decision=d.get("decision", "ALLOWED"),
            issuer=d.get("issuer", "sardis"),
            alg=d.get("alg", _ALG),
            typ=d.get("typ", _TYP),
            content_hash=d.get("content_hash", ""),
            signature=d.get("signature", ""),
        )

    def to_jws(self) -> str:
        """Compact JWT-like envelope: ``<payload_b64url>.<signature_b64url>``.

        The payload is the canonical claim (the exact bytes that were signed), so
        a verifier reconstructs and checks it deterministically.
        """
        if not self.signature:
            raise ValueError("proof is unsigned; call sign() first")
        payload = _b64url_encode(self._canonical_bytes())
        return f"{payload}.{self.signature}"

    @classmethod
    def from_jws(cls, token: str) -> AuthorityProof:
        try:
            payload_b64, signature = token.split(".", 1)
        except ValueError as exc:
            raise ValueError("malformed authority-proof token") from exc
        claim = json.loads(_b64url_decode(payload_b64))
        claim["signature"] = signature
        proof = cls.from_dict(claim)
        proof.content_hash = proof.compute_content_hash()
        return proof


def _canonical_inputs(inputs: dict[str, Any] | None) -> dict[str, Any]:
    """Stable, JSON-safe view of the evaluated inputs (no floats, sorted)."""
    if not inputs:
        return {}
    out: dict[str, Any] = {}
    for k in sorted(inputs):
        v = inputs[k]
        if isinstance(v, float):  # pragma: no cover - defensive
            raise TypeError(f"float input {k!r} forbidden on authority-proof path")
        if isinstance(v, Decimal):
            v = str(v)
        out[str(k)] = v
    return out


def _coerce_public_key(public_key: bytes | str | Ed25519PublicKey) -> Ed25519PublicKey:
    if isinstance(public_key, Ed25519PublicKey):
        return public_key
    if isinstance(public_key, (bytes, bytearray)):
        return Ed25519PublicKey.from_public_bytes(bytes(public_key))
    # str: try base64url, then hex
    try:
        return Ed25519PublicKey.from_public_bytes(_b64url_decode(public_key))
    except Exception:
        return Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key))


def build_authority_proof(
    *,
    action_id: str,
    agent: str,
    amount_minor: Any,
    currency: str,
    counterparty: str,
    policy_hash: str = "",
    mandate_hash: str = "",
    spending_mandate_id: str = "",
    amount: str | Decimal | None = None,
    inputs: dict[str, Any] | None = None,
    delegation_chain: list[Any] | None = None,
    issued_at: datetime | None = None,
    secret: bytes | str | None = None,
) -> AuthorityProof:
    """Build + sign a portable Proof-of-Authority for an ALLOWED execution.

    ``delegation_chain`` is the orchestrator's resolved chain (root mandate
    first, leaf delegation last); it is reduced to its bound authority facts via
    :func:`reduce_delegation_chain`.  Direct (non-delegated) payments pass an
    empty / ``None`` chain.
    """
    minor = _as_minor(amount_minor)
    proof = AuthorityProof(
        proof_id=new_proof_id(),
        action_id=action_id,
        agent=agent,
        amount_minor=minor,
        amount=str(amount) if amount is not None else str(minor),
        currency=currency,
        counterparty=counterparty,
        policy_hash=policy_hash,
        mandate_hash=mandate_hash,
        spending_mandate_id=spending_mandate_id,
        issued_at=issued_at or datetime.now(UTC),
        inputs=inputs or {},
        delegation_chain=reduce_delegation_chain(delegation_chain),
        decision="ALLOWED",
    )
    return proof.sign(secret)


__all__ = [
    "AuthorityProof",
    "build_authority_proof",
    "new_proof_id",
    "public_jwk",
    "public_key_b64url",
    "public_key_bytes",
    "reduce_delegation_chain",
    "resolve_signing_key",
]

"""Signed attestation envelope for policy decisions.

An AttestationEnvelope bundles the full proof of *why* a payment was allowed
(or denied): which policy rules fired, what evidence was collected, and
optionally an Ed25519 signature that makes the bundle tamper-evident.

This is the consumable API surface on top of the lower-level
``policy_attestation`` building blocks (merkle roots, canonical hashing).

Usage::

    envelope = build_attestation_envelope(
        mandate_id="mnd_abc123",
        agent_did="did:sardis:agent_42",
        policy_rules=["per_tx_limit", "scope_check", "merchant_allow"],
        evidence=["policy_hash:ab12…", "decision_hash:cd34…"],
        verification_report={
            "mandate_chain_valid": True,
            "policy_compliance": "pass",
            "kya_score": 0.85,
            "provenance": "turnkey_mpc",
        },
    )
"""

from __future__ import annotations

import base64
import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(slots=True)
class AttestationEnvelope:
    """Signed attestation envelope with policy evidence and verification report."""

    attestation_id: str
    timestamp: str  # ISO 8601
    agent_did: str
    mandate_id: str
    policy_rules_applied: list[str]
    evidence_chain: list[str]
    ap2_mandate_ref: str = ""
    verification_report: dict[str, Any] = field(default_factory=dict)
    signature: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attestation_id": self.attestation_id,
            "timestamp": self.timestamp,
            "agent_did": self.agent_did,
            "mandate_id": self.mandate_id,
            "policy_rules_applied": self.policy_rules_applied,
            "evidence_chain": self.evidence_chain,
            "ap2_mandate_ref": self.ap2_mandate_ref,
            "verification_report": self.verification_report,
            "signature": self.signature,
        }


def _canonical_json(envelope: AttestationEnvelope) -> str:
    """Produce a deterministic JSON representation for signing.

    Excludes the ``signature`` field so the payload is stable before and
    after signing.
    """
    payload = {
        "attestation_id": envelope.attestation_id,
        "timestamp": envelope.timestamp,
        "agent_did": envelope.agent_did,
        "mandate_id": envelope.mandate_id,
        "policy_rules_applied": envelope.policy_rules_applied,
        "evidence_chain": envelope.evidence_chain,
        "ap2_mandate_ref": envelope.ap2_mandate_ref,
        "verification_report": envelope.verification_report,
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def build_attestation_envelope(
    mandate_id: str,
    agent_did: str,
    policy_rules: list[str],
    evidence: list[str],
    verification_report: dict[str, Any] | None = None,
    signing_key: bytes | None = None,
) -> AttestationEnvelope:
    """Build and optionally sign an attestation envelope.

    Parameters
    ----------
    mandate_id:
        The mandate / payment ID this attestation covers.
    agent_did:
        The DID of the agent whose payment was evaluated.
    policy_rules:
        List of rule identifiers that were applied during evaluation.
    evidence:
        Evidence chain entries (hashes, anchors, etc.).
    verification_report:
        Optional dict with verification metadata (mandate chain validity,
        policy compliance, KYA score, provenance).
    signing_key:
        32-byte Ed25519 private key seed.  When provided the canonical JSON
        payload is signed and the base64-encoded signature is stored in the
        ``signature`` field.  When ``None`` the envelope is returned unsigned.

    Returns
    -------
    AttestationEnvelope
    """
    envelope = AttestationEnvelope(
        attestation_id=f"att_{uuid.uuid4().hex[:16]}",
        timestamp=datetime.now(UTC).isoformat(),
        agent_did=agent_did,
        mandate_id=mandate_id,
        policy_rules_applied=list(policy_rules),
        evidence_chain=list(evidence),
        verification_report=verification_report or {},
    )

    if signing_key is not None:
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.from_private_bytes(signing_key)
        message = _canonical_json(envelope).encode("utf-8")
        sig_bytes = private_key.sign(message)
        envelope.signature = base64.b64encode(sig_bytes).decode("ascii")

    return envelope


def verify_attestation_signature(
    envelope: AttestationEnvelope,
    public_key_bytes: bytes,
) -> bool:
    """Verify the Ed25519 signature on an attestation envelope.

    Returns ``True`` when the signature is valid, ``False`` otherwise
    (including when the envelope has no signature).
    """
    if not envelope.signature:
        return False

    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

    try:
        pub = Ed25519PublicKey.from_public_bytes(public_key_bytes)
        sig_bytes = base64.b64decode(envelope.signature)
        message = _canonical_json(envelope).encode("utf-8")
        pub.verify(sig_bytes, message)
        return True
    except Exception:
        return False

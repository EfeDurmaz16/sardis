"""TAP-style agent identity helpers."""
from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from typing import Dict, Literal, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from nacl import encoding, signing

AllowedKeys = Literal["ed25519", "ecdsa-p256"]


@dataclass(slots=True)
class AgentIdentity:
    agent_id: str
    public_key: bytes
    algorithm: AllowedKeys = "ed25519"
    domain: str = "sardis.network"
    created_at: int = int(time.time())

    def verify(self, message: bytes, signature: bytes, domain: str, nonce: str, purpose: str) -> bool:
        """Verify TAP request binding with nonce + purpose scoping."""
        if domain != self.domain:
            return False
        payload = b"|".join([domain.encode(), nonce.encode(), purpose.encode(), message])
        if self.algorithm == "ed25519":
            verify_key = signing.VerifyKey(self.public_key)
            target = payload
            try:
                verify_key.verify(target, signature)
            except Exception:  # noqa: BLE001
                return False
            return True
        if self.algorithm == "ecdsa-p256":
            try:
                pub_key = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), self.public_key)
                pub_key.verify(signature, payload, ec.ECDSA(hashes.SHA256()))
            except InvalidSignature:
                return False
            except ValueError:
                return False
            return True
        raise NotImplementedError(f"algorithm {self.algorithm} not supported")

    @staticmethod
    def generate(seed: bytes | None = None) -> tuple["AgentIdentity", bytes]:
        """Generate a new signing key pair (temporary helper for sandbox)."""
        signer = signing.SigningKey(seed) if seed else signing.SigningKey.generate()
        identity = AgentIdentity(
            agent_id=signer.verify_key.encode(encoder=encoding.HexEncoder).decode(),
            public_key=signer.verify_key.encode(),
        )
        return identity, signer.encode()


@dataclass(slots=True)
class IdentityRecord:
    """Registered TAP identity with domain binding and rotation metadata."""

    agent_id: str
    public_key: bytes
    domain: str
    algorithm: AllowedKeys = "ed25519"
    created_at: int = field(default_factory=lambda: int(time.time()))
    version: int = 1
    revoked_at: Optional[int] = None
    reason: Optional[str] = None

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_key).hexdigest()

    @property
    def verification_method(self) -> str:
        """AP2/TAP-friendly verification method fragment."""
        return f"{self.algorithm}:{self.public_key.hex()}"

    def is_active(self, domain: str) -> bool:
        return self.revoked_at is None and self.domain == domain


class IdentityRegistry:
    """
    Lightweight in-memory identity registry for TAP issuance/rotation/revocation.
    Enough for MVP; swap with persistent store later.
    """

    def __init__(self):
        self._records: Dict[str, IdentityRecord] = {}
        self._history: Dict[str, list[IdentityRecord]] = {}

    def issue(self, agent_id: str, public_key: bytes, domain: str, algorithm: AllowedKeys = "ed25519") -> IdentityRecord:
        """Issue or rotate an identity. If an active identity exists, mark it revoked."""
        previous = self._records.get(agent_id)
        version = (previous.version + 1) if previous else 1
        if previous:
            self._archive(previous, reason="rotated")
        record = IdentityRecord(
            agent_id=agent_id,
            public_key=public_key,
            domain=domain,
            algorithm=algorithm,
            version=version,
        )
        self._records[agent_id] = record
        return record

    def revoke(self, agent_id: str, reason: str = "revoked") -> Optional[IdentityRecord]:
        record = self._records.get(agent_id)
        if not record:
            return None
        record.revoked_at = int(time.time())
        record.reason = reason
        self._archive(record, reason=reason)
        self._records.pop(agent_id, None)
        return record

    def _archive(self, record: IdentityRecord, reason: str) -> None:
        record.revoked_at = record.revoked_at or int(time.time())
        record.reason = reason
        self._history.setdefault(record.agent_id, []).append(record)

    def get(self, agent_id: str) -> Optional[IdentityRecord]:
        return self._records.get(agent_id)

    def verify_binding(self, agent_id: str, domain: str, public_key: bytes, algorithm: AllowedKeys) -> bool:
        """Check that the presented key matches the active registry entry."""
        record = self._records.get(agent_id)
        if not record:
            return False
        return record.is_active(domain) and record.public_key == public_key and record.algorithm == algorithm

    @staticmethod
    def parse_verification_method(verification_method: str) -> Tuple[AllowedKeys, bytes]:
        """
        Parse verification method fragment of form 'ed25519:<hex>' or 'ecdsa-p256:<hex>'.
        Raises ValueError on bad input.
        """
        if "#" in verification_method:
            _, fragment = verification_method.split("#", 1)
        else:
            fragment = verification_method
        algorithm, key_material = fragment.split(":", 1)
        if algorithm not in {"ed25519", "ecdsa-p256"}:
            raise ValueError("unsupported_algorithm")
        try:
            public_key = bytes.fromhex(key_material)
        except ValueError as exc:
            raise ValueError("invalid_public_key_hex") from exc
        return ("ecdsa-p256" if algorithm == "ecdsa-p256" else "ed25519", public_key)

    def verify_tap_identity(self, verification_method: str, domain: str) -> tuple[bool, Optional[IdentityRecord], Optional[str]]:
        """
        Validate that a verification_method corresponds to an active registry entry for the domain.
        Returns (valid, record, reason_if_invalid)
        """
        try:
            algorithm, public_key = self.parse_verification_method(verification_method)
        except ValueError as exc:
            return False, None, str(exc)
        for agent_id, record in self._records.items():
            if (
                record.is_active(domain)
                and record.algorithm == algorithm
                and record.public_key == public_key
            ):
                return True, record, None
        return False, None, "identity_not_found_or_revoked"

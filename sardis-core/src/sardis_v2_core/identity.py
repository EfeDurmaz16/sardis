"""TAP-style agent identity helpers."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal

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

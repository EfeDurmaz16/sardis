"""DID Bridge — bidirectional did:sardis <-> did:fides mapping.

Provides registration, resolution, and Ed25519 ownership verification
for linking Sardis agent identities to FIDES decentralized identifiers.

FIDES DID format: did:fides:<base58-encoded-ed25519-public-key>
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime

from .fides_did import parse_did

logger = logging.getLogger("sardis.core.did_bridge")


@dataclass(frozen=True)
class DIDMapping:
    """A verified mapping between a Sardis agent and a FIDES DID."""
    agent_id: str
    fides_did: str
    public_key_hex: str | None = None
    verified_at: datetime | None = None
    verification_signature: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class DIDRegistrationError(Exception):
    """Raised when DID registration fails."""


class DIDBridge:
    """Manages bidirectional did:sardis <-> did:fides mappings.

    In-memory implementation. For production, swap storage to PostgreSQL
    (did_mappings table from migration 055).
    """

    def __init__(self) -> None:
        self._by_agent: dict[str, DIDMapping] = {}
        self._by_fides: dict[str, DIDMapping] = {}

    def register_fides_did(
        self,
        agent_id: str,
        fides_did: str,
        signature: str,
        public_key: str,
    ) -> DIDMapping:
        """Register a FIDES DID for a Sardis agent after verifying Ed25519 signature.

        Args:
            agent_id: Sardis agent identifier
            fides_did: FIDES DID (did:fides:<base58-pubkey>)
            signature: Hex-encoded Ed25519 signature over agent_id bytes
            public_key: Hex-encoded Ed25519 public key (32 bytes)

        Returns:
            DIDMapping on success

        Raises:
            DIDRegistrationError: if signature verification fails or DID already registered
        """
        if not fides_did.startswith("did:fides:"):
            raise DIDRegistrationError(f"Invalid FIDES DID format: {fides_did}")

        if fides_did in self._by_fides:
            existing = self._by_fides[fides_did]
            if existing.agent_id != agent_id:
                raise DIDRegistrationError(
                    f"FIDES DID {fides_did} already registered to agent {existing.agent_id}"
                )

        if not self.verify_ownership(agent_id, fides_did, signature, public_key):
            raise DIDRegistrationError("Ed25519 signature verification failed")

        mapping = DIDMapping(
            agent_id=agent_id,
            fides_did=fides_did,
            public_key_hex=public_key,
            verified_at=datetime.now(UTC),
            verification_signature=signature,
        )
        previous = self._by_agent.get(agent_id)
        if previous is not None and previous.fides_did != fides_did:
            self._by_fides.pop(previous.fides_did, None)
        self._by_agent[agent_id] = mapping
        self._by_fides[fides_did] = mapping

        logger.info("Registered FIDES DID %s for agent %s", fides_did, agent_id)
        return mapping

    def resolve_to_fides(self, agent_id: str) -> str | None:
        """Get FIDES DID for a Sardis agent. Returns None if not registered."""
        mapping = self._by_agent.get(agent_id)
        return mapping.fides_did if mapping else None

    def resolve_to_sardis(self, fides_did: str) -> str | None:
        """Get Sardis agent ID for a FIDES DID. Returns None if not registered."""
        mapping = self._by_fides.get(fides_did)
        return mapping.agent_id if mapping else None

    def get_mapping(self, agent_id: str) -> DIDMapping | None:
        """Get full DID mapping for an agent."""
        return self._by_agent.get(agent_id)

    @staticmethod
    def verify_ownership(
        agent_id: str,
        fides_did: str,
        signature: str,
        public_key: str,
    ) -> bool:
        """Verify that an agent controls a FIDES DID via Ed25519 signature.

        The signature must be over the agent_id bytes, signed with the
        Ed25519 private key corresponding to the public key embedded
        in the FIDES DID.

        Args:
            agent_id: Sardis agent identifier (the signed message)
            fides_did: FIDES DID containing the public key
            signature: Hex-encoded Ed25519 signature
            public_key: Hex-encoded Ed25519 public key

        Returns:
            True if signature is valid
        """
        try:
            from nacl.signing import VerifyKey

            did_public_key = parse_did(fides_did)
            public_key_bytes = bytes.fromhex(public_key)
            if did_public_key != public_key_bytes:
                logger.debug("FIDES DID public key mismatch for agent=%s did=%s", agent_id, fides_did)
                return False
            signature_bytes = bytes.fromhex(signature)
            verify_key = VerifyKey(public_key_bytes)
            verify_key.verify(agent_id.encode(), signature_bytes)
            return True
        except ImportError:
            logger.warning("PyNaCl not installed — cannot verify Ed25519 signatures")
            return False
        except Exception:
            logger.debug(
                "Ed25519 verification failed for agent=%s did=%s",
                agent_id, fides_did,
            )
            return False

"""TAP-style agent identity helpers."""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Literal, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec
from nacl import encoding, signing

from .exceptions import SardisAlgorithmNotSupportedError

_logger = logging.getLogger("sardis.core.identity")

AllowedKeys = Literal["ed25519", "ecdsa-p256"]


@dataclass(slots=True)
class AgentIdentity:
    agent_id: str
    public_key: bytes
    algorithm: AllowedKeys = "ed25519"
    domain: str = "sardis.sh"
    created_at: int = int(time.time())

    @property
    def did(self) -> str:
        """W3C Decentralized Identifier for this agent (did:sardis:<agent_id>)."""
        return f"did:sardis:{self.agent_id}"

    @property
    def did_document_fragment(self) -> Dict:
        """Minimal DID Document fragment for verification."""
        return {
            "id": self.did,
            "verificationMethod": [{
                "id": f"{self.did}#key-1",
                "type": "Ed25519VerificationKey2020" if self.algorithm == "ed25519" else "EcdsaSecp256r1VerificationKey2019",
                "controller": self.did,
                "publicKeyHex": self.public_key.hex(),
            }],
            "authentication": [f"{self.did}#key-1"],
        }

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
        raise SardisAlgorithmNotSupportedError(
                self.algorithm,
                supported=["ed25519", "ecdsa-p256"],
            )

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
    framework_attestation: Optional[str] = None  # e.g. "langchain:0.3.1"

    @property
    def fingerprint(self) -> str:
        return hashlib.sha256(self.public_key).hexdigest()

    @property
    def verification_method(self) -> str:
        """AP2/TAP-friendly verification method fragment."""
        return f"{self.algorithm}:{self.public_key.hex()}"

    @property
    def did(self) -> str:
        """W3C Decentralized Identifier for this agent."""
        return f"did:sardis:{self.agent_id}"

    def is_active(self, domain: str) -> bool:
        return self.revoked_at is None and self.domain == domain


class IdentityRegistry:
    """
    Identity registry for TAP issuance/rotation/revocation.

    Supports optional PostgreSQL persistence. When a dsn is provided,
    identity records are written to the identity_records table. Falls back
    to in-memory storage for dev/test.
    """

    def __init__(self, dsn: Optional[str] = None):
        self._records: Dict[str, IdentityRecord] = {}
        self._history: Dict[str, list[IdentityRecord]] = {}
        self._dsn = dsn
        self._pool = None

        env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
        if env not in ("dev", "test", "local") and not dsn:
            _logger.warning(
                "IdentityRegistry is using IN-MEMORY storage in '%s' environment. "
                "All identity bindings will be LOST on restart. "
                "Pass dsn= for PostgreSQL persistence.",
                env,
            )

    async def _get_pool(self):
        if self._pool is None:
            import asyncpg
            dsn = self._dsn
            if dsn and dsn.startswith("postgres://"):
                dsn = dsn.replace("postgres://", "postgresql://", 1)
            self._pool = await asyncpg.create_pool(dsn, min_size=1, max_size=3)
        return self._pool

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

    async def issue_async(self, agent_id: str, public_key: bytes, domain: str, algorithm: AllowedKeys = "ed25519") -> IdentityRecord:
        """Issue or rotate with DB persistence."""
        record = self.issue(agent_id, public_key, domain, algorithm)
        if self._dsn:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    async with conn.transaction():
                        # Revoke previous version in DB
                        if record.version > 1:
                            await conn.execute(
                                """
                                UPDATE identity_records SET revoked_at = NOW()
                                WHERE agent_id = $1 AND revoked_at IS NULL
                                """,
                                agent_id,
                            )
                        # Insert new record
                        await conn.execute(
                            """
                            INSERT INTO identity_records (agent_id, public_key, algorithm, domain, version)
                            VALUES ($1, $2, $3, $4, $5)
                            ON CONFLICT (agent_id, version) DO NOTHING
                            """,
                            agent_id,
                            public_key.hex(),
                            algorithm,
                            domain,
                            record.version,
                        )
            except Exception as e:
                _logger.warning(f"Failed to persist identity record: {e}")
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

    async def revoke_async(self, agent_id: str, reason: str = "revoked") -> Optional[IdentityRecord]:
        """Revoke with DB persistence."""
        record = self.revoke(agent_id, reason)
        if record and self._dsn:
            try:
                pool = await self._get_pool()
                async with pool.acquire() as conn:
                    await conn.execute(
                        "UPDATE identity_records SET revoked_at = NOW() WHERE agent_id = $1 AND revoked_at IS NULL",
                        agent_id,
                    )
            except Exception as e:
                _logger.warning(f"Failed to persist identity revocation: {e}")
        return record

    def _archive(self, record: IdentityRecord, reason: str) -> None:
        record.revoked_at = record.revoked_at or int(time.time())
        record.reason = reason
        self._history.setdefault(record.agent_id, []).append(record)

    def get(self, agent_id: str) -> Optional[IdentityRecord]:
        return self._records.get(agent_id)

    async def get_async(self, agent_id: str) -> Optional[IdentityRecord]:
        """Get identity, falling back to DB if not in memory."""
        record = self._records.get(agent_id)
        if record:
            return record
        if not self._dsn:
            return None
        try:
            pool = await self._get_pool()
            async with pool.acquire() as conn:
                row = await conn.fetchrow(
                    """
                    SELECT agent_id, public_key, algorithm, domain, version, created_at
                    FROM identity_records
                    WHERE agent_id = $1 AND revoked_at IS NULL
                    ORDER BY version DESC LIMIT 1
                    """,
                    agent_id,
                )
                if row:
                    record = IdentityRecord(
                        agent_id=row["agent_id"],
                        public_key=bytes.fromhex(row["public_key"]),
                        algorithm=row["algorithm"],
                        domain=row["domain"],
                        version=row["version"],
                        created_at=int(row["created_at"].timestamp()) if row["created_at"] else int(time.time()),
                    )
                    self._records[agent_id] = record
                    return record
        except Exception as e:
            _logger.warning(f"Failed to load identity from DB: {e}")
        return None

    def resolve_did(self, did: str) -> Optional[IdentityRecord]:
        """
        Resolve a did:sardis:<agent_id> to its active IdentityRecord.

        Returns None if the DID is invalid or no active record exists.
        """
        if not did.startswith("did:sardis:"):
            return None
        agent_id = did[len("did:sardis:"):]
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

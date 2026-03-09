"""Encrypted credential storage for delegated payment tokens.

Key source: SARDIS_CREDENTIAL_ENCRYPTION_KEY (separate from SARDIS_SECRET_KEY).
Dev fallback: HKDF derivation from SARDIS_SECRET_KEY.
Production: RuntimeError if key not configured.
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import UTC, datetime
from typing import Protocol, runtime_checkable

from .delegated_credential import (
    CREDENTIAL_HANDLING,
    CredentialClass,
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encryption helpers
# ---------------------------------------------------------------------------

class CredentialEncryption:
    """Fernet symmetric encryption for credential tokens.

    Follows pattern from sardis_api.middleware.sso._get_encryption_key().
    """

    def __init__(self, key: bytes | None = None) -> None:
        self._key = key or self._load_key()

    @staticmethod
    def _load_key() -> bytes:
        raw = os.getenv("SARDIS_CREDENTIAL_ENCRYPTION_KEY", "")
        if raw:
            return raw.encode()

        # Dev fallback — derive from SARDIS_SECRET_KEY
        env = os.getenv("SARDIS_ENVIRONMENT", "dev").strip().lower()
        if env in ("prod", "production", "staging"):
            raise RuntimeError(
                "SARDIS_CREDENTIAL_ENCRYPTION_KEY must be set in production/staging. "
                "Generate with: python -c "
                "'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
            )
        secret = os.getenv("SARDIS_SECRET_KEY", "dev-only-secret-key-not-for-production")
        return base64.urlsafe_b64encode(secret[:32].ljust(32, "0").encode())

    def encrypt(self, plaintext: bytes) -> bytes:
        from cryptography.fernet import Fernet
        f = Fernet(self._key)
        return f.encrypt(plaintext)

    def decrypt(self, ciphertext: bytes) -> bytes:
        from cryptography.fernet import Fernet
        f = Fernet(self._key)
        return f.decrypt(ciphertext)

    def encrypt_with_envelope(self, plaintext: bytes) -> bytes:
        """Placeholder for envelope encryption (DEK wrapped by KEK via KMS/HSM).

        Currently double-encrypts with the same Fernet key as a structural
        placeholder.  Production must replace with real envelope encryption
        using a separate DEK per credential, wrapped by a KEK from KMS/HSM.
        """
        inner = self.encrypt(plaintext)
        return self.encrypt(inner)

    def decrypt_with_envelope(self, ciphertext: bytes) -> bytes:
        """Placeholder — see encrypt_with_envelope docstring."""
        outer = self.decrypt(ciphertext)
        return self.decrypt(outer)

    def encrypt_for_class(self, plaintext: bytes, cred_class: CredentialClass) -> bytes:
        handling = CREDENTIAL_HANDLING[cred_class]
        if not handling["encrypt_at_rest"]:
            return plaintext
        if handling["envelope_encrypt"]:
            return self.encrypt_with_envelope(plaintext)
        return self.encrypt(plaintext)

    def decrypt_for_class(self, ciphertext: bytes, cred_class: CredentialClass) -> bytes:
        handling = CREDENTIAL_HANDLING[cred_class]
        if not handling["encrypt_at_rest"]:
            return ciphertext
        if handling["envelope_encrypt"]:
            return self.decrypt_with_envelope(ciphertext)
        return self.decrypt(ciphertext)


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class CredentialStore(Protocol):
    async def store(self, credential: DelegatedCredential) -> str: ...
    async def get(self, credential_id: str) -> DelegatedCredential | None: ...
    async def get_for_agent(self, agent_id: str) -> list[DelegatedCredential]: ...
    async def get_active_for_agent(
        self, agent_id: str, network: CredentialNetwork | None = None,
    ) -> list[DelegatedCredential]: ...
    async def update_status(
        self, credential_id: str, status: CredentialStatus,
    ) -> None: ...
    async def revoke(self, credential_id: str, reason: str) -> None: ...
    async def rotate(
        self, credential_id: str, new_token: bytes,
    ) -> DelegatedCredential: ...
    async def reprovision(
        self,
        credential_id: str,
        new_scope: CredentialScope,
        consent_id: str,
    ) -> DelegatedCredential: ...


# ---------------------------------------------------------------------------
# In-memory implementation (dev / test)
# ---------------------------------------------------------------------------

class InMemoryCredentialStore:
    """In-memory credential store for development and testing."""

    def __init__(self, encryption: CredentialEncryption | None = None) -> None:
        self._creds: dict[str, DelegatedCredential] = {}
        self._encryption = encryption or CredentialEncryption()

    async def store(self, credential: DelegatedCredential) -> str:
        self._creds[credential.credential_id] = credential
        return credential.credential_id

    async def get(self, credential_id: str) -> DelegatedCredential | None:
        return self._creds.get(credential_id)

    async def get_for_agent(self, agent_id: str) -> list[DelegatedCredential]:
        return [c for c in self._creds.values() if c.agent_id == agent_id]

    async def get_active_for_agent(
        self, agent_id: str, network: CredentialNetwork | None = None,
    ) -> list[DelegatedCredential]:
        results = []
        for c in self._creds.values():
            if c.agent_id != agent_id:
                continue
            if c.status != CredentialStatus.ACTIVE:
                continue
            if network and c.network != network:
                continue
            results.append(c)
        return results

    async def update_status(
        self, credential_id: str, status: CredentialStatus,
    ) -> None:
        cred = self._creds.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential {credential_id} not found")
        # We can't use object.__setattr__ on slots easily, so rebuild
        self._creds[credential_id] = DelegatedCredential(
            credential_id=cred.credential_id,
            org_id=cred.org_id,
            agent_id=cred.agent_id,
            network=cred.network,
            status=status,
            credential_class=cred.credential_class,
            token_reference=cred.token_reference,
            token_encrypted=cred.token_encrypted,
            scope=cred.scope,
            provider_metadata=cred.provider_metadata,
            consent_id=cred.consent_id,
            last_used_at=cred.last_used_at,
            created_at=cred.created_at,
            expires_at=cred.expires_at,
        )

    async def revoke(self, credential_id: str, reason: str) -> None:
        cred = self._creds.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential {credential_id} not found")
        self._creds[credential_id] = DelegatedCredential(
            credential_id=cred.credential_id,
            org_id=cred.org_id,
            agent_id=cred.agent_id,
            network=cred.network,
            status=CredentialStatus.REVOKED,
            credential_class=cred.credential_class,
            token_reference=cred.token_reference,
            token_encrypted=cred.token_encrypted,
            scope=cred.scope,
            provider_metadata={**cred.provider_metadata, "revoke_reason": reason},
            consent_id=cred.consent_id,
            last_used_at=cred.last_used_at,
            created_at=cred.created_at,
            expires_at=cred.expires_at,
        )

    async def rotate(
        self, credential_id: str, new_token: bytes,
    ) -> DelegatedCredential:
        """Same authority, new token."""
        cred = self._creds.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential {credential_id} not found")
        encrypted = self._encryption.encrypt_for_class(new_token, cred.credential_class)
        updated = DelegatedCredential(
            credential_id=cred.credential_id,
            org_id=cred.org_id,
            agent_id=cred.agent_id,
            network=cred.network,
            status=cred.status,
            credential_class=cred.credential_class,
            token_reference=cred.token_reference,
            token_encrypted=encrypted,
            scope=cred.scope,
            provider_metadata=cred.provider_metadata,
            consent_id=cred.consent_id,
            last_used_at=cred.last_used_at,
            created_at=cred.created_at,
            expires_at=cred.expires_at,
        )
        self._creds[credential_id] = updated
        return updated

    async def reprovision(
        self,
        credential_id: str,
        new_scope: CredentialScope,
        consent_id: str,
    ) -> DelegatedCredential:
        """New authority grant — requires new consent."""
        cred = self._creds.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential {credential_id} not found")
        updated = DelegatedCredential(
            credential_id=cred.credential_id,
            org_id=cred.org_id,
            agent_id=cred.agent_id,
            network=cred.network,
            status=CredentialStatus.ACTIVE,
            credential_class=cred.credential_class,
            token_reference=cred.token_reference,
            token_encrypted=cred.token_encrypted,
            scope=new_scope,
            provider_metadata=cred.provider_metadata,
            consent_id=consent_id,
            last_used_at=cred.last_used_at,
            created_at=cred.created_at,
            expires_at=new_scope.expires_at,
        )
        self._creds[credential_id] = updated
        return updated


# ---------------------------------------------------------------------------
# PostgreSQL implementation (production)
# ---------------------------------------------------------------------------

class PostgresCredentialStore:
    """Production credential store backed by asyncpg."""

    def __init__(self, pool, encryption: CredentialEncryption | None = None) -> None:
        self._pool = pool
        self._encryption = encryption or CredentialEncryption()

    def _row_to_credential(self, row: dict) -> DelegatedCredential:
        scope_data = row.get("scope_json") or {}
        if isinstance(scope_data, str):
            import json
            scope_data = json.loads(scope_data)
        provider_meta = row.get("provider_metadata") or {}
        if isinstance(provider_meta, str):
            import json
            provider_meta = json.loads(provider_meta)

        return DelegatedCredential(
            credential_id=row["credential_id"],
            org_id=row["org_id"],
            agent_id=row["agent_id"],
            network=CredentialNetwork(row["network"]),
            status=CredentialStatus(row["status"]),
            credential_class=CredentialClass(row.get("credential_class", "opaque_delegated_token")),
            token_reference=row["token_reference"],
            token_encrypted=bytes(row["token_encrypted"]) if row.get("token_encrypted") else b"",
            scope=CredentialScope.from_dict(scope_data),
            provider_metadata=provider_meta,
            consent_id=row.get("consent_id", ""),
            last_used_at=row.get("last_used_at"),
            created_at=row.get("created_at", datetime.now(UTC)),
            expires_at=row.get("expires_at"),
        )

    async def store(self, credential: DelegatedCredential) -> str:
        import json
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO delegated_credentials
                    (credential_id, org_id, agent_id, network, status,
                     credential_class, token_reference, token_encrypted,
                     scope_json, provider_metadata, consent_id,
                     last_used_at, expires_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                """,
                credential.credential_id,
                credential.org_id,
                credential.agent_id,
                credential.network.value,
                credential.status.value,
                credential.credential_class.value,
                credential.token_reference,
                credential.token_encrypted,
                json.dumps(credential.scope.to_dict()),
                json.dumps(credential.provider_metadata),
                credential.consent_id,
                credential.last_used_at,
                credential.expires_at,
            )
        return credential.credential_id

    async def get(self, credential_id: str) -> DelegatedCredential | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM delegated_credentials WHERE credential_id = $1",
                credential_id,
            )
        if row is None:
            return None
        return self._row_to_credential(dict(row))

    async def get_for_agent(self, agent_id: str) -> list[DelegatedCredential]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM delegated_credentials WHERE agent_id = $1 ORDER BY created_at DESC",
                agent_id,
            )
        return [self._row_to_credential(dict(r)) for r in rows]

    async def get_active_for_agent(
        self, agent_id: str, network: CredentialNetwork | None = None,
    ) -> list[DelegatedCredential]:
        async with self._pool.acquire() as conn:
            if network:
                rows = await conn.fetch(
                    """SELECT * FROM delegated_credentials
                       WHERE agent_id = $1 AND status = 'active' AND network = $2
                       ORDER BY created_at DESC""",
                    agent_id, network.value,
                )
            else:
                rows = await conn.fetch(
                    """SELECT * FROM delegated_credentials
                       WHERE agent_id = $1 AND status = 'active'
                       ORDER BY created_at DESC""",
                    agent_id,
                )
        return [self._row_to_credential(dict(r)) for r in rows]

    async def update_status(
        self, credential_id: str, status: CredentialStatus,
    ) -> None:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE delegated_credentials
                   SET status = $2, updated_at = NOW()
                   WHERE credential_id = $1""",
                credential_id, status.value,
            )
            if result == "UPDATE 0":
                raise KeyError(f"Credential {credential_id} not found")

    async def revoke(self, credential_id: str, reason: str) -> None:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE delegated_credentials
                   SET status = 'revoked', revoke_reason = $2,
                       revoked_at = NOW(), updated_at = NOW()
                   WHERE credential_id = $1""",
                credential_id, reason,
            )
            if result == "UPDATE 0":
                raise KeyError(f"Credential {credential_id} not found")

    async def rotate(
        self, credential_id: str, new_token: bytes,
    ) -> DelegatedCredential:
        cred = await self.get(credential_id)
        if cred is None:
            raise KeyError(f"Credential {credential_id} not found")
        encrypted = self._encryption.encrypt_for_class(new_token, cred.credential_class)
        async with self._pool.acquire() as conn:
            await conn.execute(
                """UPDATE delegated_credentials
                   SET token_encrypted = $2, updated_at = NOW()
                   WHERE credential_id = $1""",
                credential_id, encrypted,
            )
        cred_updated = await self.get(credential_id)
        assert cred_updated is not None
        return cred_updated

    async def reprovision(
        self,
        credential_id: str,
        new_scope: CredentialScope,
        consent_id: str,
    ) -> DelegatedCredential:
        import json
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE delegated_credentials
                   SET status = 'active', scope_json = $2, consent_id = $3,
                       expires_at = $4, updated_at = NOW()
                   WHERE credential_id = $1""",
                credential_id,
                json.dumps(new_scope.to_dict()),
                consent_id,
                new_scope.expires_at,
            )
            if result == "UPDATE 0":
                raise KeyError(f"Credential {credential_id} not found")
        cred = await self.get(credential_id)
        assert cred is not None
        return cred

"""Consent ledger for delegated payment credentials.

Every credential grant requires explicit user consent.  The consent record
tracks who authorised the credential, how they authenticated, what they
approved, and when/why consent was revoked.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Protocol, runtime_checkable


class ConsentType(str, Enum):
    INITIAL_GRANT = "initial_grant"
    SCOPE_CHANGE = "scope_change"
    RENEWAL = "renewal"
    REVOCATION = "revocation"


@dataclass
class DelegationConsent:
    """Consent record for a delegated credential."""

    consent_id: str = field(
        default_factory=lambda: f"dcns_{uuid.uuid4().hex[:16]}"
    )
    org_id: str = ""
    user_id: str = ""
    agent_id: str = ""

    # Linked credential (null for pre-provisioning consent)
    credential_id: str | None = None

    consent_type: ConsentType = ConsentType.INITIAL_GRANT

    # Timestamps
    granted_at: datetime = field(
        default_factory=lambda: datetime.now(UTC)
    )
    expires_at: datetime | None = None

    # Snapshot of what was approved at consent time
    approved_scopes_snapshot: dict[str, Any] = field(default_factory=dict)

    # Revocation
    revocable: bool = True
    revoked_at: datetime | None = None
    revoke_reason: str | None = None

    # Provenance
    source_surface: str = "api"  # dashboard, sdk, browser_agent, api
    user_auth_context: dict[str, Any] = field(default_factory=dict)

    # Extra metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def is_valid(self) -> bool:
        if self.revoked_at is not None:
            return False
        return not (self.expires_at and datetime.now(UTC) >= self.expires_at)

    def to_dict(self) -> dict[str, Any]:
        return {
            "consent_id": self.consent_id,
            "org_id": self.org_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "credential_id": self.credential_id,
            "consent_type": self.consent_type.value,
            "granted_at": self.granted_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "approved_scopes_snapshot": self.approved_scopes_snapshot,
            "revocable": self.revocable,
            "revoked_at": self.revoked_at.isoformat() if self.revoked_at else None,
            "revoke_reason": self.revoke_reason,
            "source_surface": self.source_surface,
        }


# ---------------------------------------------------------------------------
# Store protocol
# ---------------------------------------------------------------------------

@runtime_checkable
class ConsentStore(Protocol):
    async def record_consent(self, consent: DelegationConsent) -> str: ...
    async def get(self, consent_id: str) -> DelegationConsent | None: ...
    async def get_for_credential(self, credential_id: str) -> list[DelegationConsent]: ...
    async def get_for_agent(self, agent_id: str) -> list[DelegationConsent]: ...
    async def revoke_consent(self, consent_id: str, reason: str) -> None: ...
    async def is_consent_valid(self, consent_id: str) -> bool: ...


# ---------------------------------------------------------------------------
# In-memory implementation (dev / test)
# ---------------------------------------------------------------------------

class InMemoryConsentStore:
    def __init__(self) -> None:
        self._consents: dict[str, DelegationConsent] = {}

    async def record_consent(self, consent: DelegationConsent) -> str:
        self._consents[consent.consent_id] = consent
        return consent.consent_id

    async def get(self, consent_id: str) -> DelegationConsent | None:
        return self._consents.get(consent_id)

    async def get_for_credential(self, credential_id: str) -> list[DelegationConsent]:
        return [
            c for c in self._consents.values()
            if c.credential_id == credential_id
        ]

    async def get_for_agent(self, agent_id: str) -> list[DelegationConsent]:
        return [
            c for c in self._consents.values()
            if c.agent_id == agent_id
        ]

    async def revoke_consent(self, consent_id: str, reason: str) -> None:
        consent = self._consents.get(consent_id)
        if consent is None:
            raise KeyError(f"Consent {consent_id} not found")
        consent.revoked_at = datetime.now(UTC)
        consent.revoke_reason = reason

    async def is_consent_valid(self, consent_id: str) -> bool:
        consent = self._consents.get(consent_id)
        if consent is None:
            return False
        return consent.is_valid


# ---------------------------------------------------------------------------
# PostgreSQL implementation (production)
# ---------------------------------------------------------------------------

class PostgresConsentStore:
    def __init__(self, pool) -> None:
        self._pool = pool

    def _row_to_consent(self, row: dict) -> DelegationConsent:
        scopes = row.get("approved_scopes_snapshot") or {}
        if isinstance(scopes, str):
            import json
            scopes = json.loads(scopes)
        auth_ctx = row.get("user_auth_context") or {}
        if isinstance(auth_ctx, str):
            import json
            auth_ctx = json.loads(auth_ctx)
        meta = row.get("metadata") or {}
        if isinstance(meta, str):
            import json
            meta = json.loads(meta)

        return DelegationConsent(
            consent_id=row["consent_id"],
            org_id=row["org_id"],
            user_id=row.get("user_id") or "",
            agent_id=row["agent_id"],
            credential_id=row.get("credential_id"),
            consent_type=ConsentType(row["consent_type"]),
            granted_at=row.get("granted_at", datetime.now(UTC)),
            expires_at=row.get("expires_at"),
            approved_scopes_snapshot=scopes,
            revocable=row.get("revocable", True),
            revoked_at=row.get("revoked_at"),
            revoke_reason=row.get("revoke_reason"),
            source_surface=row.get("source_surface", "api"),
            user_auth_context=auth_ctx,
            metadata=meta,
        )

    async def record_consent(self, consent: DelegationConsent) -> str:
        import json
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO delegation_consents
                    (consent_id, org_id, user_id, agent_id, credential_id,
                     consent_type, granted_at, expires_at,
                     approved_scopes_snapshot, revocable,
                     source_surface, user_auth_context, metadata)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
                """,
                consent.consent_id,
                consent.org_id,
                consent.user_id,
                consent.agent_id,
                consent.credential_id,
                consent.consent_type.value,
                consent.granted_at,
                consent.expires_at,
                json.dumps(consent.approved_scopes_snapshot),
                consent.revocable,
                consent.source_surface,
                json.dumps(consent.user_auth_context),
                json.dumps(consent.metadata),
            )
        return consent.consent_id

    async def get(self, consent_id: str) -> DelegationConsent | None:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM delegation_consents WHERE consent_id = $1",
                consent_id,
            )
        if row is None:
            return None
        return self._row_to_consent(dict(row))

    async def get_for_credential(self, credential_id: str) -> list[DelegationConsent]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM delegation_consents
                   WHERE credential_id = $1
                   ORDER BY granted_at DESC""",
                credential_id,
            )
        return [self._row_to_consent(dict(r)) for r in rows]

    async def get_for_agent(self, agent_id: str) -> list[DelegationConsent]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """SELECT * FROM delegation_consents
                   WHERE agent_id = $1
                   ORDER BY granted_at DESC""",
                agent_id,
            )
        return [self._row_to_consent(dict(r)) for r in rows]

    async def revoke_consent(self, consent_id: str, reason: str) -> None:
        async with self._pool.acquire() as conn:
            result = await conn.execute(
                """UPDATE delegation_consents
                   SET revoked_at = NOW(), revoke_reason = $2, updated_at = NOW()
                   WHERE consent_id = $1""",
                consent_id, reason,
            )
            if result == "UPDATE 0":
                raise KeyError(f"Consent {consent_id} not found")

    async def is_consent_valid(self, consent_id: str) -> bool:
        consent = await self.get(consent_id)
        if consent is None:
            return False
        return consent.is_valid

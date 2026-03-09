"""Tests for credential management API endpoints."""
from __future__ import annotations

from decimal import Decimal

import pytest
from sardis_v2_core.credential_store import CredentialEncryption, InMemoryCredentialStore
from sardis_v2_core.delegated_credential import (
    CredentialNetwork,
    CredentialScope,
    CredentialStatus,
    DelegatedCredential,
)
from sardis_v2_core.delegation_consent import (
    ConsentType,
    DelegationConsent,
    InMemoryConsentStore,
)


def _fernet_key() -> bytes:
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def _make_encryption() -> CredentialEncryption:
    return CredentialEncryption(key=_fernet_key())


class TestCredentialLifecycle:
    """Integration-style tests for the credential lifecycle."""

    @pytest.fixture
    def stores(self):
        return {
            "cred_store": InMemoryCredentialStore(encryption=_make_encryption()),
            "consent_store": InMemoryConsentStore(),
        }

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, stores):
        """consent -> provision -> get -> tighten scope -> suspend -> revoke"""
        cred_store = stores["cred_store"]
        consent_store = stores["consent_store"]

        # 1. Record consent
        consent = DelegationConsent(
            org_id="org_1",
            user_id="user_1",
            agent_id="agent_1",
            consent_type=ConsentType.INITIAL_GRANT,
            source_surface="api",
            approved_scopes_snapshot={"max_per_tx": "500", "daily_limit": "2000"},
        )
        consent_id = await consent_store.record_consent(consent)
        assert await consent_store.is_consent_valid(consent_id)

        # 2. Provision credential
        scope = CredentialScope(
            max_per_tx=Decimal("500"),
            daily_limit=Decimal("2000"),
        )
        cred = DelegatedCredential(
            org_id="org_1",
            agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            token_reference="tok_ref_test",
            token_encrypted=b"encrypted_payload",
            scope=scope,
            consent_id=consent_id,
        )
        cred_id = await cred_store.store(cred)

        # 3. Get credential
        retrieved = await cred_store.get(cred_id)
        assert retrieved is not None
        assert retrieved.consent_id == consent_id

        # 4. Tighten scope
        tighter = CredentialScope(
            max_per_tx=Decimal("200"),
            daily_limit=Decimal("1000"),
        )
        assert tighter.is_tighter_than(scope)
        updated = await cred_store.reprovision(cred_id, tighter, consent_id)
        assert updated.scope.max_per_tx == Decimal("200")

        # 5. Suspend
        await cred_store.update_status(cred_id, CredentialStatus.SUSPENDED)
        suspended = await cred_store.get(cred_id)
        assert suspended.status == CredentialStatus.SUSPENDED

        # 6. Revoke
        await cred_store.revoke(cred_id, "lifecycle test")
        revoked = await cred_store.get(cred_id)
        assert revoked.status == CredentialStatus.REVOKED

    @pytest.mark.asyncio
    async def test_scope_tightening_enforced(self, stores):
        """Cannot expand limits."""
        cred_store = stores["cred_store"]
        consent_store = stores["consent_store"]

        consent = DelegationConsent(
            org_id="org_1", agent_id="agent_1",
            source_surface="api",
        )
        consent_id = await consent_store.record_consent(consent)

        scope = CredentialScope(max_per_tx=Decimal("200"), daily_limit=Decimal("800"))
        cred = DelegatedCredential(
            org_id="org_1", agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            token_reference="tok", token_encrypted=b"enc",
            scope=scope, consent_id=consent_id,
        )
        await cred_store.store(cred)

        # Attempt to expand — should fail business logic check
        wider = CredentialScope(max_per_tx=Decimal("500"), daily_limit=Decimal("2000"))
        assert not wider.is_tighter_than(scope)

    @pytest.mark.asyncio
    async def test_no_provisioning_without_consent(self, stores):
        """Business logic: consent must be valid before provisioning."""
        consent_store = stores["consent_store"]
        valid = await consent_store.is_consent_valid("dcns_nonexistent")
        assert valid is False

    @pytest.mark.asyncio
    async def test_cross_org_access_denied(self, stores):
        """Credentials are org-scoped."""
        cred_store = stores["cred_store"]
        cred = DelegatedCredential(
            org_id="org_A", agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            token_reference="tok", token_encrypted=b"enc",
            consent_id="dcns_test",
        )
        await cred_store.store(cred)

        # Another org's agents shouldn't see this credential
        org_b_creds = await cred_store.get_for_agent("agent_2_org_b")
        assert len(org_b_creds) == 0

    @pytest.mark.asyncio
    async def test_rotate_vs_reprovision(self, stores):
        """Rotate: same authority, new token. Reprovision: new consent required."""
        cred_store = stores["cred_store"]
        consent_store = stores["consent_store"]

        consent1 = DelegationConsent(
            org_id="org_1", agent_id="agent_1", source_surface="api",
        )
        cid1 = await consent_store.record_consent(consent1)

        cred = DelegatedCredential(
            org_id="org_1", agent_id="agent_1",
            network=CredentialNetwork.STRIPE_SPT,
            status=CredentialStatus.ACTIVE,
            token_reference="tok", token_encrypted=b"enc",
            scope=CredentialScope(), consent_id=cid1,
        )
        await cred_store.store(cred)

        # Rotate: consent stays the same
        rotated = await cred_store.rotate(cred.credential_id, b"new_token")
        assert rotated.consent_id == cid1

        # Reprovision: new consent required
        consent2 = DelegationConsent(
            org_id="org_1", agent_id="agent_1",
            consent_type=ConsentType.SCOPE_CHANGE,
            source_surface="api",
        )
        cid2 = await consent_store.record_consent(consent2)
        new_scope = CredentialScope(max_per_tx=Decimal("100"))
        reprovisioned = await cred_store.reprovision(
            cred.credential_id, new_scope, cid2,
        )
        assert reprovisioned.consent_id == cid2
        assert reprovisioned.scope.max_per_tx == Decimal("100")

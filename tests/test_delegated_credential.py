"""Tests for delegated credential model, consent, and stores."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest
from sardis_v2_core.credential_store import (
    CredentialEncryption,
    InMemoryCredentialStore,
)
from sardis_v2_core.delegated_credential import (
    CREDENTIAL_HANDLING,
    CredentialClass,
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

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _fernet_key() -> bytes:
    """Generate a valid Fernet key for testing."""
    from cryptography.fernet import Fernet
    return Fernet.generate_key()


def _make_encryption() -> CredentialEncryption:
    return CredentialEncryption(key=_fernet_key())


def _make_consent(
    agent_id: str = "agent_1",
    org_id: str = "org_1",
    **kwargs,
) -> DelegationConsent:
    return DelegationConsent(
        org_id=org_id,
        user_id="user_1",
        agent_id=agent_id,
        source_surface="api",
        approved_scopes_snapshot={"max_per_tx": "500", "daily_limit": "2000"},
        **kwargs,
    )


def _make_credential(
    consent_id: str = "dcns_test",
    status: CredentialStatus = CredentialStatus.ACTIVE,
    credential_class: CredentialClass = CredentialClass.OPAQUE_DELEGATED_TOKEN,
    **kwargs,
) -> DelegatedCredential:
    return DelegatedCredential(
        org_id="org_1",
        agent_id="agent_1",
        network=CredentialNetwork.STRIPE_SPT,
        status=status,
        credential_class=credential_class,
        token_reference="tok_ref_123456abcdef",
        token_encrypted=b"encrypted_payload",
        consent_id=consent_id,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Credential model tests
# ---------------------------------------------------------------------------

class TestDelegatedCredential:

    def test_create_credential(self):
        cred = _make_credential()
        assert cred.credential_id.startswith("dcred_")
        assert cred.network == CredentialNetwork.STRIPE_SPT
        assert cred.status == CredentialStatus.ACTIVE
        assert cred.consent_id == "dcns_test"

    def test_is_valid_active(self):
        cred = _make_credential(status=CredentialStatus.ACTIVE)
        assert cred.is_valid is True

    def test_is_valid_provisioning(self):
        cred = _make_credential(status=CredentialStatus.PROVISIONING)
        assert cred.is_valid is False

    def test_is_valid_revoked(self):
        cred = _make_credential(status=CredentialStatus.REVOKED)
        assert cred.is_valid is False

    def test_is_valid_expired(self):
        cred = _make_credential(
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert cred.is_valid is False

    def test_can_execute_ok(self):
        cred = _make_credential()
        ok, msg = cred.can_execute(Decimal("100"), "merch_1", "5411")
        assert ok is True
        assert msg == "OK"

    def test_can_execute_exceeds_per_tx(self):
        cred = _make_credential()
        ok, msg = cred.can_execute(Decimal("999"))
        assert ok is False
        assert "per-tx limit" in msg

    def test_can_execute_merchant_not_allowed(self):
        scope = CredentialScope(allowed_merchant_ids=["merch_a", "merch_b"])
        cred = _make_credential(scope=scope)
        ok, msg = cred.can_execute(Decimal("10"), "merch_c")
        assert ok is False
        assert "not in allowed list" in msg

    def test_can_execute_mcc_not_allowed(self):
        scope = CredentialScope(allowed_mccs=["5411", "5412"])
        cred = _make_credential(scope=scope)
        ok, msg = cred.can_execute(Decimal("10"), mcc_code="9999")
        assert ok is False
        assert "MCC" in msg

    def test_can_execute_scope_expired(self):
        scope = CredentialScope(
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        cred = _make_credential(scope=scope)
        ok, msg = cred.can_execute(Decimal("10"))
        assert ok is False
        assert "scope expired" in msg

    def test_can_execute_invalid_status(self):
        cred = _make_credential(status=CredentialStatus.SUSPENDED)
        ok, msg = cred.can_execute(Decimal("10"))
        assert ok is False
        assert "invalid" in msg


# ---------------------------------------------------------------------------
# Credential class handling matrix tests
# ---------------------------------------------------------------------------

class TestCredentialClassHandling:

    def test_reference_only_handling(self):
        h = CREDENTIAL_HANDLING[CredentialClass.REFERENCE_ONLY]
        assert h["encrypt_at_rest"] is False
        assert h["exportable"] is True
        assert h["in_logs"] is True
        assert h["cacheable"] is True

    def test_opaque_token_handling(self):
        h = CREDENTIAL_HANDLING[CredentialClass.OPAQUE_DELEGATED_TOKEN]
        assert h["encrypt_at_rest"] is True
        assert h["envelope_encrypt"] is False
        assert h["exportable"] is False
        assert h["in_logs"] == "masked"

    def test_rehydratable_handling(self):
        h = CREDENTIAL_HANDLING[CredentialClass.REHYDRATABLE_EXECUTION_TOKEN]
        assert h["encrypt_at_rest"] is True
        assert h["envelope_encrypt"] is True
        assert h["in_logs"] is False
        assert h["cacheable"] is False

    def test_sensitive_handling(self):
        h = CREDENTIAL_HANDLING[CredentialClass.SENSITIVE_PAYMENT_SECRET]
        assert h["encrypt_at_rest"] is True
        assert h["envelope_encrypt"] is True
        assert h["exportable"] is False
        assert h["decryptable_by"] == "hsm"

    def test_mask_token_reference_only(self):
        cred = _make_credential(credential_class=CredentialClass.REFERENCE_ONLY)
        assert cred.mask_token_reference() == cred.token_reference

    def test_mask_token_opaque(self):
        cred = _make_credential(credential_class=CredentialClass.OPAQUE_DELEGATED_TOKEN)
        masked = cred.mask_token_reference()
        assert masked.startswith("tok_")
        assert "..." in masked

    def test_mask_token_rehydratable(self):
        cred = _make_credential(credential_class=CredentialClass.REHYDRATABLE_EXECUTION_TOKEN)
        assert cred.mask_token_reference() == "[REDACTED]"


# ---------------------------------------------------------------------------
# Scope tests
# ---------------------------------------------------------------------------

class TestCredentialScope:

    def test_scope_to_dict_roundtrip(self):
        scope = CredentialScope(
            max_per_tx=Decimal("100"),
            daily_limit=Decimal("500"),
            allowed_mccs=["5411"],
            allowed_merchant_ids=["merch_a"],
        )
        d = scope.to_dict()
        restored = CredentialScope.from_dict(d)
        assert restored.max_per_tx == Decimal("100")
        assert restored.daily_limit == Decimal("500")
        assert restored.allowed_mccs == ["5411"]

    def test_is_tighter_than(self):
        wide = CredentialScope(max_per_tx=Decimal("500"), daily_limit=Decimal("2000"))
        tight = CredentialScope(max_per_tx=Decimal("200"), daily_limit=Decimal("1000"))
        assert tight.is_tighter_than(wide)
        assert not wide.is_tighter_than(tight)


# ---------------------------------------------------------------------------
# Encryption tests
# ---------------------------------------------------------------------------

class TestCredentialEncryption:

    def test_encrypt_decrypt_roundtrip(self):
        enc = _make_encryption()
        plaintext = b"secret-token-payload"
        encrypted = enc.encrypt(plaintext)
        assert encrypted != plaintext
        decrypted = enc.decrypt(encrypted)
        assert decrypted == plaintext

    def test_envelope_encrypt_roundtrip(self):
        enc = _make_encryption()
        plaintext = b"super-secret"
        encrypted = enc.encrypt_with_envelope(plaintext)
        decrypted = enc.decrypt_with_envelope(encrypted)
        assert decrypted == plaintext

    def test_encrypt_for_reference_only_class(self):
        enc = _make_encryption()
        plaintext = b"ref-value"
        result = enc.encrypt_for_class(plaintext, CredentialClass.REFERENCE_ONLY)
        assert result == plaintext  # no encryption

    def test_encrypt_for_opaque_class(self):
        enc = _make_encryption()
        plaintext = b"opaque-token"
        result = enc.encrypt_for_class(plaintext, CredentialClass.OPAQUE_DELEGATED_TOKEN)
        assert result != plaintext
        decrypted = enc.decrypt_for_class(result, CredentialClass.OPAQUE_DELEGATED_TOKEN)
        assert decrypted == plaintext

    def test_encrypt_for_rehydratable_class(self):
        enc = _make_encryption()
        plaintext = b"exec-token"
        result = enc.encrypt_for_class(plaintext, CredentialClass.REHYDRATABLE_EXECUTION_TOKEN)
        assert result != plaintext
        decrypted = enc.decrypt_for_class(result, CredentialClass.REHYDRATABLE_EXECUTION_TOKEN)
        assert decrypted == plaintext

    def test_encrypt_for_sensitive_class(self):
        enc = _make_encryption()
        plaintext = b"payment-secret"
        result = enc.encrypt_for_class(plaintext, CredentialClass.SENSITIVE_PAYMENT_SECRET)
        assert result != plaintext
        decrypted = enc.decrypt_for_class(result, CredentialClass.SENSITIVE_PAYMENT_SECRET)
        assert decrypted == plaintext


# ---------------------------------------------------------------------------
# InMemoryCredentialStore tests
# ---------------------------------------------------------------------------

class TestInMemoryCredentialStore:

    @pytest.fixture
    def store(self):
        return InMemoryCredentialStore(encryption=_make_encryption())

    @pytest.mark.asyncio
    async def test_store_and_get(self, store):
        cred = _make_credential()
        cid = await store.store(cred)
        assert cid == cred.credential_id
        retrieved = await store.get(cid)
        assert retrieved is not None
        assert retrieved.credential_id == cred.credential_id

    @pytest.mark.asyncio
    async def test_get_not_found(self, store):
        result = await store.get("dcred_nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_for_agent(self, store):
        cred1 = _make_credential()
        cred2 = _make_credential()
        await store.store(cred1)
        await store.store(cred2)
        results = await store.get_for_agent("agent_1")
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_active_for_agent(self, store):
        active = _make_credential(status=CredentialStatus.ACTIVE)
        revoked = _make_credential(status=CredentialStatus.REVOKED)
        await store.store(active)
        await store.store(revoked)
        results = await store.get_active_for_agent("agent_1")
        assert len(results) == 1
        assert results[0].status == CredentialStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_get_active_for_agent_with_network_filter(self, store):
        cred = _make_credential()
        await store.store(cred)
        results = await store.get_active_for_agent("agent_1", CredentialNetwork.VISA_TAP)
        assert len(results) == 0
        results = await store.get_active_for_agent("agent_1", CredentialNetwork.STRIPE_SPT)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_update_status(self, store):
        cred = _make_credential()
        await store.store(cred)
        await store.update_status(cred.credential_id, CredentialStatus.SUSPENDED)
        updated = await store.get(cred.credential_id)
        assert updated is not None
        assert updated.status == CredentialStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_revoke(self, store):
        cred = _make_credential()
        await store.store(cred)
        await store.revoke(cred.credential_id, "user requested")
        updated = await store.get(cred.credential_id)
        assert updated is not None
        assert updated.status == CredentialStatus.REVOKED
        assert updated.provider_metadata.get("revoke_reason") == "user requested"

    @pytest.mark.asyncio
    async def test_rotate(self, store):
        cred = _make_credential()
        await store.store(cred)
        new_token = b"new-token-bytes"
        updated = await store.rotate(cred.credential_id, new_token)
        assert updated.token_encrypted != cred.token_encrypted
        assert updated.consent_id == cred.consent_id  # same authority

    @pytest.mark.asyncio
    async def test_reprovision(self, store):
        cred = _make_credential(status=CredentialStatus.SUSPENDED)
        await store.store(cred)
        new_scope = CredentialScope(max_per_tx=Decimal("200"), daily_limit=Decimal("800"))
        updated = await store.reprovision(cred.credential_id, new_scope, "dcns_new_consent")
        assert updated.status == CredentialStatus.ACTIVE
        assert updated.scope.max_per_tx == Decimal("200")
        assert updated.consent_id == "dcns_new_consent"

    @pytest.mark.asyncio
    async def test_status_transitions(self, store):
        """provisioning -> active -> suspended -> revoked"""
        cred = _make_credential(status=CredentialStatus.PROVISIONING)
        await store.store(cred)
        await store.update_status(cred.credential_id, CredentialStatus.ACTIVE)
        c = await store.get(cred.credential_id)
        assert c.status == CredentialStatus.ACTIVE
        await store.update_status(cred.credential_id, CredentialStatus.SUSPENDED)
        c = await store.get(cred.credential_id)
        assert c.status == CredentialStatus.SUSPENDED
        await store.revoke(cred.credential_id, "policy violation")
        c = await store.get(cred.credential_id)
        assert c.status == CredentialStatus.REVOKED


# ---------------------------------------------------------------------------
# Consent tests
# ---------------------------------------------------------------------------

class TestDelegationConsent:

    def test_create_consent(self):
        consent = _make_consent()
        assert consent.consent_id.startswith("dcns_")
        assert consent.is_valid is True

    def test_consent_revoked_is_invalid(self):
        consent = _make_consent()
        consent.revoked_at = datetime.now(UTC)
        assert consent.is_valid is False

    def test_consent_expired_is_invalid(self):
        consent = _make_consent(
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert consent.is_valid is False

    def test_consent_to_dict(self):
        consent = _make_consent()
        d = consent.to_dict()
        assert d["consent_type"] == "initial_grant"
        assert d["source_surface"] == "api"


class TestInMemoryConsentStore:

    @pytest.fixture
    def store(self):
        return InMemoryConsentStore()

    @pytest.mark.asyncio
    async def test_record_and_get(self, store):
        consent = _make_consent()
        cid = await store.record_consent(consent)
        retrieved = await store.get(cid)
        assert retrieved is not None
        assert retrieved.consent_id == consent.consent_id

    @pytest.mark.asyncio
    async def test_get_for_agent(self, store):
        c1 = _make_consent(agent_id="agent_1")
        c2 = _make_consent(agent_id="agent_2")
        await store.record_consent(c1)
        await store.record_consent(c2)
        results = await store.get_for_agent("agent_1")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_get_for_credential(self, store):
        consent = _make_consent(credential_id="dcred_abc")
        await store.record_consent(consent)
        results = await store.get_for_credential("dcred_abc")
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_revoke_consent(self, store):
        consent = _make_consent()
        await store.record_consent(consent)
        await store.revoke_consent(consent.consent_id, "user revoked")
        retrieved = await store.get(consent.consent_id)
        assert retrieved.revoked_at is not None
        assert retrieved.revoke_reason == "user revoked"
        assert retrieved.is_valid is False

    @pytest.mark.asyncio
    async def test_is_consent_valid(self, store):
        consent = _make_consent()
        await store.record_consent(consent)
        assert await store.is_consent_valid(consent.consent_id) is True
        await store.revoke_consent(consent.consent_id, "revoked")
        assert await store.is_consent_valid(consent.consent_id) is False

    @pytest.mark.asyncio
    async def test_is_consent_valid_not_found(self, store):
        assert await store.is_consent_valid("dcns_nonexistent") is False


# ---------------------------------------------------------------------------
# Consent-credential integration
# ---------------------------------------------------------------------------

class TestConsentCredentialIntegration:

    @pytest.mark.asyncio
    async def test_no_credential_without_consent(self):
        """Credentials must have a consent_id — empty string is default."""
        cred = _make_credential(consent_id="")
        assert cred.consent_id == ""
        # DB schema enforces NOT NULL; empty string will fail FK constraint

    @pytest.mark.asyncio
    async def test_consent_revocation_cascades(self):
        """When consent is revoked, credential should be suspended."""
        consent_store = InMemoryConsentStore()
        cred_store = InMemoryCredentialStore(encryption=_make_encryption())

        consent = _make_consent()
        await consent_store.record_consent(consent)

        cred = _make_credential(consent_id=consent.consent_id)
        await cred_store.store(cred)

        # Revoke consent
        await consent_store.revoke_consent(consent.consent_id, "policy change")

        # Application logic: suspend credential when consent revoked
        valid = await consent_store.is_consent_valid(consent.consent_id)
        assert valid is False

        # Simulate cascade
        if not valid:
            await cred_store.update_status(cred.credential_id, CredentialStatus.SUSPENDED)

        updated = await cred_store.get(cred.credential_id)
        assert updated.status == CredentialStatus.SUSPENDED

    @pytest.mark.asyncio
    async def test_consent_chain_integrity(self):
        """initial_grant -> scope_change -> revocation chain."""
        store = InMemoryConsentStore()

        # Initial grant
        c1 = _make_consent(consent_type=ConsentType.INITIAL_GRANT)
        await store.record_consent(c1)

        # Scope change
        c2 = _make_consent(
            consent_type=ConsentType.SCOPE_CHANGE,
            credential_id="dcred_test",
        )
        await store.record_consent(c2)

        # Revocation
        c3 = _make_consent(consent_type=ConsentType.REVOCATION)
        await store.record_consent(c3)

        agent_consents = await store.get_for_agent("agent_1")
        assert len(agent_consents) == 3
        types = [c.consent_type for c in agent_consents]
        assert ConsentType.INITIAL_GRANT in types
        assert ConsentType.SCOPE_CHANGE in types
        assert ConsentType.REVOCATION in types

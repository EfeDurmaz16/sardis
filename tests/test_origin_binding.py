"""Tests for origin binding security features.

Verifies that payment intents are bound to their originating context
(page origin, action description, session state) so that prompt injection
attacks in browser agents cannot smuggle transactions.
"""
import hashlib
from datetime import UTC, datetime

import pytest
from sardis_v2_core.attestation_envelope import (
    AttestationEnvelope,
    _hash_value,
    build_attestation_envelope,
    verify_attestation_signature,
)
from sardis_v2_core.execution_intent import ExecutionIntent, IntentSource


class TestExecutionIntentOriginBinding:
    """ExecutionIntent carries origin context for browser agent payments."""

    def test_default_origin_fields_empty(self):
        intent = ExecutionIntent()
        assert intent.origin_url == ""
        assert intent.action_description == ""
        assert intent.action_description_hash == ""
        assert intent.session_context_hash == ""
        assert intent.approved_at is None

    def test_origin_fields_set(self):
        now = datetime.now(UTC)
        intent = ExecutionIntent(
            origin_url="https://shop.example.com/checkout",
            action_description="Purchase 3x Widget at $10 each",
            action_description_hash=hashlib.sha256(
                b"Purchase 3x Widget at $10 each"
            ).hexdigest(),
            session_context_hash="abc123def456",
            approved_at=now,
        )
        assert intent.origin_url == "https://shop.example.com/checkout"
        assert intent.action_description == "Purchase 3x Widget at $10 each"
        assert intent.approved_at == now

    def test_to_dict_includes_origin_fields(self):
        intent = ExecutionIntent(
            origin_url="https://example.com",
            action_description="test payment",
            action_description_hash="hash123",
            session_context_hash="session456",
        )
        d = intent.to_dict()
        assert d["origin_url"] == "https://example.com"
        assert d["action_description"] == "test payment"
        assert d["action_description_hash"] == "hash123"
        assert d["session_context_hash"] == "session456"
        assert d["approved_at"] is None

    def test_to_dict_approved_at_iso(self):
        now = datetime.now(UTC)
        intent = ExecutionIntent(approved_at=now)
        d = intent.to_dict()
        assert d["approved_at"] == now.isoformat()

    def test_browser_source_with_origin(self):
        """AP2 intents from browser agents should carry origin."""
        intent = ExecutionIntent(
            source=IntentSource.AP2,
            origin_url="https://merchant.example.com/pay",
            action_description="Buy premium plan for $49/mo",
        )
        assert intent.source == IntentSource.AP2
        assert intent.origin_url == "https://merchant.example.com/pay"


class TestAttestationEnvelopeOriginBinding:
    """AttestationEnvelope captures origin context for audit trail."""

    def test_default_origin_fields_empty(self):
        envelope = AttestationEnvelope(
            attestation_id="att_test",
            timestamp="2026-01-01T00:00:00Z",
            agent_did="did:sardis:agent_1",
            mandate_id="mnd_1",
            policy_rules_applied=["per_tx_limit"],
            evidence_chain=["hash1"],
        )
        assert envelope.origin_hash == ""
        assert envelope.action_description_hash == ""
        assert envelope.approval_timestamp == ""

    def test_to_dict_includes_origin_fields(self):
        envelope = AttestationEnvelope(
            attestation_id="att_test",
            timestamp="2026-01-01T00:00:00Z",
            agent_did="did:sardis:agent_1",
            mandate_id="mnd_1",
            policy_rules_applied=[],
            evidence_chain=[],
            origin_hash="origin_hash_abc",
            action_description_hash="action_hash_def",
            approval_timestamp="2026-01-01T00:00:00Z",
        )
        d = envelope.to_dict()
        assert d["origin_hash"] == "origin_hash_abc"
        assert d["action_description_hash"] == "action_hash_def"
        assert d["approval_timestamp"] == "2026-01-01T00:00:00Z"

    def test_build_envelope_with_origin_context(self):
        envelope = build_attestation_envelope(
            mandate_id="mnd_1",
            agent_did="did:sardis:agent_1",
            policy_rules=["per_tx_limit"],
            evidence=["hash1"],
            origin_url="https://example.com/pay",
            action_description_hash="desc_hash_123",
            approval_timestamp="2026-01-01T00:00:00Z",
        )
        # origin_url should be hashed, not stored raw
        assert envelope.origin_hash != ""
        assert envelope.origin_hash != "https://example.com/pay"
        assert envelope.origin_hash == _hash_value("https://example.com/pay")
        assert envelope.action_description_hash == "desc_hash_123"
        assert envelope.approval_timestamp == "2026-01-01T00:00:00Z"

    def test_build_envelope_without_origin_context(self):
        """Backward compat: no origin = empty fields."""
        envelope = build_attestation_envelope(
            mandate_id="mnd_1",
            agent_did="did:sardis:agent_1",
            policy_rules=[],
            evidence=[],
        )
        assert envelope.origin_hash == ""
        assert envelope.action_description_hash == ""
        assert envelope.approval_timestamp == ""


class TestHashValue:
    """_hash_value produces deterministic SHA-256 hashes."""

    def test_consistent_hash(self):
        assert _hash_value("hello") == _hash_value("hello")

    def test_different_inputs_different_hashes(self):
        assert _hash_value("hello") != _hash_value("world")

    def test_matches_stdlib(self):
        expected = hashlib.sha256(b"test").hexdigest()
        assert _hash_value("test") == expected

    def test_empty_string(self):
        assert _hash_value("") == hashlib.sha256(b"").hexdigest()


class TestVerifierActionDescriptionHashCheck:
    """MandateVerifier.verify_chain() enforces action_description_hash on IntentMandate."""

    def _make_chain_bundle(self, *, description: str = "", desc_hash: str = ""):
        """Build a minimal AP2 chain bundle for testing the verifier check.

        We don't need valid signatures here — just enough to trigger the
        action_description_hash check (which runs before signature verification).
        """
        import time
        now = int(time.time()) + 300
        return {
            "intent": {
                "mandate_id": "int_test",
                "mandate_type": "intent",
                "issuer": "agent_1",
                "subject": "agent_1",
                "expires_at": now,
                "nonce": "n1",
                "domain": "sardis.sh",
                "purpose": "intent",
                "scope": ["compute"],
                "natural_language_description": description,
                "action_description_hash": desc_hash,
                "proof": {
                    "verification_method": "did:key:z6Mktest#key-1",
                    "created": "2026-01-01T00:00:00Z",
                    "proof_value": "dGVzdA==",
                },
            },
            "cart": {
                "mandate_id": "cart_test",
                "mandate_type": "cart",
                "issuer": "merchant_1",
                "subject": "agent_1",
                "expires_at": now,
                "nonce": "n2",
                "domain": "sardis.sh",
                "purpose": "cart",
                "line_items": [{"item_id": "i1", "name": "Widget", "quantity": 1, "price_minor": 1000}],
                "merchant_domain": "shop.example.com",
                "currency": "USD",
                "subtotal_minor": 1000,
                "taxes_minor": 80,
                "proof": {
                    "verification_method": "did:key:z6Mktest#key-1",
                    "created": "2026-01-01T00:00:00Z",
                    "proof_value": "dGVzdA==",
                },
            },
            "payment": {
                "mandate_id": "pay_test",
                "mandate_type": "payment",
                "issuer": "agent_1",
                "subject": "agent_1",
                "expires_at": now,
                "nonce": "n3",
                "domain": "sardis.sh",
                "purpose": "checkout",
                "chain": "base",
                "token": "USDC",
                "amount_minor": 1000,
                "destination": "0xmerchant",
                "audit_hash": "ah_test",
                "ai_agent_presence": True,
                "transaction_modality": "human_present",
                "merchant_domain": "shop.example.com",
                "proof": {
                    "verification_method": "did:key:z6Mktest#key-1",
                    "created": "2026-01-01T00:00:00Z",
                    "proof_value": "dGVzdA==",
                },
            },
        }

    def test_mismatched_hash_rejects_chain(self):
        """If action_description_hash doesn't match SHA-256(description), chain is rejected."""
        import os
        os.environ.setdefault("SARDIS_ENVIRONMENT", "test")

        from sardis_protocol.verifier import MandateVerifier
        from sardis_v2_core import SardisSettings

        settings = SardisSettings(allowed_domains=["sardis.sh"])
        verifier = MandateVerifier(settings=settings)

        bundle = self._make_chain_bundle(
            description="Buy 1 Widget for $10",
            desc_hash="wrong_hash_that_does_not_match",
        )

        from sardis_protocol.schemas import AP2PaymentExecuteRequest
        req = AP2PaymentExecuteRequest(**bundle)
        result = verifier.verify_chain(req)

        assert not result.accepted
        assert result.reason == "action_description_hash_mismatch"

    def test_correct_hash_passes_check(self):
        """Correct action_description_hash passes the origin binding check."""
        import os
        os.environ.setdefault("SARDIS_ENVIRONMENT", "test")

        from sardis_protocol.verifier import MandateVerifier
        from sardis_v2_core import SardisSettings

        settings = SardisSettings(allowed_domains=["sardis.sh"])
        verifier = MandateVerifier(settings=settings)

        description = "Buy 1 Widget for $10"
        correct_hash = hashlib.sha256(description.encode("utf-8")).hexdigest()

        bundle = self._make_chain_bundle(
            description=description,
            desc_hash=correct_hash,
        )

        from sardis_protocol.schemas import AP2PaymentExecuteRequest
        req = AP2PaymentExecuteRequest(**bundle)
        result = verifier.verify_chain(req)

        # Should pass the hash check (may fail later on signature verification,
        # but the reason should NOT be action_description_hash_mismatch)
        if not result.accepted:
            assert result.reason != "action_description_hash_mismatch"

    def test_empty_description_skips_check(self):
        """No description = no check (backward compat)."""
        import os
        os.environ.setdefault("SARDIS_ENVIRONMENT", "test")

        from sardis_protocol.verifier import MandateVerifier
        from sardis_v2_core import SardisSettings

        settings = SardisSettings(allowed_domains=["sardis.sh"])
        verifier = MandateVerifier(settings=settings)

        bundle = self._make_chain_bundle(description="", desc_hash="")

        from sardis_protocol.schemas import AP2PaymentExecuteRequest
        req = AP2PaymentExecuteRequest(**bundle)
        result = verifier.verify_chain(req)

        # Should not fail on action_description_hash_mismatch
        if not result.accepted:
            assert result.reason != "action_description_hash_mismatch"


class TestSignatureCoversOriginFields:
    """Attestation signature must cover origin fields (tamper-evident)."""

    def test_modified_origin_hash_invalidates_signature(self):
        """If origin_hash is tampered after signing, verification fails."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key_bytes = private_key.public_key().public_bytes_raw()
        signing_key = private_key.private_bytes_raw()

        envelope = build_attestation_envelope(
            mandate_id="mnd_tamper_test",
            agent_did="did:sardis:agent_1",
            policy_rules=["per_tx_limit"],
            evidence=["hash1"],
            signing_key=signing_key,
            origin_url="https://legit-merchant.com",
            action_description_hash="legit_hash",
            approval_timestamp="2026-01-01T00:00:00Z",
        )

        # Signature should be valid initially
        assert verify_attestation_signature(envelope, public_key_bytes)

        # Tamper with origin_hash
        envelope.origin_hash = _hash_value("https://evil-merchant.com")

        # Signature should now be INVALID
        assert not verify_attestation_signature(envelope, public_key_bytes)

    def test_modified_action_hash_invalidates_signature(self):
        """If action_description_hash is tampered, verification fails."""
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

        private_key = Ed25519PrivateKey.generate()
        public_key_bytes = private_key.public_key().public_bytes_raw()
        signing_key = private_key.private_bytes_raw()

        envelope = build_attestation_envelope(
            mandate_id="mnd_tamper_test2",
            agent_did="did:sardis:agent_1",
            policy_rules=[],
            evidence=[],
            signing_key=signing_key,
            action_description_hash="original_action",
        )
        assert verify_attestation_signature(envelope, public_key_bytes)

        envelope.action_description_hash = "smuggled_action"
        assert not verify_attestation_signature(envelope, public_key_bytes)

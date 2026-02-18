"""Tests: KYC/AML compliance gating across all payment paths."""
from __future__ import annotations

import time
import uuid
from unittest.mock import MagicMock
import pytest

from sardis_compliance.checks import ComplianceEngine, ComplianceAuditStore
from sardis_v2_core.mandates import PaymentMandate, VCProof


# ============ Mock Services ============


class MockSanctionsService:
    """Mock sanctions screening service matching Elliptic interface."""

    def __init__(self, should_block: bool = False, raise_error: bool = False):
        self._should_block = should_block
        self._raise_error = raise_error

    async def screen_address(self, address: str, chain: str = ""):
        if self._raise_error:
            raise ConnectionError("Sanctions API unavailable")
        result = MagicMock()
        result.should_block = self._should_block
        result.risk_score = 0.9 if self._should_block else 0.1
        result.reason = "ofac_match" if self._should_block else None
        result.provider = "elliptic"
        return result


class MockKYCService:
    """Mock KYC verification service matching Persona interface."""

    def __init__(self, verified: bool = True, raise_error: bool = False):
        self._verified = verified
        self._raise_error = raise_error

    async def check_verification(self, subject: str):
        if self._raise_error:
            raise ConnectionError("KYC API unavailable")
        result = MagicMock()
        result.is_verified = self._verified
        result.status = "approved" if self._verified else "not_started"
        return result


# ============ Helpers ============


def _make_mock_audit_store() -> ComplianceAuditStore:
    """Return an in-memory audit store (safe in non-prod env)."""
    return ComplianceAuditStore()


def _make_mock_provider(allowed: bool = True, reason: str | None = None):
    """Return a synchronous mock compliance provider."""
    from sardis_compliance.checks import ComplianceResult
    provider = MagicMock()
    provider.evaluate.return_value = ComplianceResult(
        allowed=allowed,
        reason=reason,
        provider="mock_rules",
        rule_id="mock_baseline",
    )
    return provider


def _make_payment_mandate(
    subject: str = "agent_123",
    destination: str = "0xabc",
    chain: str = "base",
    token: str = "USDC",
    amount_minor: int = 100_000_000,
) -> PaymentMandate:
    """Construct a minimal valid PaymentMandate."""
    proof = VCProof(
        verification_method="did:key:z6Mk#key-1",
        created="2024-01-01T00:00:00Z",
        proof_value="test_proof_value",
    )
    return PaymentMandate(
        mandate_id=str(uuid.uuid4()),
        mandate_type="payment",
        issuer="did:key:z6Mk",
        subject=subject,
        expires_at=int(time.time()) + 3600,
        nonce=str(uuid.uuid4()),
        proof=proof,
        domain="example.com",
        purpose="checkout",
        chain=chain,
        token=token,
        amount_minor=amount_minor,
        destination=destination,
        audit_hash="abc123",
    )


def _make_engine(
    kyc_service=None,
    sanctions_service=None,
    provider_allowed: bool = True,
) -> ComplianceEngine:
    """Construct a ComplianceEngine with mock audit store and provider."""
    return ComplianceEngine(
        settings=MagicMock(),
        provider=_make_mock_provider(allowed=provider_allowed),
        audit_store=_make_mock_audit_store(),
        kyc_service=kyc_service,
        sanctions_service=sanctions_service,
    )


# ============ Sanctions Tests ============


class TestComplianceEngineSanctions:
    """Test sanctions screening in ComplianceEngine.preflight()."""

    @pytest.mark.asyncio
    async def test_sanctions_flagged_address_blocked(self):
        """Sanctioned address must be blocked with a sanctions-related reason."""
        engine = _make_engine(sanctions_service=MockSanctionsService(should_block=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert result.reason is not None
        assert "sanction" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_sanctions_clean_address_allowed(self):
        """Non-sanctioned address with no KYC requirement must pass."""
        engine = _make_engine(sanctions_service=MockSanctionsService(should_block=False))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.allowed

    @pytest.mark.asyncio
    async def test_sanctions_error_fails_closed(self):
        """Sanctions API error must block the transaction regardless of environment."""
        engine = _make_engine(sanctions_service=MockSanctionsService(raise_error=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert result.reason is not None
        assert "sanction" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_sanctions_rule_id_set_on_block(self):
        """Blocked result from sanctions must carry the correct rule_id."""
        engine = _make_engine(sanctions_service=MockSanctionsService(should_block=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.rule_id == "sanctions_screening"

    @pytest.mark.asyncio
    async def test_sanctions_audit_id_recorded(self):
        """Every preflight call must produce an audit_id."""
        engine = _make_engine(sanctions_service=MockSanctionsService(should_block=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.audit_id is not None
        assert len(result.audit_id) > 0


# ============ KYC Tests ============


class TestComplianceEngineKYC:
    """Test KYC verification in ComplianceEngine.preflight()."""

    @pytest.mark.asyncio
    async def test_kyc_unverified_agent_blocked(self):
        """Agent without KYC verification must be blocked."""
        engine = _make_engine(kyc_service=MockKYCService(verified=False))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert result.reason is not None
        assert "kyc" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_kyc_verified_agent_allowed(self):
        """Agent with completed KYC must pass when no sanctions hit."""
        engine = _make_engine(kyc_service=MockKYCService(verified=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.allowed

    @pytest.mark.asyncio
    async def test_kyc_error_fails_closed(self):
        """KYC API error must block the transaction (fail-closed)."""
        engine = _make_engine(kyc_service=MockKYCService(raise_error=True))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert result.reason is not None
        assert "kyc" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_kyc_rule_id_set_on_block(self):
        """Blocked result from KYC must carry the correct rule_id."""
        engine = _make_engine(kyc_service=MockKYCService(verified=False))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.rule_id == "kyc_verification"

    @pytest.mark.asyncio
    async def test_kyc_provider_set_to_persona(self):
        """KYC block must be attributed to persona provider."""
        engine = _make_engine(kyc_service=MockKYCService(verified=False))
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.provider == "persona"

    @pytest.mark.asyncio
    async def test_kyc_not_checked_when_sanctions_block(self):
        """KYC must not be invoked if sanctions already blocked the mandate."""
        kyc_mock = MockKYCService(verified=True)
        # Replace check_verification with a tracker to ensure it is never called
        called = []

        async def tracking_check(subject: str):
            called.append(subject)
            return await MockKYCService(verified=True).check_verification(subject)

        kyc_mock.check_verification = tracking_check

        engine = _make_engine(
            kyc_service=kyc_mock,
            sanctions_service=MockSanctionsService(should_block=True),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert called == [], "KYC service must not be called when sanctions block first"


# ============ Combined KYC + AML Tests ============


class TestComplianceBothServices:
    """Test combined KYC + AML enforcement."""

    @pytest.mark.asyncio
    async def test_both_pass(self):
        """Both KYC and sanctions passing must result in allowed."""
        engine = _make_engine(
            kyc_service=MockKYCService(verified=True),
            sanctions_service=MockSanctionsService(should_block=False),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.allowed

    @pytest.mark.asyncio
    async def test_kyc_fails_sanctions_passes(self):
        """Failing KYC must block even when sanctions pass."""
        engine = _make_engine(
            kyc_service=MockKYCService(verified=False),
            sanctions_service=MockSanctionsService(should_block=False),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert "kyc" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_sanctions_fails_kyc_passes(self):
        """Sanctions hit must block even when KYC is verified."""
        engine = _make_engine(
            kyc_service=MockKYCService(verified=True),
            sanctions_service=MockSanctionsService(should_block=True),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert "sanction" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_both_fail_sanctions_reason_wins(self):
        """When both services block, sanctions reason wins (checked first)."""
        engine = _make_engine(
            kyc_service=MockKYCService(verified=False),
            sanctions_service=MockSanctionsService(should_block=True),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert "sanction" in (result.reason or "").lower()

    @pytest.mark.asyncio
    async def test_both_services_errors_fail_closed(self):
        """Both services erroring must still fail-closed."""
        engine = _make_engine(
            kyc_service=MockKYCService(raise_error=True),
            sanctions_service=MockSanctionsService(raise_error=True),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed


# ============ Base Provider Tests ============


class TestComplianceBaseRules:
    """Test that base rule provider blocks flow before KYC/AML."""

    @pytest.mark.asyncio
    async def test_base_rules_block_skips_kyc_and_sanctions(self):
        """When base provider blocks, KYC and sanctions must not be called."""
        kyc_calls = []
        sanctions_calls = []

        class TrackingKYC:
            async def check_verification(self, subject):
                kyc_calls.append(subject)
                return MagicMock(is_verified=True)

        class TrackingSanctions:
            async def screen_address(self, address, chain=""):
                sanctions_calls.append(address)
                return MagicMock(should_block=False, reason=None, provider="elliptic")

        engine = ComplianceEngine(
            settings=MagicMock(),
            provider=_make_mock_provider(allowed=False, reason="token_not_permitted"),
            audit_store=_make_mock_audit_store(),
            kyc_service=TrackingKYC(),
            sanctions_service=TrackingSanctions(),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert kyc_calls == [], "KYC must not be called when base rules block"
        assert sanctions_calls == [], "Sanctions must not be called when base rules block"


# ============ Audit Trail Tests ============


class TestComplianceAuditTrail:
    """Verify audit entries are recorded for all outcomes."""

    @pytest.mark.asyncio
    async def test_audit_recorded_on_allow(self):
        """Allowed mandates must generate an audit entry."""
        audit_store = _make_mock_audit_store()
        engine = ComplianceEngine(
            settings=MagicMock(),
            provider=_make_mock_provider(allowed=True),
            audit_store=audit_store,
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert result.allowed
        assert result.audit_id is not None
        assert audit_store.count() == 1

    @pytest.mark.asyncio
    async def test_audit_recorded_on_deny(self):
        """Denied mandates must also generate an audit entry."""
        audit_store = _make_mock_audit_store()
        engine = ComplianceEngine(
            settings=MagicMock(),
            provider=_make_mock_provider(allowed=True),
            audit_store=audit_store,
            sanctions_service=MockSanctionsService(should_block=True),
        )
        mandate = _make_payment_mandate()
        result = await engine.preflight(mandate)
        assert not result.allowed
        assert result.audit_id is not None
        assert audit_store.count() == 1

    @pytest.mark.asyncio
    async def test_audit_mandate_id_linked(self):
        """Audit entry must be retrievable by mandate_id."""
        audit_store = _make_mock_audit_store()
        engine = ComplianceEngine(
            settings=MagicMock(),
            provider=_make_mock_provider(allowed=True),
            audit_store=audit_store,
        )
        mandate = _make_payment_mandate()
        await engine.preflight(mandate)
        entries = audit_store.get_by_mandate(mandate.mandate_id)
        assert len(entries) == 1
        assert entries[0].mandate_id == mandate.mandate_id


# ============ Router Source Inspection Tests ============


class TestComplianceInRouters:
    """Verify compliance.preflight() is present in all payment router sources."""

    def test_mandates_has_compliance(self):
        import inspect
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        assert "compliance" in source
        assert "preflight" in source

    def test_mvp_has_compliance(self):
        import inspect
        from sardis_api.routers import mvp
        source = inspect.getsource(mvp)
        assert "compliance" in source
        assert "preflight" in source

    def test_a2a_has_compliance_in_both_paths(self):
        import inspect
        from sardis_api.routers import a2a
        source = inspect.getsource(a2a)
        count = source.count("preflight")
        assert count >= 2, (
            f"Expected compliance.preflight in both /pay and /messages, found {count}"
        )

    def test_wallets_has_compliance(self):
        import inspect
        from sardis_api.routers import wallets
        source = inspect.getsource(wallets)
        assert "compliance" in source
        assert "preflight" in source

    def test_mandates_has_multiple_preflight_calls(self):
        import inspect
        from sardis_api.routers import mandates
        source = inspect.getsource(mandates)
        count = source.count("preflight")
        assert count >= 2, (
            f"Expected multiple compliance.preflight calls in mandates router, found {count}"
        )

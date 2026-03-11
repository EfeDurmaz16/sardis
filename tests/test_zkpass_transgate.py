"""Tests for zkPass Transgate integration.

Issue: #150
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from sardis_protocol.zkpass_transgate import (
    DEFAULT_PROOF_TTL_HOURS,
    IDENFY_COST_PER_VERIFICATION,
    KYC_LEVEL_MAPPING,
    SUPPORTED_PROOF_TYPES,
    ZKPASS_VERSION,
    PortableKYCResult,
    ProofStatus,
    TransgateConfig,
    TransgateIssuer,
    TransgateProofType,
    TransgateSchema,
    VerificationMethod,
    VerificationResult,
    ZKPassVerifier,
    ZKProof,
    build_register_schema_calldata,
    build_verify_proof_calldata,
    create_zkpass_verifier,
    hash_public_inputs,
)


# ============ TestTransgateSchema ============


class TestTransgateSchema:
    def test_creation(self):
        schema = TransgateSchema(
            schema_id="test_schema",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            required_fields=["kyc_status"],
            description="Test schema",
        )
        assert schema.schema_id == "test_schema"
        assert schema.proof_type == TransgateProofType.KYC_VERIFIED
        assert schema.issuer == TransgateIssuer.COINBASE
        assert schema.required_fields == ["kyc_status"]
        assert schema.description == "Test schema"
        assert schema.version == 1

    def test_fields(self):
        schema = TransgateSchema(
            schema_id="multi_field",
            proof_type=TransgateProofType.SANCTIONS_CLEAR,
            issuer=TransgateIssuer.GENERIC,
            required_fields=["screening_date", "result"],
            description="Sanctions check",
            version=2,
        )
        assert len(schema.required_fields) == 2
        assert schema.version == 2


# ============ TestZKProof ============


class TestZKProof:
    def test_creation(self):
        proof = ZKProof(
            proof_id="abc123",
            schema_id="coinbase_kyc",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            prover_address="0xabc",
            proof_data=b"\x01\x02\x03",
            public_inputs={"kyc_status": "verified"},
        )
        assert proof.proof_id == "abc123"
        assert proof.schema_id == "coinbase_kyc"
        assert proof.prover_address == "0xabc"
        assert proof.status == ProofStatus.PENDING

    def test_is_valid_verified_and_not_expired(self):
        proof = ZKProof(
            proof_id="valid1",
            schema_id="test",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={},
            status=ProofStatus.VERIFIED,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        assert proof.is_valid is True

    def test_is_valid_not_verified(self):
        proof = ZKProof(
            proof_id="pend1",
            schema_id="test",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={},
            status=ProofStatus.PENDING,
        )
        assert proof.is_valid is False

    def test_is_expired(self):
        proof = ZKProof(
            proof_id="exp1",
            schema_id="test",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={},
            status=ProofStatus.VERIFIED,
            expires_at=datetime.now(UTC) - timedelta(hours=1),
        )
        assert proof.is_expired is True
        assert proof.is_valid is False

    def test_not_expired_when_no_expiry(self):
        proof = ZKProof(
            proof_id="noexp",
            schema_id="test",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={},
            status=ProofStatus.VERIFIED,
            expires_at=None,
        )
        assert proof.is_expired is False
        assert proof.is_valid is True

    def test_default_status_is_pending(self):
        proof = ZKProof(
            proof_id="def1",
            schema_id="test",
            proof_type=TransgateProofType.AGE_VERIFIED,
            issuer=TransgateIssuer.GENERIC,
            prover_address="0x2",
            proof_data=b"\x01",
            public_inputs={},
        )
        assert proof.status == ProofStatus.PENDING


# ============ TestVerificationResult ============


class TestVerificationResult:
    def test_creation(self):
        result = VerificationResult(
            proof_id="res1",
            success=True,
            method=VerificationMethod.ZKPASS,
            issuer=TransgateIssuer.COINBASE,
            proof_type=TransgateProofType.KYC_VERIFIED,
            verified_at=datetime.now(UTC),
        )
        assert result.proof_id == "res1"
        assert result.success is True
        assert result.method == VerificationMethod.ZKPASS
        assert result.issuer == TransgateIssuer.COINBASE
        assert result.proof_type == TransgateProofType.KYC_VERIFIED

    def test_fields_with_details(self):
        result = VerificationResult(
            proof_id="res2",
            success=False,
            method=VerificationMethod.IDENFY,
            issuer=None,
            proof_type=None,
            verified_at=datetime.now(UTC),
            details={"reason": "test failure"},
        )
        assert result.details == {"reason": "test failure"}
        assert result.issuer is None
        assert result.proof_type is None


# ============ TestPortableKYCResult ============


class TestPortableKYCResult:
    def test_creation(self):
        vr = VerificationResult(
            proof_id="kyc1",
            success=True,
            method=VerificationMethod.ZKPASS,
            issuer=TransgateIssuer.COINBASE,
            proof_type=TransgateProofType.KYC_VERIFIED,
            verified_at=datetime.now(UTC),
        )
        result = PortableKYCResult(
            verification_result=vr,
            kyc_level="basic",
            accepted_proof_types=[TransgateProofType.KYC_VERIFIED],
        )
        assert result.kyc_level == "basic"
        assert result.verification_result.success is True

    def test_cost_savings(self):
        vr = VerificationResult(
            proof_id="kyc2",
            success=True,
            method=VerificationMethod.ZKPASS,
            issuer=TransgateIssuer.BINANCE,
            proof_type=TransgateProofType.KYC_VERIFIED,
            verified_at=datetime.now(UTC),
        )
        result = PortableKYCResult(
            verification_result=vr,
            kyc_level="basic",
            accepted_proof_types=[TransgateProofType.KYC_VERIFIED],
        )
        assert result.cost_savings_usd == 0.55

    def test_custom_cost_savings(self):
        vr = VerificationResult(
            proof_id="kyc3",
            success=False,
            method=VerificationMethod.ZKPASS,
            issuer=None,
            proof_type=None,
            verified_at=datetime.now(UTC),
        )
        result = PortableKYCResult(
            verification_result=vr,
            kyc_level="",
            accepted_proof_types=[],
            cost_savings_usd=0.0,
        )
        assert result.cost_savings_usd == 0.0


# ============ TestZKPassVerifier ============


class TestZKPassVerifier:
    """Tests for the ZKPassVerifier manager class."""

    # ---- Schema Management ----

    def test_register_schema(self):
        verifier = ZKPassVerifier()
        schema = TransgateSchema(
            schema_id="custom_schema",
            proof_type=TransgateProofType.BALANCE_VERIFIED,
            issuer=TransgateIssuer.KRAKEN,
            required_fields=["balance_usd"],
            description="Custom balance proof",
        )
        result = verifier.register_schema(schema)
        assert result.schema_id == "custom_schema"
        assert verifier.get_schema("custom_schema") is not None

    def test_get_schema(self):
        verifier = ZKPassVerifier()
        schema = verifier.get_schema("coinbase_kyc")
        assert schema is not None
        assert schema.proof_type == TransgateProofType.KYC_VERIFIED
        assert schema.issuer == TransgateIssuer.COINBASE

    def test_load_defaults_six_schemas(self):
        verifier = ZKPassVerifier()
        assert verifier.schema_count == 6

    def test_default_schema_ids(self):
        verifier = ZKPassVerifier()
        expected = {
            "coinbase_kyc", "binance_kyc", "age_verification",
            "country_check", "sanctions_screen", "accredited_check",
        }
        for sid in expected:
            assert verifier.get_schema(sid) is not None, f"Missing schema: {sid}"

    def test_duplicate_schema_raises(self):
        verifier = ZKPassVerifier()
        schema = TransgateSchema(
            schema_id="coinbase_kyc",
            proof_type=TransgateProofType.KYC_VERIFIED,
            issuer=TransgateIssuer.COINBASE,
            required_fields=["kyc_status"],
            description="Duplicate",
        )
        with pytest.raises(ValueError, match="already registered"):
            verifier.register_schema(schema)

    # ---- Proof Submission ----

    def test_submit_proof(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0xABC",
            proof_data=b"\x01\x02\x03",
            public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        assert proof.status == ProofStatus.PENDING
        assert proof.prover_address == "0xABC"
        assert proof.proof_type == TransgateProofType.KYC_VERIFIED
        assert proof.issuer == TransgateIssuer.COINBASE
        assert len(proof.proof_id) == 16

    def test_submit_proof_unknown_schema(self):
        verifier = ZKPassVerifier()
        with pytest.raises(ValueError, match="Schema not found"):
            verifier.submit_proof(
                schema_id="nonexistent",
                prover_address="0x1",
                proof_data=b"\x01",
                public_inputs={},
            )

    def test_get_proof(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "ok", "verification_date": "2026-01-01"},
        )
        fetched = verifier.get_proof(proof.proof_id)
        assert fetched is not None
        assert fetched.proof_id == proof.proof_id

    def test_get_proof_not_found(self):
        verifier = ZKPassVerifier()
        assert verifier.get_proof("nonexistent") is None

    def test_get_proofs_for_address(self):
        verifier = ZKPassVerifier()
        verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0xAA",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "ok", "verification_date": "2026-01-01"},
        )
        verifier.submit_proof(
            schema_id="binance_kyc",
            prover_address="0xAA",
            proof_data=b"\x02",
            public_inputs={"kyc_level": "2", "verification_date": "2026-01-01"},
        )
        verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0xBB",
            proof_data=b"\x03",
            public_inputs={"kyc_status": "ok", "verification_date": "2026-01-01"},
        )
        proofs = verifier.get_proofs_for_address("0xAA")
        assert len(proofs) == 2

    def test_get_valid_proofs_for_address(self):
        verifier = ZKPassVerifier()
        # Submit and verify one proof
        proof1 = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0xAA",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        verifier.verify_proof(proof1.proof_id)

        # Submit but don't verify another
        verifier.submit_proof(
            schema_id="binance_kyc",
            prover_address="0xAA",
            proof_data=b"\x02",
            public_inputs={"kyc_level": "2", "verification_date": "2026-01-01"},
        )

        valid = verifier.get_valid_proofs_for_address("0xAA")
        assert len(valid) == 1
        assert valid[0].proof_id == proof1.proof_id

    # ---- Verification ----

    def test_verify_successful(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01\x02",
            public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        result = verifier.verify_proof(proof.proof_id)
        assert result.success is True
        assert result.method == VerificationMethod.ZKPASS
        assert result.issuer == TransgateIssuer.COINBASE
        assert result.proof_type == TransgateProofType.KYC_VERIFIED

        # Proof should be marked verified
        updated = verifier.get_proof(proof.proof_id)
        assert updated is not None
        assert updated.status == ProofStatus.VERIFIED
        assert updated.verified_at is not None

    def test_verify_missing_fields_fails(self):
        verifier = ZKPassVerifier()
        # coinbase_kyc requires kyc_status and verification_date
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "verified"},  # missing verification_date
        )
        result = verifier.verify_proof(proof.proof_id)
        assert result.success is False
        assert "Missing required field" in result.details.get("reason", "")

    def test_verify_empty_proof_data_fails(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"",
            public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        result = verifier.verify_proof(proof.proof_id)
        assert result.success is False
        assert "Empty proof data" in result.details.get("reason", "")

    def test_verify_not_found_raises(self):
        verifier = ZKPassVerifier()
        with pytest.raises(ValueError, match="Proof not found"):
            verifier.verify_proof("nonexistent")

    # ---- Reject ----

    def test_reject_proof(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        rejected = verifier.reject_proof(proof.proof_id, reason="Suspicious data")
        assert rejected.status == ProofStatus.REJECTED

    def test_reject_not_found_raises(self):
        verifier = ZKPassVerifier()
        with pytest.raises(ValueError, match="Proof not found"):
            verifier.reject_proof("nonexistent")

    # ---- Portable KYC ----

    def _submit_and_verify(
        self,
        verifier: ZKPassVerifier,
        schema_id: str,
        address: str,
        public_inputs: dict[str, str],
    ) -> ZKProof:
        """Helper: submit and verify a proof."""
        proof = verifier.submit_proof(
            schema_id=schema_id,
            prover_address=address,
            proof_data=b"\x01\x02\x03",
            public_inputs=public_inputs,
        )
        verifier.verify_proof(proof.proof_id)
        return proof

    def test_portable_kyc_basic(self):
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "coinbase_kyc", "0xA",
            {"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        result = verifier.check_portable_kyc("0xA")
        assert result.kyc_level == "basic"
        assert result.verification_result.success is True
        assert result.cost_savings_usd == 0.55

    def test_portable_kyc_enhanced(self):
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "coinbase_kyc", "0xA",
            {"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        self._submit_and_verify(
            verifier, "country_check", "0xA",
            {"country_code": "US"},
        )
        result = verifier.check_portable_kyc("0xA")
        assert result.kyc_level == "enhanced"

    def test_portable_kyc_full(self):
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "coinbase_kyc", "0xA",
            {"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        self._submit_and_verify(
            verifier, "country_check", "0xA",
            {"country_code": "US"},
        )
        self._submit_and_verify(
            verifier, "sanctions_screen", "0xA",
            {"screening_date": "2026-01-01", "result": "clear"},
        )
        result = verifier.check_portable_kyc("0xA")
        assert result.kyc_level == "full"

    def test_portable_kyc_no_proofs(self):
        verifier = ZKPassVerifier()
        result = verifier.check_portable_kyc("0xNONE")
        assert result.kyc_level == ""
        assert result.verification_result.success is False
        assert result.cost_savings_usd == 0.0

    def test_portable_kyc_enhanced_with_sanctions_only(self):
        """KYC + SANCTIONS (no country) should be enhanced."""
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "coinbase_kyc", "0xA",
            {"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        self._submit_and_verify(
            verifier, "sanctions_screen", "0xA",
            {"screening_date": "2026-01-01", "result": "clear"},
        )
        result = verifier.check_portable_kyc("0xA")
        assert result.kyc_level == "enhanced"

    # ---- has_valid_kyc ----

    def test_has_valid_kyc_true(self):
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "coinbase_kyc", "0xA",
            {"kyc_status": "verified", "verification_date": "2026-01-01"},
        )
        assert verifier.has_valid_kyc("0xA") is True

    def test_has_valid_kyc_false(self):
        verifier = ZKPassVerifier()
        assert verifier.has_valid_kyc("0xNOBODY") is False

    def test_has_valid_kyc_false_not_kyc_type(self):
        """Age verification alone does not count as KYC."""
        verifier = ZKPassVerifier()
        self._submit_and_verify(
            verifier, "age_verification", "0xA",
            {"is_over_18": "true"},
        )
        assert verifier.has_valid_kyc("0xA") is False

    # ---- Properties ----

    def test_total_proofs(self):
        verifier = ZKPassVerifier()
        assert verifier.total_proofs == 0
        verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "ok", "verification_date": "2026-01-01"},
        )
        assert verifier.total_proofs == 1

    def test_verified_proofs(self):
        verifier = ZKPassVerifier()
        proof = verifier.submit_proof(
            schema_id="coinbase_kyc",
            prover_address="0x1",
            proof_data=b"\x01",
            public_inputs={"kyc_status": "ok", "verification_date": "2026-01-01"},
        )
        assert verifier.verified_proofs == 0
        verifier.verify_proof(proof.proof_id)
        assert verifier.verified_proofs == 1

    def test_schema_count(self):
        verifier = ZKPassVerifier()
        assert verifier.schema_count == 6
        verifier.register_schema(TransgateSchema(
            schema_id="extra",
            proof_type=TransgateProofType.BALANCE_VERIFIED,
            issuer=TransgateIssuer.OKX,
            required_fields=["balance"],
            description="Extra schema",
        ))
        assert verifier.schema_count == 7


# ============ TestCalldata ============


class TestCalldata:
    def test_verify_proof_calldata(self):
        calldata = build_verify_proof_calldata(
            proof_id="abc123",
            proof_data=b"\x01\x02\x03",
            public_inputs_hash=b"\xff" * 32,
        )
        assert calldata[:4] == bytes.fromhex("e1a2b3c4")
        assert len(calldata) > 4

    def test_register_schema_calldata(self):
        calldata = build_register_schema_calldata(
            schema_id="coinbase_kyc",
            proof_type="kyc_verified",
            issuer="coinbase",
        )
        assert calldata[:4] == bytes.fromhex("f2b3c4d5")
        assert len(calldata) > 4


# ============ TestEnums ============


class TestEnums:
    def test_transgate_proof_type_values(self):
        assert len(TransgateProofType) == 6
        assert TransgateProofType.KYC_VERIFIED.value == "kyc_verified"
        assert TransgateProofType.AGE_VERIFIED.value == "age_verified"
        assert TransgateProofType.COUNTRY_VERIFIED.value == "country_verified"
        assert TransgateProofType.BALANCE_VERIFIED.value == "balance_verified"
        assert TransgateProofType.ACCREDITED_INVESTOR.value == "accredited_investor"
        assert TransgateProofType.SANCTIONS_CLEAR.value == "sanctions_clear"

    def test_transgate_issuer_values(self):
        assert len(TransgateIssuer) == 6
        assert TransgateIssuer.COINBASE.value == "coinbase"
        assert TransgateIssuer.BINANCE.value == "binance"
        assert TransgateIssuer.KRAKEN.value == "kraken"
        assert TransgateIssuer.OKX.value == "okx"
        assert TransgateIssuer.BYBIT.value == "bybit"
        assert TransgateIssuer.GENERIC.value == "generic"

    def test_proof_status_values(self):
        assert len(ProofStatus) == 4
        assert ProofStatus.PENDING.value == "pending"
        assert ProofStatus.VERIFIED.value == "verified"
        assert ProofStatus.REJECTED.value == "rejected"
        assert ProofStatus.EXPIRED.value == "expired"

    def test_verification_method_values(self):
        assert len(VerificationMethod) == 4
        assert VerificationMethod.IDENFY.value == "idenfy"
        assert VerificationMethod.ZKPASS.value == "zkpass"
        assert VerificationMethod.PRIVADO_ID.value == "privado_id"
        assert VerificationMethod.MANUAL.value == "manual"


# ============ TestConstants ============


class TestConstants:
    def test_zkpass_version(self):
        assert ZKPASS_VERSION == "0.1.0"

    def test_default_proof_ttl(self):
        assert DEFAULT_PROOF_TTL_HOURS == 720

    def test_idenfy_cost(self):
        assert IDENFY_COST_PER_VERIFICATION == 0.55

    def test_supported_proof_types(self):
        assert isinstance(SUPPORTED_PROOF_TYPES, frozenset)
        assert len(SUPPORTED_PROOF_TYPES) == 6
        assert "kyc_verified" in SUPPORTED_PROOF_TYPES
        assert "sanctions_clear" in SUPPORTED_PROOF_TYPES

    def test_kyc_level_mapping(self):
        assert KYC_LEVEL_MAPPING[frozenset({"kyc_verified"})] == "basic"
        assert KYC_LEVEL_MAPPING[frozenset({"kyc_verified", "country_verified"})] == "enhanced"
        assert KYC_LEVEL_MAPPING[frozenset({"kyc_verified", "country_verified", "sanctions_clear"})] == "full"


# ============ TestFactory ============


class TestFactory:
    def test_create_zkpass_verifier_default(self):
        verifier = create_zkpass_verifier()
        assert isinstance(verifier, ZKPassVerifier)
        assert verifier.schema_count == 6

    def test_create_zkpass_verifier_with_args(self):
        verifier = create_zkpass_verifier(app_id="myapp", api_key="mykey")
        assert isinstance(verifier, ZKPassVerifier)
        assert verifier._config.app_id == "myapp"
        assert verifier._config.api_key == "mykey"


# ============ TestHashPublicInputs ============


class TestHashPublicInputs:
    def test_deterministic(self):
        inputs = {"kyc_status": "verified", "date": "2026-01-01"}
        h1 = hash_public_inputs(inputs)
        h2 = hash_public_inputs(inputs)
        assert h1 == h2

    def test_different_inputs_different_hash(self):
        h1 = hash_public_inputs({"a": "1"})
        h2 = hash_public_inputs({"a": "2"})
        assert h1 != h2

    def test_order_independent(self):
        h1 = hash_public_inputs({"b": "2", "a": "1"})
        h2 = hash_public_inputs({"a": "1", "b": "2"})
        assert h1 == h2

    def test_returns_32_bytes(self):
        h = hash_public_inputs({"x": "y"})
        assert len(h) == 32


# ============ TestModuleExports ============


class TestModuleExports:
    def test_import_from_sardis_protocol(self):
        from sardis_protocol import (
            ZKPassVerifier,
            TransgateProofType,
            TransgateIssuer,
            TransgateSchema,
            ZKProof,
            ProofStatus,
            VerificationMethod,
            ZKPassVerificationResult,
            PortableKYCResult,
            TransgateConfig,
            create_zkpass_verifier,
            hash_public_inputs,
        )
        # All imports should succeed
        assert ZKPassVerifier is not None
        assert TransgateProofType is not None
        assert TransgateIssuer is not None
        assert TransgateSchema is not None
        assert ZKProof is not None
        assert ProofStatus is not None
        assert VerificationMethod is not None
        assert ZKPassVerificationResult is not None
        assert PortableKYCResult is not None
        assert TransgateConfig is not None
        assert create_zkpass_verifier is not None
        assert hash_public_inputs is not None

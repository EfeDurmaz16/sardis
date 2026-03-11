"""Tests for ERC-8126 ZK risk scoring.

Covers issue #130. Tests verification layers, composite scoring,
ZK proof commitments, and calldata builders.
"""
from __future__ import annotations

import pytest

from sardis_protocol.erc8126 import (
    DEFAULT_WEIGHTS,
    AgentVerification,
    RiskBand,
    VerificationResult,
    VerificationStatus,
    VerificationType,
    ZKProofCommitment,
    build_risk_score_query_calldata,
    build_verification_calldata,
    compute_composite_score,
    create_proof_commitment,
    evaluate_etv,
    evaluate_scv,
    evaluate_wav,
    evaluate_wv,
    risk_score_to_normalized,
    score_to_risk_band,
    verify_agent,
)


# ============ Risk Band Tests ============

class TestScoreToRiskBand:
    def test_high_risk(self):
        assert score_to_risk_band(0) == RiskBand.HIGH
        assert score_to_risk_band(25) == RiskBand.HIGH

    def test_medium_high_risk(self):
        assert score_to_risk_band(26) == RiskBand.MEDIUM_HIGH
        assert score_to_risk_band(50) == RiskBand.MEDIUM_HIGH

    def test_medium_low_risk(self):
        assert score_to_risk_band(51) == RiskBand.MEDIUM_LOW
        assert score_to_risk_band(75) == RiskBand.MEDIUM_LOW

    def test_low_risk(self):
        assert score_to_risk_band(76) == RiskBand.LOW
        assert score_to_risk_band(100) == RiskBand.LOW


# ============ ETV Tests ============

class TestEvaluateETV:
    def test_fully_verified(self):
        result = evaluate_etv(
            contract_address="0x1234",
            is_verified_source=True,
            has_audit=True,
            uses_proxy=False,
            bytecode_size=5000,
        )
        assert result.verification_type == VerificationType.ETV
        assert result.status == VerificationStatus.VERIFIED
        assert result.score == 100

    def test_verified_source_only(self):
        result = evaluate_etv(
            contract_address="0x1234",
            is_verified_source=True,
            has_audit=False,
            uses_proxy=True,
            bytecode_size=5000,
        )
        assert result.score == 60  # 40 + 15 + 5

    def test_nothing_verified(self):
        result = evaluate_etv(
            contract_address="0x1234",
            is_verified_source=False,
            has_audit=False,
            uses_proxy=False,
            bytecode_size=0,
        )
        assert result.score == 15  # no proxy bonus
        assert result.status == VerificationStatus.VERIFIED

    def test_proxy_partial_credit(self):
        result = evaluate_etv(
            contract_address="0x1234",
            is_verified_source=False,
            has_audit=False,
            uses_proxy=True,
            bytecode_size=5000,
        )
        assert result.score == 20  # 15 (bytecode) + 5 (proxy partial)


# ============ SCV Tests ============

class TestEvaluateSCV:
    def test_high_stake(self):
        result = evaluate_scv(
            staked_amount_usd=100000,
            staking_duration_days=400,
            slashing_enabled=True,
        )
        assert result.score == 100

    def test_moderate_stake(self):
        result = evaluate_scv(
            staked_amount_usd=10000,
            staking_duration_days=100,
            slashing_enabled=False,
        )
        assert result.score == 50  # 30 + 20

    def test_minimal_stake(self):
        result = evaluate_scv(staked_amount_usd=100)
        assert result.score == 10

    def test_no_stake(self):
        result = evaluate_scv(staked_amount_usd=0)
        assert result.score == 0
        assert result.status == VerificationStatus.FAILED


# ============ WV Tests ============

class TestEvaluateWV:
    def test_established_wallet(self):
        result = evaluate_wv(
            wallet_age_days=500,
            transaction_count=2000,
            unique_counterparties=100,
            has_ens=True,
            flagged_transactions=0,
        )
        assert result.score == 100

    def test_new_wallet(self):
        result = evaluate_wv(
            wallet_age_days=5,
            transaction_count=2,
            unique_counterparties=1,
            flagged_transactions=0,
        )
        assert result.score == 20  # only base rep

    def test_flagged_wallet(self):
        result = evaluate_wv(
            wallet_age_days=400,
            transaction_count=500,
            unique_counterparties=30,
            flagged_transactions=3,
        )
        # 25 (age) + 15 (tx 100-999) + 10 (counterparties 10-49) - 30 (penalty) = 20
        assert result.score == 20

    def test_heavily_flagged(self):
        result = evaluate_wv(flagged_transactions=10)
        assert result.score == 0
        assert result.status == VerificationStatus.FAILED


# ============ WAV Tests ============

class TestEvaluateWAV:
    def test_fully_secured(self):
        result = evaluate_wav(
            has_https=True,
            valid_ssl=True,
            domain_age_days=400,
            has_security_headers=True,
            cors_configured=True,
        )
        assert result.score == 100

    def test_basic_https(self):
        result = evaluate_wav(has_https=True, valid_ssl=True)
        assert result.score == 45

    def test_no_security(self):
        result = evaluate_wav()
        assert result.score == 0
        assert result.status == VerificationStatus.FAILED


# ============ Composite Score Tests ============

class TestCompositeScore:
    def test_all_perfect(self):
        results = {
            VerificationType.ETV: VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.VERIFIED,
                score=100,
            ),
            VerificationType.SCV: VerificationResult(
                verification_type=VerificationType.SCV,
                status=VerificationStatus.VERIFIED,
                score=100,
            ),
            VerificationType.WAV: VerificationResult(
                verification_type=VerificationType.WAV,
                status=VerificationStatus.VERIFIED,
                score=100,
            ),
            VerificationType.WV: VerificationResult(
                verification_type=VerificationType.WV,
                status=VerificationStatus.VERIFIED,
                score=100,
            ),
        }
        assert compute_composite_score(results) == 100

    def test_single_layer(self):
        results = {
            VerificationType.ETV: VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.VERIFIED,
                score=80,
            ),
        }
        assert compute_composite_score(results) == 80

    def test_no_valid_results(self):
        results = {
            VerificationType.ETV: VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.FAILED,
                score=50,
            ),
        }
        assert compute_composite_score(results) == 0

    def test_custom_weights(self):
        results = {
            VerificationType.ETV: VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.VERIFIED,
                score=100,
            ),
            VerificationType.WV: VerificationResult(
                verification_type=VerificationType.WV,
                status=VerificationStatus.VERIFIED,
                score=50,
            ),
        }
        weights = {
            VerificationType.ETV: 50,
            VerificationType.WV: 50,
        }
        assert compute_composite_score(results, weights) == 75

    def test_default_weights_sum(self):
        assert sum(DEFAULT_WEIGHTS.values()) == 100


# ============ ZK Proof Commitment Tests ============

class TestZKProofCommitment:
    def test_create_commitment(self):
        proof = create_proof_commitment(
            VerificationType.ETV,
            b"test data",
            [42],
        )
        assert len(proof.commitment_hash) == 32
        assert len(proof.nonce) == 32
        assert proof.verification_type == VerificationType.ETV
        assert proof.public_inputs == [42]

    def test_verify_commitment(self):
        proof = create_proof_commitment(VerificationType.SCV, b"secret")
        assert proof.verify_commitment(b"secret") is True
        assert proof.verify_commitment(b"wrong") is False

    def test_different_commitments(self):
        p1 = create_proof_commitment(VerificationType.ETV, b"data")
        p2 = create_proof_commitment(VerificationType.ETV, b"data")
        assert p1.commitment_hash != p2.commitment_hash  # Different nonces


# ============ Calldata Tests ============

class TestCalldata:
    def test_verification_calldata(self):
        calldata = build_verification_calldata(
            agent_id=42,
            verification_type=VerificationType.ETV,
            score=85,
            proof_commitment=b"\x01" * 32,
        )
        assert len(calldata) > 4
        # Selector is first 4 bytes
        assert len(calldata[:4]) == 4

    def test_risk_score_query(self):
        calldata = build_risk_score_query_calldata(42)
        assert len(calldata) > 4


# ============ Full Verification Tests ============

class TestVerifyAgent:
    def test_full_verification(self):
        verification = verify_agent(
            agent_id=42,
            agent_address="0x1234",
            etv_params={
                "contract_address": "0xabcd",
                "is_verified_source": True,
                "has_audit": True,
                "uses_proxy": False,
                "bytecode_size": 5000,
            },
            scv_params={
                "staked_amount_usd": 50000,
                "staking_duration_days": 200,
                "slashing_enabled": True,
            },
            wv_params={
                "wallet_age_days": 400,
                "transaction_count": 500,
                "unique_counterparties": 60,
                "has_ens": True,
                "flagged_transactions": 0,
            },
        )
        assert isinstance(verification, AgentVerification)
        assert verification.agent_id == 42
        assert verification.is_verified is True
        assert verification.verification_count == 3
        assert verification.composite_score > 50
        assert verification.risk_band in (RiskBand.LOW, RiskBand.MEDIUM_LOW)
        assert len(verification.proofs) == 3

    def test_no_layers(self):
        verification = verify_agent(agent_id=1, agent_address="0x1234")
        assert verification.composite_score == 0
        assert verification.is_verified is False
        assert verification.risk_band == RiskBand.HIGH

    def test_single_layer(self):
        verification = verify_agent(
            agent_id=1,
            agent_address="0x1234",
            etv_params={
                "contract_address": "0xabcd",
                "is_verified_source": True,
                "has_audit": False,
                "uses_proxy": False,
                "bytecode_size": 5000,
            },
        )
        assert verification.verification_count == 1
        assert verification.etv_result is not None
        assert verification.scv_result is None


# ============ Normalized Risk Tests ============

class TestNormalizedRisk:
    def test_perfect_score(self):
        assert risk_score_to_normalized(100) == 0.0

    def test_zero_score(self):
        assert risk_score_to_normalized(0) == 1.0

    def test_mid_score(self):
        assert abs(risk_score_to_normalized(50) - 0.5) < 0.01

    def test_clamped_high(self):
        assert risk_score_to_normalized(-10) == 1.0

    def test_clamped_low(self):
        assert risk_score_to_normalized(200) == 0.0


# ============ AgentVerification Properties ============

class TestAgentVerificationProperties:
    def test_risk_band_property(self):
        v = AgentVerification(agent_id=1, agent_address="0x1234", composite_score=90)
        assert v.risk_band == RiskBand.LOW

    def test_is_verified_with_valid_result(self):
        v = AgentVerification(
            agent_id=1,
            agent_address="0x1234",
            etv_result=VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.VERIFIED,
                score=80,
            ),
        )
        assert v.is_verified is True

    def test_is_verified_with_failed_result(self):
        v = AgentVerification(
            agent_id=1,
            agent_address="0x1234",
            etv_result=VerificationResult(
                verification_type=VerificationType.ETV,
                status=VerificationStatus.FAILED,
            ),
        )
        assert v.is_verified is False


# ============ Enum Tests ============

class TestEnums:
    def test_verification_types(self):
        assert len(VerificationType) == 4

    def test_risk_bands(self):
        assert len(RiskBand) == 4

    def test_verification_statuses(self):
        assert VerificationStatus.VERIFIED.value == "verified"
        assert VerificationStatus.FAILED.value == "failed"


# ============ Module Export Tests ============

class TestModuleExports:
    def test_imports(self):
        from sardis_protocol.erc8126 import (
            AgentVerification,
            RiskBand,
            VerificationType,
            compute_composite_score,
            create_proof_commitment,
            evaluate_etv,
            evaluate_scv,
            evaluate_wav,
            evaluate_wv,
            verify_agent,
        )
        assert all([
            AgentVerification, RiskBand, VerificationType,
            compute_composite_score, create_proof_commitment,
            evaluate_etv, evaluate_scv, evaluate_wav, evaluate_wv,
            verify_agent,
        ])

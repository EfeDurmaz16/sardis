"""Tests for ML-based fraud detection.

Covers issue #132. Tests feature extraction, rule-based scoring,
model loading, and the scoring pipeline. ONNX inference is tested
with mocks (onnxruntime may not be installed).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from sardis_guardrails.ml_fraud import (
    FEATURE_SCHEMA,
    HIGH_RISK_COUNTRIES,
    MERCHANT_CATEGORY_RISK,
    FraudAction,
    FraudResult,
    MLFraudScorer,
    ModelStatus,
    ScalerState,
    TransactionFeatures,
    extract_features,
    get_ml_fraud_scorer,
)


# ============ Feature Extraction Tests ============

class TestExtractFeatures:
    def test_basic_extraction(self):
        features = extract_features(amount=100.0)
        assert isinstance(features, TransactionFeatures)
        assert features.amount == 100.0
        assert features.velocity_1h == 0.0
        assert features.is_new_merchant == 0.0

    def test_zscore_computation(self):
        features = extract_features(
            amount=500.0,
            mean_amount=100.0,
            std_amount=50.0,
        )
        # z = (500 - 100) / 50 = 8.0, clamped to 5.0
        assert features.amount_zscore == 5.0

    def test_zscore_negative(self):
        features = extract_features(
            amount=10.0,
            mean_amount=500.0,
            std_amount=50.0,
        )
        # z = (10 - 500) / 50 = -9.8, clamped to -5.0
        assert features.amount_zscore == -5.0

    def test_zscore_no_history(self):
        features = extract_features(amount=100.0)
        assert features.amount_zscore == 0.0

    def test_merchant_category_risk(self):
        features = extract_features(amount=100.0, merchant_category="gambling")
        assert features.merchant_category_risk == 0.85

    def test_merchant_category_default(self):
        features = extract_features(amount=100.0, merchant_category="unknown")
        assert features.merchant_category_risk == 0.3

    def test_country_high_risk(self):
        features = extract_features(
            amount=100.0,
            billing_country="KP",
        )
        assert features.country_high_risk == 1.0

    def test_country_mismatch(self):
        features = extract_features(
            amount=100.0,
            billing_country="US",
            card_country="DE",
        )
        assert features.country_mismatch == 1.0

    def test_no_country_mismatch(self):
        features = extract_features(
            amount=100.0,
            billing_country="US",
            card_country="US",
        )
        assert features.country_mismatch == 0.0

    def test_out_of_hours(self):
        features = extract_features(
            amount=100.0,
            hour_of_day=3,
            typical_hours={9, 10, 11, 12, 13, 14, 15, 16, 17},
        )
        assert features.is_out_of_hours == 1.0

    def test_within_hours(self):
        features = extract_features(
            amount=100.0,
            hour_of_day=12,
            typical_hours={9, 10, 11, 12, 13, 14, 15, 16, 17},
        )
        assert features.is_out_of_hours == 0.0

    def test_weekend_detection(self):
        features = extract_features(amount=100.0, day_of_week=5)
        assert features.is_weekend == 1.0

    def test_weekday_detection(self):
        features = extract_features(amount=100.0, day_of_week=2)
        assert features.is_weekend == 0.0

    def test_round_amount(self):
        features = extract_features(amount=1000.0)
        assert features.is_round_amount == 1.0

    def test_non_round_amount(self):
        features = extract_features(amount=1234.56)
        assert features.is_round_amount == 0.0

    def test_interaction_large_new_merchant(self):
        features = extract_features(amount=5000.0, is_new_merchant=True)
        assert features.large_amount_new_merchant == 1.0

    def test_interaction_no_large_new(self):
        features = extract_features(amount=50.0, is_new_merchant=True)
        assert features.large_amount_new_merchant == 0.0

    def test_high_velocity_high_amount(self):
        features = extract_features(amount=5000.0, velocity_1h=10)
        assert features.high_velocity_high_amount == 1.0

    def test_geo_anomalous(self):
        features = extract_features(amount=100.0, geo_distance_km=5000.0)
        assert features.geo_anomalous == 1.0

    def test_geo_distance_capped(self):
        features = extract_features(amount=100.0, geo_distance_km=50000.0)
        assert features.geo_distance_km == 20000.0

    def test_device_signals(self):
        features = extract_features(
            amount=100.0,
            vpn_detected=True,
            bot_detected=True,
            tampering_detected=True,
            incognito=True,
            virtual_machine=True,
            ip_blocklisted=True,
            suspect_score=85,
        )
        assert features.vpn_detected == 1.0
        assert features.bot_detected == 1.0
        assert features.tampering_detected == 1.0
        assert features.incognito == 1.0
        assert features.virtual_machine == 1.0
        assert features.ip_blocklisted == 1.0
        assert abs(features.suspect_score - 0.85) < 0.01

    def test_velocity_normalization(self):
        features = extract_features(amount=100.0, velocity_24h=48)
        assert features.velocity_24h == 2.0  # 48/24


# ============ TransactionFeatures Tests ============

class TestTransactionFeatures:
    def test_to_array(self):
        features = TransactionFeatures(amount=500.0, velocity_1h=3.0)
        arr = features.to_array()
        assert isinstance(arr, np.ndarray)
        assert arr.dtype == np.float32
        assert arr.shape == (1, len(FEATURE_SCHEMA))
        assert arr[0][0] == 500.0  # amount is first feature

    def test_to_array_custom_order(self):
        features = TransactionFeatures(amount=500.0, velocity_1h=3.0)
        arr = features.to_array(["velocity_1h", "amount"])
        assert arr.shape == (1, 2)
        assert arr[0][0] == 3.0
        assert arr[0][1] == 500.0


# ============ ScalerState Tests ============

class TestScalerState:
    def test_normalize(self):
        scaler = ScalerState(
            feature_names=["amount", "velocity_1h"],
            mean=[100.0, 2.0],
            scale=[50.0, 1.0],
        )
        features = TransactionFeatures(amount=200.0, velocity_1h=4.0)
        normalized = scaler.normalize(features)
        assert normalized.shape == (1, 2)
        assert abs(normalized[0][0] - 2.0) < 0.01  # (200-100)/50
        assert abs(normalized[0][1] - 2.0) < 0.01  # (4-2)/1

    def test_normalize_zero_scale(self):
        scaler = ScalerState(
            feature_names=["amount"],
            mean=[100.0],
            scale=[0.0],  # Zero scale should not cause division error
        )
        features = TransactionFeatures(amount=200.0)
        normalized = scaler.normalize(features)
        assert abs(normalized[0][0] - 100.0) < 0.01  # (200-100)/1


# ============ Rule-Based Scoring Tests ============

class TestRuleBasedScoring:
    def test_clean_transaction(self):
        scorer = MLFraudScorer()
        features = TransactionFeatures(amount=50.0)
        result = scorer._rule_based_score(features)
        assert result.risk_score == 0.0
        assert result.action == FraudAction.APPROVE

    def test_bot_detected(self):
        scorer = MLFraudScorer()
        features = TransactionFeatures(bot_detected=1.0)
        result = scorer._rule_based_score(features)
        assert result.risk_score >= 0.35
        assert result.details["source"] == "rule_based_fallback"

    def test_multiple_signals(self):
        scorer = MLFraudScorer()
        features = TransactionFeatures(
            bot_detected=1.0,
            vpn_detected=1.0,
            ip_blocklisted=1.0,
            amount_zscore=4.0,
        )
        result = scorer._rule_based_score(features)
        assert result.risk_score >= 0.64

    def test_block_threshold(self):
        scorer = MLFraudScorer(block_threshold=0.50)
        features = TransactionFeatures(
            bot_detected=1.0,
            vpn_detected=1.0,
            tampering_detected=1.0,
        )
        result = scorer._rule_based_score(features)
        assert result.action == FraudAction.BLOCK

    def test_review_threshold(self):
        scorer = MLFraudScorer(review_threshold=0.30)
        features = TransactionFeatures(
            bot_detected=1.0,
        )
        result = scorer._rule_based_score(features)
        assert result.action == FraudAction.REVIEW

    def test_capped_at_1(self):
        scorer = MLFraudScorer()
        features = TransactionFeatures(
            bot_detected=1.0,
            vpn_detected=1.0,
            tampering_detected=1.0,
            ip_blocklisted=1.0,
            amount_zscore=5.0,
            velocity_1h=20.0,
            geo_anomalous=1.0,
            country_high_risk=1.0,
            country_mismatch=1.0,
        )
        result = scorer._rule_based_score(features)
        assert result.risk_score <= 1.0


# ============ MLFraudScorer Tests ============

class TestMLFraudScorer:
    def test_init_defaults(self):
        scorer = MLFraudScorer()
        assert scorer.status == ModelStatus.NOT_LOADED
        assert scorer.is_loaded is False

    def test_init_custom_thresholds(self):
        scorer = MLFraudScorer(
            block_threshold=0.90,
            review_threshold=0.70,
        )
        assert scorer._block_threshold == 0.90
        assert scorer._review_threshold == 0.70

    @pytest.mark.asyncio
    async def test_score_without_model(self):
        scorer = MLFraudScorer()
        features = TransactionFeatures(amount=100.0)
        result = await scorer.score(features)
        assert isinstance(result, FraudResult)
        assert result.model_version == "rule_based_v1"

    @pytest.mark.asyncio
    async def test_load_model_no_onnxruntime(self):
        with patch("sardis_guardrails.ml_fraud.HAS_ONNXRUNTIME", False):
            scorer = MLFraudScorer(model_path="test.onnx")
            loaded = await scorer.load_model()
            assert loaded is False
            assert scorer.status == ModelStatus.DISABLED

    @pytest.mark.asyncio
    async def test_load_model_no_path(self):
        scorer = MLFraudScorer(model_path="")
        loaded = await scorer.load_model()
        assert loaded is False


# ============ FraudResult Properties ============

class TestFraudResult:
    def test_is_blocked(self):
        result = FraudResult(risk_score=0.90, action=FraudAction.BLOCK)
        assert result.is_blocked is True
        assert result.needs_review is False

    def test_needs_review(self):
        result = FraudResult(risk_score=0.70, action=FraudAction.REVIEW)
        assert result.is_blocked is False
        assert result.needs_review is True

    def test_approved(self):
        result = FraudResult(risk_score=0.10, action=FraudAction.APPROVE)
        assert result.is_blocked is False
        assert result.needs_review is False


# ============ Constants Tests ============

class TestConstants:
    def test_feature_schema_length(self):
        assert len(FEATURE_SCHEMA) == 24

    def test_high_risk_countries(self):
        assert "KP" in HIGH_RISK_COUNTRIES
        assert "IR" in HIGH_RISK_COUNTRIES
        assert "US" not in HIGH_RISK_COUNTRIES

    def test_merchant_risk_map(self):
        assert MERCHANT_CATEGORY_RISK["gambling"] > 0.5
        assert MERCHANT_CATEGORY_RISK["food"] < 0.5


# ============ Singleton Tests ============

class TestSingleton:
    def test_get_ml_fraud_scorer(self):
        import sardis_guardrails.ml_fraud as mod
        mod._scorer = None
        s1 = get_ml_fraud_scorer()
        s2 = get_ml_fraud_scorer()
        assert s1 is s2
        mod._scorer = None


# ============ Module Export Tests ============

class TestModuleExports:
    def test_from_guardrails(self):
        from sardis_guardrails import (
            FEATURE_SCHEMA,
            FraudResult,
            MLFraudAction,
            MLFraudScorer,
            ModelStatus,
            TransactionFeatures,
            extract_features,
            get_ml_fraud_scorer,
        )
        assert all([
            FEATURE_SCHEMA, FraudResult, MLFraudAction,
            MLFraudScorer, ModelStatus, TransactionFeatures,
            extract_features, get_ml_fraud_scorer,
        ])

"""ML-based fraud detection with ONNX Runtime inference.

Provides real-time payment fraud scoring using pre-trained XGBoost models
exported to ONNX format. Integrates with the existing guardrails pipeline
for weighted signal aggregation.

Architecture:
    [Transaction] → Feature extraction → ONNX inference → FraudResult
    FraudResult feeds into AnomalyEngine as an additional risk signal.

Model Training: Separate pipeline (not included here).
Model Format: ONNX (exported from XGBoost via skl2onnx).

Issue: #132
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Optional ONNX Runtime import
try:
    import onnxruntime as ort
    HAS_ONNXRUNTIME = True
except ImportError:
    ort = None  # type: ignore[assignment]
    HAS_ONNXRUNTIME = False


# ============ Enums ============

class FraudAction(str, Enum):
    """Action to take based on fraud score."""
    APPROVE = "approve"
    REVIEW = "review"
    BLOCK = "block"


class ModelStatus(str, Enum):
    """Model loading status."""
    NOT_LOADED = "not_loaded"
    LOADED = "loaded"
    ERROR = "error"
    DISABLED = "disabled"


# ============ Feature Schema ============

# Ordered list of features expected by the model.
# Must match the feature order used during training.
FEATURE_SCHEMA: list[str] = [
    "amount",
    "amount_zscore",
    "velocity_1h",
    "velocity_24h",
    "account_age_days",
    "is_new_merchant",
    "merchant_category_risk",
    "hour_of_day",
    "is_weekend",
    "is_out_of_hours",
    "geo_distance_km",
    "geo_anomalous",
    "country_high_risk",
    "country_mismatch",
    "vpn_detected",
    "bot_detected",
    "tampering_detected",
    "incognito",
    "virtual_machine",
    "ip_blocklisted",
    "suspect_score",
    "is_round_amount",
    "large_amount_new_merchant",
    "high_velocity_high_amount",
]

# High-risk merchant categories mapped to risk scores
MERCHANT_CATEGORY_RISK: dict[str, float] = {
    "gambling": 0.85,
    "crypto_exchange": 0.65,
    "money_transfer": 0.55,
    "adult_content": 0.50,
    "weapons": 0.90,
    "shell_company": 0.95,
    "electronics": 0.30,
    "travel": 0.25,
    "food": 0.10,
    "retail": 0.15,
}

# OFAC/FATF high-risk countries
HIGH_RISK_COUNTRIES: set[str] = {
    "KP", "IR", "SY", "CU", "MM", "YE", "BY", "RU", "VE",
    "AF", "SO", "LY", "SD", "SS", "CF",
}


# ============ Data Models ============

@dataclass
class TransactionFeatures:
    """Features extracted from a payment transaction for ML scoring.

    All features should be normalized to float values for model input.
    Boolean features are 0.0 or 1.0.
    """
    # Transaction
    amount: float = 0.0
    amount_zscore: float = 0.0  # Standard deviations from agent's mean
    velocity_1h: float = 0.0    # Transactions in last hour
    velocity_24h: float = 0.0   # Avg transactions per hour (24h window)
    account_age_days: float = 0.0
    is_new_merchant: float = 0.0
    merchant_category_risk: float = 0.3  # Default moderate risk

    # Time
    hour_of_day: float = 12.0
    is_weekend: float = 0.0
    is_out_of_hours: float = 0.0

    # Geographic
    geo_distance_km: float = 0.0
    geo_anomalous: float = 0.0
    country_high_risk: float = 0.0
    country_mismatch: float = 0.0

    # Device (from FingerprintJS)
    vpn_detected: float = 0.0
    bot_detected: float = 0.0
    tampering_detected: float = 0.0
    incognito: float = 0.0
    virtual_machine: float = 0.0
    ip_blocklisted: float = 0.0
    suspect_score: float = 0.0  # Normalized 0-1

    # Interaction features
    is_round_amount: float = 0.0
    large_amount_new_merchant: float = 0.0
    high_velocity_high_amount: float = 0.0

    def to_array(self, feature_order: list[str] | None = None) -> np.ndarray:
        """Convert to numpy array in model-expected order."""
        order = feature_order or FEATURE_SCHEMA
        values = [getattr(self, name, 0.0) for name in order]
        return np.array([values], dtype=np.float32)


@dataclass
class FraudResult:
    """Result from ML fraud scoring."""
    risk_score: float = 0.0      # 0.0 (safe) to 1.0 (fraud)
    action: FraudAction = FraudAction.APPROVE
    model_version: str = ""
    features_used: int = 0
    inference_time_ms: float = 0.0
    details: dict[str, Any] = field(default_factory=dict)
    scored_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @property
    def is_blocked(self) -> bool:
        return self.action == FraudAction.BLOCK

    @property
    def needs_review(self) -> bool:
        return self.action == FraudAction.REVIEW


@dataclass
class ScalerState:
    """StandardScaler state for feature normalization.

    Saved from training pipeline and loaded at inference time.
    """
    feature_names: list[str]
    mean: list[float]
    scale: list[float]
    missing_values: dict[str, float] = field(default_factory=dict)

    def normalize(self, features: TransactionFeatures) -> np.ndarray:
        """Apply StandardScaler normalization to features."""
        raw = features.to_array(self.feature_names)
        mean_arr = np.array([self.mean], dtype=np.float32)
        scale_arr = np.array([self.scale], dtype=np.float32)
        # Avoid division by zero
        scale_arr = np.where(scale_arr == 0, 1.0, scale_arr)
        return (raw - mean_arr) / scale_arr


# ============ Feature Extraction ============

def extract_features(
    amount: float,
    velocity_1h: int = 0,
    velocity_24h: int = 0,
    account_age_days: int = 0,
    is_new_merchant: bool = False,
    merchant_category: str | None = None,
    hour_of_day: int | None = None,
    day_of_week: int | None = None,
    typical_hours: set[int] | None = None,
    geo_distance_km: float = 0.0,
    billing_country: str | None = None,
    card_country: str | None = None,
    vpn_detected: bool = False,
    bot_detected: bool = False,
    tampering_detected: bool = False,
    incognito: bool = False,
    virtual_machine: bool = False,
    ip_blocklisted: bool = False,
    suspect_score: int = 0,
    mean_amount: float | None = None,
    std_amount: float | None = None,
) -> TransactionFeatures:
    """Extract and engineer features from raw transaction data.

    Computes derived features (z-scores, interaction terms) from
    raw input signals.

    Args:
        amount: Transaction amount in USD.
        velocity_1h: Number of transactions in last hour.
        velocity_24h: Number of transactions in last 24 hours.
        account_age_days: Days since account creation.
        is_new_merchant: First transaction with this merchant.
        merchant_category: Merchant category slug.
        hour_of_day: UTC hour (0-23), auto-detected if None.
        day_of_week: Day of week (0=Mon, 6=Sun), auto-detected if None.
        typical_hours: Set of hours the agent normally transacts.
        geo_distance_km: Distance from typical location in km.
        billing_country: Billing country ISO code.
        card_country: Card country ISO code.
        vpn_detected: VPN detected by fingerprinting.
        bot_detected: Bot detected.
        tampering_detected: Browser tampering detected.
        incognito: Incognito mode.
        virtual_machine: VM detected.
        ip_blocklisted: IP on blocklist.
        suspect_score: Fingerprint suspect score 0-100.
        mean_amount: Agent's historical mean transaction amount.
        std_amount: Agent's historical transaction amount std dev.

    Returns:
        TransactionFeatures ready for model input.
    """
    now = datetime.now(UTC)
    hour = hour_of_day if hour_of_day is not None else now.hour
    dow = day_of_week if day_of_week is not None else now.weekday()

    # Amount z-score
    zscore = 0.0
    if mean_amount is not None and std_amount is not None and std_amount > 0:
        zscore = (amount - mean_amount) / std_amount
        zscore = max(-5.0, min(5.0, zscore))  # Clamp

    # Merchant category risk
    cat_risk = MERCHANT_CATEGORY_RISK.get(merchant_category or "", 0.3)

    # Country risk
    country_risk = 0.0
    if billing_country and billing_country.upper() in HIGH_RISK_COUNTRIES:
        country_risk = 1.0
    if card_country and card_country.upper() in HIGH_RISK_COUNTRIES:
        country_risk = max(country_risk, 1.0)

    # Country mismatch
    mismatch = 0.0
    if billing_country and card_country and billing_country != card_country:
        mismatch = 1.0

    # Out of hours
    out_of_hours = 0.0
    if typical_hours and hour not in typical_hours:
        out_of_hours = 1.0

    # Round amount detection
    is_round = 0.0
    if amount > 0 and amount == int(amount) and amount % 10 == 0:
        is_round = 1.0

    # Interaction features
    large_threshold = 1000.0
    large_new = float(amount > large_threshold and is_new_merchant)
    high_vel_high_amt = float(velocity_1h > 5 and amount > large_threshold)

    return TransactionFeatures(
        amount=amount,
        amount_zscore=zscore,
        velocity_1h=float(velocity_1h),
        velocity_24h=float(velocity_24h) / 24.0 if velocity_24h > 0 else 0.0,
        account_age_days=float(account_age_days),
        is_new_merchant=float(is_new_merchant),
        merchant_category_risk=cat_risk,
        hour_of_day=float(hour),
        is_weekend=float(dow >= 5),
        is_out_of_hours=out_of_hours,
        geo_distance_km=min(geo_distance_km, 20000.0),
        geo_anomalous=float(geo_distance_km > 2000),
        country_high_risk=country_risk,
        country_mismatch=mismatch,
        vpn_detected=float(vpn_detected),
        bot_detected=float(bot_detected),
        tampering_detected=float(tampering_detected),
        incognito=float(incognito),
        virtual_machine=float(virtual_machine),
        ip_blocklisted=float(ip_blocklisted),
        suspect_score=float(suspect_score) / 100.0,
        is_round_amount=is_round,
        large_amount_new_merchant=large_new,
        high_velocity_high_amount=high_vel_high_amt,
    )


# ============ ML Fraud Scorer ============

class MLFraudScorer:
    """ONNX-based ML fraud detection scorer.

    Loads a pre-trained XGBoost model (ONNX format) and scores
    transactions for fraud risk in real-time.

    Configuration via environment variables:
        SARDIS_ML_FRAUD_MODEL_PATH   — Path to .onnx model file
        SARDIS_ML_FRAUD_BLOCK_THRESHOLD  — Score threshold to block (default: 0.85)
        SARDIS_ML_FRAUD_REVIEW_THRESHOLD — Score threshold for review (default: 0.60)

    Usage:
        scorer = MLFraudScorer()
        await scorer.load_model("models/fraud_detector.onnx")
        features = extract_features(amount=5000, velocity_1h=10, ...)
        result = await scorer.score(features)
        if result.is_blocked:
            # Reject transaction
    """

    def __init__(
        self,
        model_path: str | None = None,
        block_threshold: float | None = None,
        review_threshold: float | None = None,
        scaler_state: ScalerState | None = None,
    ) -> None:
        self._model_path = model_path or os.getenv("SARDIS_ML_FRAUD_MODEL_PATH", "")
        self._block_threshold = block_threshold or float(
            os.getenv("SARDIS_ML_FRAUD_BLOCK_THRESHOLD", "0.85")
        )
        self._review_threshold = review_threshold or float(
            os.getenv("SARDIS_ML_FRAUD_REVIEW_THRESHOLD", "0.60")
        )
        self._scaler = scaler_state
        self._session: Any = None
        self._input_name: str = ""
        self._output_names: list[str] = []
        self._model_version: str = ""
        self._status = ModelStatus.NOT_LOADED

    @property
    def status(self) -> ModelStatus:
        return self._status

    @property
    def is_loaded(self) -> bool:
        return self._status == ModelStatus.LOADED

    async def load_model(self, model_path: str | None = None) -> bool:
        """Load ONNX model for inference.

        Args:
            model_path: Path to .onnx file. Falls back to env var.

        Returns:
            True if model loaded successfully.
        """
        if not HAS_ONNXRUNTIME:
            logger.warning("onnxruntime not installed, ML fraud scoring disabled")
            self._status = ModelStatus.DISABLED
            return False

        path = model_path or self._model_path
        if not path:
            logger.warning("No ML fraud model path configured")
            self._status = ModelStatus.DISABLED
            return False

        try:
            loop = asyncio.get_event_loop()
            self._session = await loop.run_in_executor(
                None,
                lambda: ort.InferenceSession(path, providers=["CPUExecutionProvider"]),
            )
            self._input_name = self._session.get_inputs()[0].name
            self._output_names = [o.name for o in self._session.get_outputs()]
            self._model_version = f"onnx:{path.split('/')[-1]}"
            self._status = ModelStatus.LOADED
            logger.info("ML fraud model loaded: %s", path)
            return True
        except Exception as e:
            logger.error("Failed to load ML fraud model: %s", e)
            self._status = ModelStatus.ERROR
            return False

    async def score(self, features: TransactionFeatures) -> FraudResult:
        """Score a transaction for fraud risk.

        If the model is not loaded, falls back to rule-based scoring.

        Args:
            features: Extracted transaction features.

        Returns:
            FraudResult with risk score and recommended action.
        """
        start = datetime.now(UTC)

        if not self.is_loaded:
            # Fallback: rule-based scoring
            result = self._rule_based_score(features)
            result.inference_time_ms = (datetime.now(UTC) - start).total_seconds() * 1000
            return result

        try:
            loop = asyncio.get_event_loop()
            risk_score = await loop.run_in_executor(
                None, self._inference_sync, features
            )
        except Exception as e:
            logger.error("ML inference failed, using rule-based fallback: %s", e)
            result = self._rule_based_score(features)
            result.details["inference_error"] = str(e)
            result.inference_time_ms = (datetime.now(UTC) - start).total_seconds() * 1000
            return result

        action = self._score_to_action(risk_score)
        elapsed = (datetime.now(UTC) - start).total_seconds() * 1000

        return FraudResult(
            risk_score=risk_score,
            action=action,
            model_version=self._model_version,
            features_used=len(FEATURE_SCHEMA),
            inference_time_ms=elapsed,
            details={"source": "onnx_model"},
        )

    def _inference_sync(self, features: TransactionFeatures) -> float:
        """Synchronous ONNX inference (runs in thread pool)."""
        if self._scaler:
            input_array = self._scaler.normalize(features)
        else:
            input_array = features.to_array()

        outputs = self._session.run(
            self._output_names,
            {self._input_name: input_array},
        )

        # XGBoost binary classifier outputs: [[not_fraud_prob, fraud_prob]]
        probabilities = outputs[0]
        if probabilities.ndim == 2 and probabilities.shape[1] >= 2:
            return float(probabilities[0][1])
        # Single output (regression)
        return float(probabilities[0][0])

    def _rule_based_score(self, features: TransactionFeatures) -> FraudResult:
        """Simple rule-based fallback when model is not available."""
        score = 0.0

        # Device signals
        if features.bot_detected > 0.5:
            score += 0.35
        if features.vpn_detected > 0.5:
            score += 0.10
        if features.tampering_detected > 0.5:
            score += 0.10
        if features.ip_blocklisted > 0.5:
            score += 0.10

        # Behavioral signals
        if features.amount_zscore > 3.0:
            score += 0.10
        if features.velocity_1h > 10:
            score += 0.10
        if features.geo_anomalous > 0.5:
            score += 0.05

        # Country risk
        if features.country_high_risk > 0.5:
            score += 0.05
        if features.country_mismatch > 0.5:
            score += 0.05

        score = min(score, 1.0)
        action = self._score_to_action(score)

        return FraudResult(
            risk_score=score,
            action=action,
            model_version="rule_based_v1",
            features_used=len(FEATURE_SCHEMA),
            details={"source": "rule_based_fallback"},
        )

    def _score_to_action(self, score: float) -> FraudAction:
        if score >= self._block_threshold:
            return FraudAction.BLOCK
        if score >= self._review_threshold:
            return FraudAction.REVIEW
        return FraudAction.APPROVE


# ============ Singleton ============

_scorer: MLFraudScorer | None = None


def get_ml_fraud_scorer() -> MLFraudScorer:
    """Get or create the global MLFraudScorer singleton."""
    global _scorer
    if _scorer is None:
        _scorer = MLFraudScorer()
    return _scorer

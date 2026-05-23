"""Sardis Guardrails - Runtime safety for agent payments.

Provides circuit breakers, kill switches, rate limiting, input validation,
and behavioral monitoring for safe agent payment execution.
"""

from sardis.guardrails.agent_threat_detector import (
    AgentThreatAssessment,
    AgentThreatDetector,
    AgentThreatSignals,
    ThreatCategory,
    get_agent_threat_detector,
)
from sardis.guardrails.anomaly_engine import (
    AnomalyEngine,
    RiskAction,
    RiskAssessment,
    RiskSignal,
)
from sardis.guardrails.behavioral_monitor import (
    AlertSeverity,
    BehavioralAlert,
    BehavioralMonitor,
    SensitivityLevel,
    SpendingPattern,
    TransactionData,
)
from sardis.guardrails.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerStats,
    CircuitState,
)
from sardis.guardrails.fingerprint import (
    BotResult,
    DeviceIntelligence,
    DeviceRisk,
    FingerprintError,
    FingerprintProvider,
    TamperingResult,
    VPNResult,
    get_fingerprint_provider,
)
from sardis.guardrails.ft3_taxonomy import (
    FT3Event,
    FT3Mitigation,
    FT3MitigationStatus,
    FT3Severity,
    FT3Tactic,
    FT3TaxonomyRegistry,
    FT3TaxonomyStats,
    FT3Technique,
    classify_event,
    create_ft3_registry,
)
from sardis.guardrails.graph_fraud import (
    GraphAnalysisResult,
    GraphFraudAnalyzer,
    GraphPattern,
    GraphRiskLevel,
    PatternMatch,
    TransactionEdge,
    TransactionGraph,
    WalletNode,
    create_graph_analyzer,
)
from sardis.guardrails.input_validator import (
    AmountValidator,
    ChainTokenValidator,
    PaymentInputValidator,
    StringSanitizer,
    ValidationError,
    WalletAddressValidator,
)
from sardis.guardrails.kill_switch import (
    ActivationReason,
    KillSwitch,
    KillSwitchActivation,
    KillSwitchError,
    get_kill_switch,
)
from sardis.guardrails.ml_fraud import (
    FEATURE_SCHEMA,
    FraudResult,
    MLFraudScorer,
    ModelStatus,
    ScalerState,
    TransactionFeatures,
    extract_features,
    get_ml_fraud_scorer,
)

# Alias to avoid conflict with zen_engine FraudAction
from sardis.guardrails.ml_fraud import FraudAction as MLFraudAction
from sardis.guardrails.rate_limiter import (
    RateLimit,
    RateLimiter,
    RateLimitError,
    TokenBucket,
    TransactionRecord,
)

try:
    from sardis.guardrails.zen_engine import (
        FraudAction,
        FraudRuleResult,
        ZenFraudEngine,
        ZenFraudProvider,
    )
except ImportError:
    # zen-engine optional dependency not installed
    ZenFraudEngine = None  # type: ignore[assignment,misc]
    ZenFraudProvider = None  # type: ignore[assignment,misc]
    FraudAction = None  # type: ignore[assignment,misc]
    FraudRuleResult = None  # type: ignore[assignment,misc]

__version__ = "2.0.0a0"

__all__ = [
    # Circuit Breaker
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerError",
    "CircuitBreakerStats",
    "CircuitState",
    # Kill Switch
    "ActivationReason",
    "KillSwitch",
    "KillSwitchActivation",
    "KillSwitchError",
    "get_kill_switch",
    # Rate Limiter
    "RateLimit",
    "RateLimiter",
    "RateLimitError",
    "TokenBucket",
    "TransactionRecord",
    # Input Validator
    "AmountValidator",
    "ChainTokenValidator",
    "PaymentInputValidator",
    "StringSanitizer",
    "ValidationError",
    "WalletAddressValidator",
    # Behavioral Monitor
    "AlertSeverity",
    "BehavioralAlert",
    "BehavioralMonitor",
    "SensitivityLevel",
    "SpendingPattern",
    "TransactionData",
    # Anomaly Engine
    "AnomalyEngine",
    "RiskAction",
    "RiskAssessment",
    "RiskSignal",
    # Agent Threat Detection
    "AgentThreatDetector",
    "AgentThreatAssessment",
    "AgentThreatSignals",
    "ThreatCategory",
    "get_agent_threat_detector",
    # Zen Fraud Engine
    "ZenFraudEngine",
    "ZenFraudProvider",
    "FraudAction",
    "FraudRuleResult",
    # Fingerprint Device Intelligence
    "FingerprintProvider",
    "DeviceIntelligence",
    "DeviceRisk",
    "BotResult",
    "VPNResult",
    "TamperingResult",
    "FingerprintError",
    "get_fingerprint_provider",
    # ML Fraud Detection
    "MLFraudScorer",
    "MLFraudAction",
    "FraudResult",
    "TransactionFeatures",
    "ScalerState",
    "ModelStatus",
    "FEATURE_SCHEMA",
    "extract_features",
    "get_ml_fraud_scorer",
    # Graph-Based Fraud Detection
    "GraphFraudAnalyzer",
    "GraphAnalysisResult",
    "GraphPattern",
    "GraphRiskLevel",
    "PatternMatch",
    "TransactionEdge",
    "TransactionGraph",
    "WalletNode",
    "create_graph_analyzer",
    # FT3 Fraud Taxonomy
    "FT3TaxonomyRegistry",
    "FT3Tactic",
    "FT3Technique",
    "FT3Event",
    "FT3Severity",
    "FT3Mitigation",
    "FT3MitigationStatus",
    "FT3TaxonomyStats",
    "create_ft3_registry",
    "classify_event",
]

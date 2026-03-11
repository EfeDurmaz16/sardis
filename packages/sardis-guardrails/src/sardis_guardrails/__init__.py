"""Sardis Guardrails - Runtime safety for agent payments.

Provides circuit breakers, kill switches, rate limiting, input validation,
and behavioral monitoring for safe agent payment execution.
"""

from sardis_guardrails.agent_threat_detector import (
    AgentThreatAssessment,
    AgentThreatDetector,
    AgentThreatSignals,
    ThreatCategory,
    get_agent_threat_detector,
)
from sardis_guardrails.anomaly_engine import (
    AnomalyEngine,
    RiskAction,
    RiskAssessment,
    RiskSignal,
)
from sardis_guardrails.behavioral_monitor import (
    AlertSeverity,
    BehavioralAlert,
    BehavioralMonitor,
    SensitivityLevel,
    SpendingPattern,
    TransactionData,
)
from sardis_guardrails.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerStats,
    CircuitState,
)
from sardis_guardrails.input_validator import (
    AmountValidator,
    ChainTokenValidator,
    PaymentInputValidator,
    StringSanitizer,
    ValidationError,
    WalletAddressValidator,
)
from sardis_guardrails.kill_switch import (
    ActivationReason,
    KillSwitch,
    KillSwitchActivation,
    KillSwitchError,
    get_kill_switch,
)
from sardis_guardrails.rate_limiter import (
    RateLimit,
    RateLimiter,
    RateLimitError,
    TokenBucket,
    TransactionRecord,
)

from sardis_guardrails.fingerprint import (
    BotResult,
    DeviceIntelligence,
    DeviceRisk,
    FingerprintError,
    FingerprintProvider,
    TamperingResult,
    VPNResult,
    get_fingerprint_provider,
)

try:
    from sardis_guardrails.zen_engine import (
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

__version__ = "0.1.0"

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
]

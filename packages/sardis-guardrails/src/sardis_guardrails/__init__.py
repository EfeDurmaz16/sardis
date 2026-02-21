"""Sardis Guardrails - Runtime safety for agent payments.

Provides circuit breakers, kill switches, rate limiting, input validation,
and behavioral monitoring for safe agent payment execution.
"""

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
]

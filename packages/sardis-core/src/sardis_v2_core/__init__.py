"""Core domain primitives shared across Sardis services.

Version: 0.1.0

This package provides the foundational components for the Sardis payment
infrastructure, including:

- Exception hierarchy with detailed error codes
- Configuration management and validation
- Input validation utilities
- Retry mechanisms with exponential backoff
- Circuit breaker pattern for service resilience
- Structured logging with sensitive data masking
- Domain models (wallets, transactions, holds, etc.)

Example usage:
    from sardis_v2_core import (
        # Configuration
        load_config_from_env,
        validate_startup,

        # Domain models
        Wallet,
        Transaction,
        Hold,

        # Utilities
        retry,
        get_circuit_breaker,
        get_logger,
        validate_wallet_id,
    )
"""

from .exceptions import (
    SardisException,
    SardisValidationError,
    SardisNotFoundError,
    SardisAuthenticationError,
    SardisAuthorizationError,
    SardisConflictError,
    SardisPaymentError,
    SardisPolicyViolationError,
    SardisInsufficientBalanceError,
    SardisTransactionFailedError,
    SardisMandateError,
    SardisSignatureError,
    SardisMandateExpiredError,
    SardisMandateReplayError,
    SardisMandateChainError,
    SardisChainError,
    SardisRPCError,
    SardisDatabaseError,
    SardisMPCError,
    SardisComplianceError,
    SardisKYCRequiredError,
    SardisKYCExpiredError,
    SardisSanctionsHitError,
    SardisTravelRuleError,
    SardisAlgorithmNotSupportedError,
    SardisHoldError,
    SardisHoldNotFoundError,
    SardisHoldExpiredError,
    SardisHoldAlreadyCapturedError,
    SardisHoldAlreadyVoidedError,
    SardisConfigurationError,
    SardisDependencyNotConfiguredError,
    SardisRateLimitError,
    SardisTimeoutError,
    SardisServiceUnavailableError,
    # Error mapping utilities
    exception_from_chain_error,
    exception_from_mpc_error,
    exception_from_compliance_error,
    get_exception_class,
    create_exception,
)
from .config import SardisSettings, load_settings, TurnkeyConfig, MPCProvider, ChainConfig
from .identity import AgentIdentity
from .mandates import IntentMandate, CartMandate, PaymentMandate, MandateChain
from .tokens import TokenType, TokenMetadata
from .wallets import Wallet, TokenLimit, TokenBalance  # TokenBalance is alias for TokenLimit
from .spending_policy import SpendingPolicy, TimeWindowLimit, MerchantRule, TrustLevel, SpendingScope, create_default_policy
from .spending_policy_store import SpendingPolicyStore
from .policy_store import AsyncPolicyStore
from .policy_store_memory import InMemoryPolicyStore
from .policy_store_postgres import PostgresPolicyStore
from .spending_policy_json import spending_policy_to_json, spending_policy_from_json
from .transactions import Transaction, TransactionStatus, OnChainRecord
from .virtual_card import VirtualCard, CardStatus, CardType, FundingSource
from .orchestrator import PaymentOrchestrator, PaymentResult, PaymentExecutionError
from .database import Database, init_database, SCHEMA_SQL
from .holds import Hold, HoldResult, HoldsRepository
from .webhooks import (
    EventType,
    WebhookEvent,
    WebhookSubscription,
    DeliveryAttempt,
    WebhookRepository,
    WebhookService,
    create_payment_event,
    create_hold_event,
)
from .cache import CacheService, CacheBackend, InMemoryCache, RedisCache, create_cache_service
from .agents import Agent, AgentPolicy, SpendingLimits, AgentRepository
from .agent_groups import AgentGroup, AgentGroupRepository, GroupSpendingLimits, GroupMerchantPolicy
from .group_policy import GroupPolicyEvaluator, GroupPolicyResult, GroupPolicyPort, InMemoryGroupSpendingTracker
from .wallet_repository import WalletRepository
from .agent_repository_postgres import PostgresAgentRepository
from .wallet_repository_postgres import PostgresWalletRepository
from .utils import TTLDict, BoundedDict, TTLEntry
from .nl_policy_parser import (
    NLPolicyParser,
    RegexPolicyParser,
    create_policy_parser,
    parse_nl_policy,
    parse_nl_policy_sync,
)
from .spending_tracker import (
    SpendingTracker,
    InMemorySpendingTracker,
    create_spending_tracker,
)

# New enterprise-quality modules
from .constants import (
    Timeouts,
    RetryConfig as RetryDefaults,
    CircuitBreakerDefaults,
    PoolLimits,
    CacheTTL,
    CacheLimits,
    PaymentLimits,
    HoldConfig,
    CardLimits,
    TokenConfig,
    APIConfig,
    SecurityConfig,
    LoggingConfig,
    ErrorCodes,
    get_http_status_for_error,
    map_chain_error,
)
from .retry import (
    RetryConfig,
    RetryStats,
    RetryExhausted,
    RetryContext,
    retry,
    retry_async,
    retry_sync,
    MPC_RETRY_CONFIG,
    RPC_RETRY_CONFIG,
    DB_RETRY_CONFIG,
    WEBHOOK_RETRY_CONFIG,
)
from .validators import (
    validate_wallet_id,
    validate_agent_id,
    validate_amount,
    validate_token,
    validate_chain,
    validate_eth_address,
    validate_chain_address,
    validate_url,
    validate_email,
    validate_payment_request,
    validate_hold_request,
    ValidationResult,
)
from .circuit_breaker import (
    CircuitState,
    CircuitBreakerConfig,
    CircuitStats,
    CircuitBreakerError,
    CircuitBreaker,
    CircuitBreakerRegistry,
    get_circuit_breaker_registry,
    get_circuit_breaker,
    create_service_circuit_breakers,
    circuit_breaker,
)
from .logging import (
    get_logger,
    StructuredLogger,
    RequestContext,
    mask_sensitive_data,
    mask_headers,
    log_request,
    log_response,
    log_operation,
    configure_logging,
)
from .config_validation import (
    SardisConfig,
    DatabaseConfig,
    CacheConfig as CacheConfigModel,
    TurnkeyConfig as TurnkeyConfigModel,
    PersonaConfig,
    EllipticConfig,
    LithicConfig,
    ChainConfig as ChainConfigModel,
    APIServerConfig,
    Environment,
    load_config_from_env,
    validate_config,
    require_service_config,
    validate_startup,
)

__all__ = [
    # Exceptions
    "SardisException",
    "SardisValidationError",
    "SardisNotFoundError",
    "SardisAuthenticationError",
    "SardisAuthorizationError",
    "SardisConflictError",
    "SardisPaymentError",
    "SardisPolicyViolationError",
    "SardisInsufficientBalanceError",
    "SardisTransactionFailedError",
    "SardisMandateError",
    "SardisSignatureError",
    "SardisMandateExpiredError",
    "SardisMandateReplayError",
    "SardisMandateChainError",
    "SardisChainError",
    "SardisRPCError",
    "SardisDatabaseError",
    "SardisMPCError",
    "SardisComplianceError",
    "SardisKYCRequiredError",
    "SardisKYCExpiredError",
    "SardisSanctionsHitError",
    "SardisTravelRuleError",
    "SardisAlgorithmNotSupportedError",
    "SardisHoldError",
    "SardisHoldNotFoundError",
    "SardisHoldExpiredError",
    "SardisHoldAlreadyCapturedError",
    "SardisHoldAlreadyVoidedError",
    "SardisConfigurationError",
    "SardisDependencyNotConfiguredError",
    "SardisRateLimitError",
    # Config
    "SardisSettings",
    "TurnkeyConfig",
    "MPCProvider",
    "ChainConfig",
    "AgentIdentity",
    "IntentMandate",
    "CartMandate",
    "PaymentMandate",
    "MandateChain",
    "load_settings",
    "TokenType",
    "TokenMetadata",
    "Wallet",
    "TokenLimit",
    "TokenBalance",  # Backwards compatibility alias for TokenLimit
    "SpendingPolicy",
    "TimeWindowLimit",
    "MerchantRule",
    "TrustLevel",
    "SpendingScope",
    "create_default_policy",
    "Transaction",
    "TransactionStatus",
    "OnChainRecord",
    "VirtualCard",
    "CardStatus",
    "CardType",
    "FundingSource",
    "PaymentOrchestrator",
    "PaymentResult",
    "PaymentExecutionError",
    "Database",
    "init_database",
    "SCHEMA_SQL",
    "Hold",
    "HoldResult",
    "HoldsRepository",
    "EventType",
    "WebhookEvent",
    "WebhookSubscription",
    "DeliveryAttempt",
    "WebhookRepository",
    "WebhookService",
    "create_payment_event",
    "create_hold_event",
    "CacheService",
    "CacheBackend",
    "InMemoryCache",
    "RedisCache",
    "create_cache_service",
    "Agent",
    "AgentPolicy",
    "SpendingLimits",
    "AgentRepository",
    "AgentGroup",
    "AgentGroupRepository",
    "GroupSpendingLimits",
    "GroupMerchantPolicy",
    "GroupPolicyEvaluator",
    "GroupPolicyResult",
    "GroupPolicyPort",
    "InMemoryGroupSpendingTracker",
    "WalletRepository",
    # Utilities
    "TTLDict",
    "BoundedDict",
    "TTLEntry",
    # NL Policy Parser
    "NLPolicyParser",
    "RegexPolicyParser",
    "create_policy_parser",
    "parse_nl_policy",
    "parse_nl_policy_sync",
    # Spending Tracker
    "SpendingTracker",
    "InMemorySpendingTracker",
    "create_spending_tracker",
    # Constants
    "Timeouts",
    "RetryDefaults",
    "CircuitBreakerDefaults",
    "PoolLimits",
    "CacheTTL",
    "CacheLimits",
    "PaymentLimits",
    "HoldConfig",
    "CardLimits",
    "TokenConfig",
    "APIConfig",
    "SecurityConfig",
    "LoggingConfig",
    "ErrorCodes",
    "get_http_status_for_error",
    "map_chain_error",
    # Retry
    "RetryConfig",
    "RetryStats",
    "RetryExhausted",
    "RetryContext",
    "retry",
    "retry_async",
    "retry_sync",
    "MPC_RETRY_CONFIG",
    "RPC_RETRY_CONFIG",
    "DB_RETRY_CONFIG",
    "WEBHOOK_RETRY_CONFIG",
    # Validators
    "validate_wallet_id",
    "validate_agent_id",
    "validate_amount",
    "validate_token",
    "validate_chain",
    "validate_eth_address",
    "validate_chain_address",
    "validate_url",
    "validate_email",
    "validate_payment_request",
    "validate_hold_request",
    "ValidationResult",
    # Circuit Breaker
    "CircuitState",
    "CircuitBreakerConfig",
    "CircuitStats",
    "CircuitBreakerError",
    "CircuitBreaker",
    "CircuitBreakerRegistry",
    "get_circuit_breaker_registry",
    "get_circuit_breaker",
    "create_service_circuit_breakers",
    "circuit_breaker",
    # Logging
    "get_logger",
    "StructuredLogger",
    "RequestContext",
    "mask_sensitive_data",
    "mask_headers",
    "log_request",
    "log_response",
    "log_operation",
    "configure_logging",
    # Configuration Validation
    "SardisConfig",
    "DatabaseConfig",
    "CacheConfigModel",
    "TurnkeyConfigModel",
    "PersonaConfig",
    "EllipticConfig",
    "LithicConfig",
    "ChainConfigModel",
    "APIServerConfig",
    "Environment",
    "load_config_from_env",
    "validate_config",
    "require_service_config",
    "validate_startup",
    # Exception utilities
    "SardisTimeoutError",
    "SardisServiceUnavailableError",
    "exception_from_chain_error",
    "exception_from_mpc_error",
    "exception_from_compliance_error",
    "get_exception_class",
    "create_exception",
    # Version
    "__version__",
]

__version__ = "0.1.0"

"""Core domain primitives shared across Sardis services.

Version: 0.3.0

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

from .agent_groups import (
    AgentGroup,
    AgentGroupHierarchy,
    AgentGroupRepository,
    GroupMerchantPolicy,
    GroupSpendingLimits,
    merge_group_policies,
)
from .agent_repository_postgres import PostgresAgentRepository
from .agents import Agent, AgentPolicy, AgentRepository, SpendingLimits
from .cache import CacheBackend, CacheService, InMemoryCache, RedisCache, create_cache_service
from .circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitBreakerError,
    CircuitBreakerRegistry,
    CircuitState,
    CircuitStats,
    circuit_breaker,
    create_service_circuit_breakers,
    get_circuit_breaker,
    get_circuit_breaker_registry,
)
from .config import (
    CardStackConfig,
    ChainConfig,
    CircleCPNConfig,
    CoinbaseConfig,
    LithicConfig,
    MPCProvider,
    SardisSettings,
    StripeConfig,
    TurnkeyConfig,
    load_settings,
)
from .config_validation import (
    APIServerConfig,
    DatabaseConfig,
    EllipticConfig,
    Environment,
    LithicConfig,
    PersonaConfig,
    SardisConfig,
    load_config_from_env,
    require_service_config,
    validate_config,
    validate_startup,
)
from .config_validation import (
    CacheConfig as CacheConfigModel,
)
from .config_validation import (
    ChainConfig as ChainConfigModel,
)
from .config_validation import (
    TurnkeyConfig as TurnkeyConfigModel,
)

# New enterprise-quality modules
from .constants import (
    APIConfig,
    CacheLimits,
    CacheTTL,
    CardLimits,
    CircuitBreakerDefaults,
    ErrorCodes,
    HoldConfig,
    LoggingConfig,
    PaymentLimits,
    PoolLimits,
    SecurityConfig,
    Timeouts,
    TokenConfig,
    get_http_status_for_error,
    map_chain_error,
)
from .constants import (
    RetryConfig as RetryDefaults,
)
from .database import SCHEMA_SQL, Database, init_database
from .drift_policy_integrator import (
    DriftAction,
    DriftActionResult,
    DriftPolicyConfig,
    DriftPolicyIntegrator,
)
from .event_bus import (
    EventBus,
    emit_approval_event,
    emit_card_event,
    emit_compliance_event,
    emit_group_event,
    emit_policy_event,
    emit_spend_event,
    get_default_bus,
)
from .exception_workflows import (
    ExceptionStatus,
    ExceptionType,
    ExceptionWorkflowEngine,
    PaymentException,
    ResolutionStrategy,
)
from .exceptions import (
    SardisAlgorithmNotSupportedError,
    SardisAuthenticationError,
    SardisAuthorizationError,
    SardisChainError,
    SardisComplianceError,
    SardisConfigurationError,
    SardisConflictError,
    SardisDatabaseError,
    SardisDependencyNotConfiguredError,
    SardisException,
    SardisHoldAlreadyCapturedError,
    SardisHoldAlreadyVoidedError,
    SardisHoldError,
    SardisHoldExpiredError,
    SardisHoldNotFoundError,
    SardisInsufficientBalanceError,
    SardisKYCExpiredError,
    SardisKYCRequiredError,
    SardisMandateChainError,
    SardisMandateError,
    SardisMandateExpiredError,
    SardisMandateReplayError,
    SardisMPCError,
    SardisNotFoundError,
    SardisPaymentError,
    SardisPolicyViolationError,
    SardisRateLimitError,
    SardisRPCError,
    SardisSanctionsHitError,
    SardisServiceUnavailableError,
    SardisSignatureError,
    SardisTimeoutError,
    SardisTransactionFailedError,
    SardisTravelRuleError,
    SardisValidationError,
    create_exception,
    # Error mapping utilities
    exception_from_chain_error,
    exception_from_compliance_error,
    exception_from_mpc_error,
    get_exception_class,
)
from .group_policy import (
    GroupPolicyEvaluator,
    GroupPolicyPort,
    GroupPolicyResult,
    InMemoryGroupSpendingTracker,
)
from .holds import Hold, HoldResult, HoldsRepository
from .identity import AgentIdentity
from .logging import (
    RequestContext,
    StructuredLogger,
    configure_logging,
    get_logger,
    log_operation,
    log_request,
    log_response,
    mask_headers,
    mask_sensitive_data,
)
from .mandates import CartMandate, IntentMandate, MandateChain, PaymentMandate
from .merchant_trust import MerchantProfile, MerchantTrustLevel, MerchantTrustService
from .nl_policy_parser import (
    NLPolicyParser,
    RegexPolicyParser,
    create_policy_parser,
    parse_nl_policy,
    parse_nl_policy_sync,
)
from .orchestrator import (
    FASTPATH_MAX_AMOUNT_MINOR,
    FASTPATH_MIN_TRUST_SCORE,
    FASTPATH_REQUIRED_KYA_LEVEL,
    FastPathResult,
    KYAVerificationPort,
    KYAViolationError,
    PaymentExecutionError,
    PaymentOrchestrator,
    PaymentResult,
    SanctionsScreeningPort,
)
from .policy_evidence import (
    PolicyDecisionLog,
    PolicyStepResult,
    compute_evidence_hash,
    evaluate_with_evidence,
    export_evidence_bundle,
)
from .policy_recommendations import PolicyRecommendation, PolicyRecommendationEngine
from .policy_store import AsyncPolicyStore
from .policy_store_memory import InMemoryPolicyStore
from .policy_store_postgres import PostgresPolicyStore
from .policy_version_store import PolicyVersion, PolicyVersionStore, compute_policy_hash
from .rail import Rail, RailCapabilities, RailExecutor, RailResult, RailRouter
from .retry import (
    DB_RETRY_CONFIG,
    MPC_RETRY_CONFIG,
    RPC_RETRY_CONFIG,
    WEBHOOK_RETRY_CONFIG,
    RetryConfig,
    RetryContext,
    RetryExhausted,
    RetryStats,
    retry,
    retry_async,
    retry_sync,
)
from .spending_policy import (
    KYA_TO_TRUST,
    TRUST_TO_KYA,
    MerchantRule,
    SpendingPolicy,
    SpendingScope,
    TimeWindowLimit,
    TrustLevel,
    create_default_policy,
    kya_level_for_trust,
    trust_level_for_kya,
)
from .spending_policy_json import spending_policy_from_json, spending_policy_to_json
from .spending_policy_store import SpendingPolicyStore
from .spending_tracker import (
    InMemorySpendingTracker,
    SpendingTracker,
    create_spending_tracker,
)
from .tokens import TokenMetadata, TokenType
from .transactions import OnChainRecord, Transaction, TransactionStatus
from .utils import BoundedDict, TTLDict, TTLEntry
from .validators import (
    ValidationResult,
    validate_agent_id,
    validate_amount,
    validate_chain,
    validate_chain_address,
    validate_email,
    validate_eth_address,
    validate_hold_request,
    validate_payment_request,
    validate_token,
    validate_url,
    validate_wallet_id,
)
from .virtual_card import CardStatus, CardType, FundingSource, VirtualCard
from .wallet_repository import WalletRepository
from .wallet_repository_postgres import PostgresWalletRepository
from .wallets import TokenBalance, TokenLimit, Wallet  # TokenBalance is alias for TokenLimit
from .webhooks import (
    DeliveryAttempt,
    EventType,
    WebhookEvent,
    WebhookRepository,
    WebhookService,
    WebhookSubscription,
    create_hold_event,
    create_payment_event,
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
    "LithicConfig",
    "StripeConfig",
    "CoinbaseConfig",
    "CircleCPNConfig",
    "CardStackConfig",
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
    "trust_level_for_kya",
    "kya_level_for_trust",
    "KYA_TO_TRUST",
    "TRUST_TO_KYA",
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
    "KYAViolationError",
    "KYAVerificationPort",
    "FastPathResult",
    "SanctionsScreeningPort",
    "FASTPATH_MIN_TRUST_SCORE",
    "FASTPATH_MAX_AMOUNT_MINOR",
    "FASTPATH_REQUIRED_KYA_LEVEL",
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
    # Event Bus
    "EventBus",
    "get_default_bus",
    "emit_policy_event",
    "emit_spend_event",
    "emit_approval_event",
    "emit_card_event",
    "emit_compliance_event",
    "emit_group_event",
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
    "AgentGroupHierarchy",
    "merge_group_policies",
    # Policy Versioning
    "PolicyVersionStore",
    "PolicyVersion",
    "compute_policy_hash",
    # Policy Evidence
    "PolicyStepResult",
    "PolicyDecisionLog",
    "evaluate_with_evidence",
    "export_evidence_bundle",
    "compute_evidence_hash",
    # Drift Policy Integration
    "DriftPolicyIntegrator",
    "DriftAction",
    "DriftPolicyConfig",
    "DriftActionResult",
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
    # Stripe Treasury
    "StripeTreasuryProvider",
    "TreasuryBalance",
    "FinancialAccount",
    "OutboundPayment",
    "IssuingFundTransfer",
    # Sub-ledger
    "SubLedgerManager",
    "SubLedgerAccount",
    "SubLedgerTransaction",
    "SubLedgerTxType",
    # Fiat orchestrator
    "FiatPaymentOrchestrator",
    "FiatPaymentResult",
    # Funding ports/adapters
    "CircleCPNFundingAdapter",
    "FundingRailAdapter",
]

# Stripe Treasury integration
from .cpn_funding_adapter import CircleCPNFundingAdapter

# End-to-end fiat payment orchestrator
from .fiat_orchestrator import (
    FiatPaymentOrchestrator,
    FiatPaymentResult,
)
from .funding_ports import FundingRailAdapter
from .stripe_treasury import (
    FinancialAccount,
    IssuingFundTransfer,
    OutboundPayment,
    StripeTreasuryProvider,
    TreasuryBalance,
)

# Sub-ledger fiat account management
from .sub_ledger import (
    SubLedgerAccount,
    SubLedgerManager,
    SubLedgerTransaction,
    SubLedgerTxType,
)

__version__ = "0.3.0"

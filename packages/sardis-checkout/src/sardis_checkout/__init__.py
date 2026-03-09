"""
Sardis Checkout Surface - PSP routing and orchestration.

This package provides the checkout surface that routes agent payments
to existing PSPs (Stripe, PayPal, Coinbase, Circle) while leveraging
the core Agent Wallet OS for policy enforcement.

Production-grade features:
- Idempotency support for all operations
- Session timeout of 15 minutes (configurable)
- Comprehensive analytics tracking
- Fraud detection integration
- Multi-currency checkout
- Partial payment support
- Payment link management
- Webhook delivery with retry
- Checkout customization options
"""

# Analytics
from sardis_checkout.analytics import (
    AnalyticsBackend,
    BufferedAnalyticsBackend,
    CheckoutAnalytics,
    CompositeAnalyticsBackend,
    InMemoryAnalyticsBackend,
    LoggingAnalyticsBackend,
)

# Connectors
from sardis_checkout.connectors import (
    PSPConnector,
    StripeConnector,
)

# Multi-currency
from sardis_checkout.currency import (
    DEFAULT_CURRENCIES,
    CachedExchangeRateProvider,
    ConversionError,
    CurrencyConverter,
    CurrencyError,
    ExchangeRate,
    ExchangeRateProvider,
    MultiCurrencyCheckout,
    RateNotAvailable,
    StaticExchangeRateProvider,
    UnsupportedCurrency,
)

# Fraud detection
from sardis_checkout.fraud import (
    AmountCheckProvider,
    EmailCheckProvider,
    FraudCheckContext,
    FraudCheckFailed,
    FraudDeclined,
    FraudDetector,
    FraudError,
    FraudRuleEngine,
    FraudSignalProvider,
    GeoCheckProvider,
    VelocityCheckProvider,
)

# Idempotency
from sardis_checkout.idempotency import (
    IdempotencyError,
    IdempotencyKeyConflict,
    IdempotencyManager,
    IdempotencyOperationInProgress,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    generate_idempotency_key,
)
from sardis_checkout.models import (
    DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS,
    # Constants
    DEFAULT_SESSION_TIMEOUT_MINUTES,
    # Analytics
    CheckoutAnalyticsEvent,
    CheckoutCustomization,
    CheckoutEventType,
    # Core models
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSession,  # Legacy, for backwards compatibility
    # Multi-currency
    CurrencyConversion,
    # Sessions
    CustomerSession,
    # Fraud detection
    FraudCheckResult,
    FraudDecision,
    FraudRiskLevel,
    FraudRule,
    FraudSignal,
    # Idempotency
    IdempotencyRecord,
    MerchantConfig,
    # Partial payments
    PartialPayment,
    # Payment links
    PaymentLink,
    PaymentStatus,
    # Configuration
    PSPConfig,
    PSPType,
    SupportedCurrency,
    # Webhooks
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
)
from sardis_checkout.orchestrator import CheckoutError, CheckoutOrchestrator

# Partial payments
from sardis_checkout.partial_payments import (
    CheckoutAlreadyPaid,
    InMemoryPartialPaymentStore,
    PartialPaymentError,
    PartialPaymentManager,
    PartialPaymentsNotAllowed,
    PartialPaymentState,
    PartialPaymentStore,
    PaymentAmountTooLarge,
    PaymentAmountTooSmall,
)

# Payment links
from sardis_checkout.payment_links import (
    InMemoryPaymentLinkStore,
    PaymentLinkAlreadyUsed,
    PaymentLinkError,
    PaymentLinkExpired,
    PaymentLinkManager,
    PaymentLinkNotFound,
    PaymentLinkRevoked,
    PaymentLinkStore,
)

# Sessions
from sardis_checkout.sessions import (
    InMemorySessionStore,
    SessionError,
    SessionExpired,
    SessionInvalid,
    SessionManager,
    SessionNotFound,
    SessionStore,
)

# Webhooks
from sardis_checkout.webhooks import (
    InMemoryWebhookStore,
    RetryConfig,
    WebhookDeliveryFailed,
    WebhookDeliveryManager,
    WebhookEndpointNotFound,
    WebhookError,
    WebhookSignatureInvalid,
    WebhookSigner,
    WebhookStore,
)

__all__ = [
    # Orchestrator
    "CheckoutOrchestrator",
    "CheckoutError",
    # Core models
    "CheckoutRequest",
    "CheckoutResponse",
    "CheckoutSession",
    "PaymentStatus",
    "PSPType",
    "PSPConfig",
    "MerchantConfig",
    "CheckoutCustomization",
    # Idempotency
    "IdempotencyManager",
    "IdempotencyStore",
    "InMemoryIdempotencyStore",
    "IdempotencyRecord",
    "IdempotencyError",
    "IdempotencyKeyConflict",
    "IdempotencyOperationInProgress",
    "generate_idempotency_key",
    # Analytics
    "CheckoutAnalytics",
    "AnalyticsBackend",
    "InMemoryAnalyticsBackend",
    "LoggingAnalyticsBackend",
    "CompositeAnalyticsBackend",
    "BufferedAnalyticsBackend",
    "CheckoutAnalyticsEvent",
    "CheckoutEventType",
    # Payment links
    "PaymentLinkManager",
    "PaymentLinkStore",
    "InMemoryPaymentLinkStore",
    "PaymentLink",
    "PaymentLinkError",
    "PaymentLinkNotFound",
    "PaymentLinkExpired",
    "PaymentLinkAlreadyUsed",
    "PaymentLinkRevoked",
    # Partial payments
    "PartialPaymentManager",
    "PartialPaymentStore",
    "InMemoryPartialPaymentStore",
    "PartialPayment",
    "PartialPaymentState",
    "PartialPaymentError",
    "PaymentAmountTooSmall",
    "PaymentAmountTooLarge",
    "CheckoutAlreadyPaid",
    "PartialPaymentsNotAllowed",
    # Multi-currency
    "CurrencyConverter",
    "MultiCurrencyCheckout",
    "ExchangeRateProvider",
    "StaticExchangeRateProvider",
    "CachedExchangeRateProvider",
    "ExchangeRate",
    "CurrencyConversion",
    "SupportedCurrency",
    "CurrencyError",
    "UnsupportedCurrency",
    "ConversionError",
    "RateNotAvailable",
    "DEFAULT_CURRENCIES",
    # Sessions
    "SessionManager",
    "SessionStore",
    "InMemorySessionStore",
    "CustomerSession",
    "SessionError",
    "SessionNotFound",
    "SessionExpired",
    "SessionInvalid",
    # Webhooks
    "WebhookDeliveryManager",
    "WebhookStore",
    "InMemoryWebhookStore",
    "WebhookSigner",
    "RetryConfig",
    "WebhookDelivery",
    "WebhookDeliveryStatus",
    "WebhookEndpoint",
    "WebhookError",
    "WebhookEndpointNotFound",
    "WebhookDeliveryFailed",
    "WebhookSignatureInvalid",
    # Fraud detection
    "FraudDetector",
    "FraudCheckContext",
    "FraudSignalProvider",
    "VelocityCheckProvider",
    "GeoCheckProvider",
    "AmountCheckProvider",
    "EmailCheckProvider",
    "FraudRuleEngine",
    "FraudCheckResult",
    "FraudDecision",
    "FraudRiskLevel",
    "FraudRule",
    "FraudSignal",
    "FraudError",
    "FraudCheckFailed",
    "FraudDeclined",
    # Connectors
    "PSPConnector",
    "StripeConnector",
    # Constants
    "DEFAULT_SESSION_TIMEOUT_MINUTES",
    "DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS",
]

__version__ = "0.3.0"

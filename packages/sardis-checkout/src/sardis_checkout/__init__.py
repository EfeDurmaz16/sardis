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

from sardis_checkout.orchestrator import CheckoutOrchestrator, CheckoutError
from sardis_checkout.models import (
    # Core models
    CheckoutRequest,
    CheckoutResponse,
    CheckoutSession,  # Legacy, for backwards compatibility
    PaymentStatus,
    PSPType,
    # Configuration
    PSPConfig,
    MerchantConfig,
    CheckoutCustomization,
    # Idempotency
    IdempotencyRecord,
    # Analytics
    CheckoutAnalyticsEvent,
    CheckoutEventType,
    # Partial payments
    PartialPayment,
    # Multi-currency
    CurrencyConversion,
    SupportedCurrency,
    # Sessions
    CustomerSession,
    # Payment links
    PaymentLink,
    # Webhooks
    WebhookDelivery,
    WebhookDeliveryStatus,
    WebhookEndpoint,
    # Fraud detection
    FraudCheckResult,
    FraudDecision,
    FraudRiskLevel,
    FraudRule,
    FraudSignal,
    # Constants
    DEFAULT_SESSION_TIMEOUT_MINUTES,
    DEFAULT_PAYMENT_LINK_EXPIRATION_HOURS,
)

# Idempotency
from sardis_checkout.idempotency import (
    IdempotencyManager,
    IdempotencyStore,
    InMemoryIdempotencyStore,
    IdempotencyError,
    IdempotencyKeyConflict,
    IdempotencyOperationInProgress,
    generate_idempotency_key,
)

# Analytics
from sardis_checkout.analytics import (
    CheckoutAnalytics,
    AnalyticsBackend,
    InMemoryAnalyticsBackend,
    LoggingAnalyticsBackend,
    CompositeAnalyticsBackend,
    BufferedAnalyticsBackend,
)

# Payment links
from sardis_checkout.payment_links import (
    PaymentLinkManager,
    PaymentLinkStore,
    InMemoryPaymentLinkStore,
    PaymentLinkError,
    PaymentLinkNotFound,
    PaymentLinkExpired,
    PaymentLinkAlreadyUsed,
    PaymentLinkRevoked,
)

# Partial payments
from sardis_checkout.partial_payments import (
    PartialPaymentManager,
    PartialPaymentStore,
    InMemoryPartialPaymentStore,
    PartialPaymentState,
    PartialPaymentError,
    PaymentAmountTooSmall,
    PaymentAmountTooLarge,
    CheckoutAlreadyPaid,
    PartialPaymentsNotAllowed,
)

# Multi-currency
from sardis_checkout.currency import (
    CurrencyConverter,
    MultiCurrencyCheckout,
    ExchangeRateProvider,
    StaticExchangeRateProvider,
    CachedExchangeRateProvider,
    ExchangeRate,
    CurrencyError,
    UnsupportedCurrency,
    ConversionError,
    RateNotAvailable,
    DEFAULT_CURRENCIES,
)

# Sessions
from sardis_checkout.sessions import (
    SessionManager,
    SessionStore,
    InMemorySessionStore,
    SessionError,
    SessionNotFound,
    SessionExpired,
    SessionInvalid,
)

# Webhooks
from sardis_checkout.webhooks import (
    WebhookDeliveryManager,
    WebhookStore,
    InMemoryWebhookStore,
    WebhookSigner,
    RetryConfig,
    WebhookError,
    WebhookEndpointNotFound,
    WebhookDeliveryFailed,
    WebhookSignatureInvalid,
)

# Fraud detection
from sardis_checkout.fraud import (
    FraudDetector,
    FraudCheckContext,
    FraudSignalProvider,
    VelocityCheckProvider,
    GeoCheckProvider,
    AmountCheckProvider,
    EmailCheckProvider,
    FraudRuleEngine,
    FraudError,
    FraudCheckFailed,
    FraudDeclined,
)

# Connectors
from sardis_checkout.connectors import (
    PSPConnector,
    StripeConnector,
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

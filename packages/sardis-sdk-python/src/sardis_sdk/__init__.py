"""
Sardis Python SDK

A production-grade SDK for interacting with the Sardis stablecoin execution layer.

Features:
- Sync and Async clients with connection pooling
- Configurable retry with exponential backoff
- Request/response logging
- Per-request timeout configuration
- Automatic token refresh
- Comprehensive error handling with error codes
- Pagination helpers
- Bulk operation support

Quick Start:
    ```python
    from sardis_sdk import SardisClient, AsyncSardisClient

    # Async client (recommended for production)
    async with AsyncSardisClient(api_key="your-key") as client:
        agents = await client.agents.list()
        wallet = await client.wallets.get("wallet_123")

    # Sync client
    with SardisClient(api_key="your-key") as client:
        agents = client.agents.list()
        wallet = client.wallets.get("wallet_123")
    ```
"""
from __future__ import annotations

# Version
__version__ = "0.2.0"

# Core clients
from .client import (
    AsyncSardisClient,
    SardisClient,
    # Configuration classes
    LogLevel,
    PoolConfig,
    RequestContext,
    RetryConfig,
    TimeoutConfig,
    TokenInfo,
)

# Errors
from .models.errors import (
    # Base errors
    APIError,
    SardisError,
    # Authentication
    AuthenticationError,
    # Validation
    ValidationError,
    # Resources
    NotFoundError,
    # Rate limiting
    RateLimitError,
    # Balance
    InsufficientBalanceError,
    # Server errors
    BadGatewayError,
    GatewayTimeoutError,
    ServerError,
    ServiceUnavailableError,
    # Network errors
    ConnectionError,
    NetworkError,
    TimeoutError,
    # Payment errors
    HoldAlreadyCapturedError,
    HoldAlreadyVoidedError,
    HoldError,
    HoldExpiredError,
    PaymentError,
    # Blockchain errors
    BlockchainError,
    ChainNotSupportedError,
    GasEstimationError,
    TransactionFailedError,
    # Compliance errors
    ComplianceError,
    KYCRequiredError,
    PolicyViolationError,
    SanctionsCheckFailedError,
    # Error utilities
    ErrorCode,
    ErrorSeverity,
    error_from_code,
)

# Models
from .models.agent import Agent, AgentCreate, AgentUpdate, CreateAgentRequest
from .models.hold import (
    CaptureHoldRequest,
    CreateHoldRequest,
    CreateHoldResponse,
    Hold,
    HoldCreate,
    HoldStatus,
)
from .models.marketplace import (
    CreateOfferRequest,
    CreateReviewRequest,
    CreateServiceRequest,
    OfferStatus,
    Service,
    ServiceCategory,
    ServiceOffer,
    ServiceReview,
    ServiceStatus,
)
from .models.payment import (
    ExecuteAP2Request,
    ExecuteAP2Response,
    ExecuteMandateRequest,
    ExecutePaymentRequest,
    ExecutePaymentResponse,
    Payment,
    PaymentStatus,
)
from .models.wallet import (
    CreateWalletRequest,
    TokenBalance,
    TokenLimit,
    Wallet,
    WalletBalance,
    WalletCreate,
)
from .models.webhook import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    Webhook,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventType,
)
from .models.base import (
    Chain,
    ChainEnum,
    ExperimentalChain,
    MPCProvider,
    SardisModel,
    Token,
)

# Pagination
from .pagination import (
    AsyncPaginator,
    Page,
    PageInfo,
    SyncPaginator,
    create_page_from_response,
)

# Bulk operations
from .bulk import (
    AsyncBulkExecutor,
    BulkConfig,
    BulkOperationResult,
    BulkOperationSummary,
    OperationResult,
    OperationStatus,
    SyncBulkExecutor,
    bulk_execute_async,
    bulk_execute_sync,
)

__all__ = [
    # Version
    "__version__",
    # Clients
    "SardisClient",
    "AsyncSardisClient",
    # Configuration
    "RetryConfig",
    "TimeoutConfig",
    "PoolConfig",
    "LogLevel",
    "RequestContext",
    "TokenInfo",
    # Base errors
    "SardisError",
    "APIError",
    # Authentication errors
    "AuthenticationError",
    # Validation errors
    "ValidationError",
    # Resource errors
    "NotFoundError",
    # Rate limiting
    "RateLimitError",
    # Balance errors
    "InsufficientBalanceError",
    # Server errors
    "ServerError",
    "BadGatewayError",
    "ServiceUnavailableError",
    "GatewayTimeoutError",
    # Network errors
    "NetworkError",
    "ConnectionError",
    "TimeoutError",
    # Payment errors
    "PaymentError",
    "HoldError",
    "HoldExpiredError",
    "HoldAlreadyCapturedError",
    "HoldAlreadyVoidedError",
    # Blockchain errors
    "BlockchainError",
    "TransactionFailedError",
    "GasEstimationError",
    "ChainNotSupportedError",
    # Compliance errors
    "ComplianceError",
    "KYCRequiredError",
    "SanctionsCheckFailedError",
    "PolicyViolationError",
    # Error utilities
    "ErrorCode",
    "ErrorSeverity",
    "error_from_code",
    # Base models
    "SardisModel",
    "Chain",
    "ChainEnum",
    "ExperimentalChain",
    "Token",
    "MPCProvider",
    # Agent models
    "Agent",
    "AgentCreate",
    "AgentUpdate",
    "CreateAgentRequest",
    # Wallet models
    "Wallet",
    "WalletBalance",
    "WalletCreate",
    "CreateWalletRequest",
    "TokenBalance",
    "TokenLimit",
    # Payment models
    "Payment",
    "PaymentStatus",
    "ExecutePaymentRequest",
    "ExecutePaymentResponse",
    "ExecuteMandateRequest",
    "ExecuteAP2Request",
    "ExecuteAP2Response",
    # Hold models
    "Hold",
    "HoldStatus",
    "HoldCreate",
    "CreateHoldRequest",
    "CaptureHoldRequest",
    "CreateHoldResponse",
    # Webhook models
    "Webhook",
    "WebhookEvent",
    "WebhookEventType",
    "WebhookDelivery",
    "CreateWebhookRequest",
    "UpdateWebhookRequest",
    # Marketplace models
    "Service",
    "ServiceOffer",
    "ServiceReview",
    "ServiceCategory",
    "ServiceStatus",
    "OfferStatus",
    "CreateServiceRequest",
    "CreateOfferRequest",
    "CreateReviewRequest",
    # Pagination
    "PageInfo",
    "Page",
    "AsyncPaginator",
    "SyncPaginator",
    "create_page_from_response",
    # Bulk operations
    "OperationStatus",
    "OperationResult",
    "BulkOperationSummary",
    "BulkOperationResult",
    "BulkConfig",
    "AsyncBulkExecutor",
    "SyncBulkExecutor",
    "bulk_execute_async",
    "bulk_execute_sync",
]

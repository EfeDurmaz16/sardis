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
__version__ = "1.0.0"

# Core clients
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
from .client import (
    AsyncSardisClient,
    # Configuration classes
    LogLevel,
    PoolConfig,
    RequestContext,
    RetryConfig,
    SardisClient,
    TimeoutConfig,
    TokenInfo,
)

# Models
from .models.agent import Agent, AgentCreate, AgentUpdate, CreateAgentRequest
from .models.base import (
    Chain,
    ChainEnum,
    ExperimentalChain,
    MPCProvider,
    SardisModel,
    Token,
)
from .models.card import (
    Card,
    CardTransaction,
    SimulateCardPurchaseResponse,
)

# Errors
from .models.errors import (
    # Base errors
    APIError,
    # Authentication
    AuthenticationError,
    # Server errors
    BadGatewayError,
    # Blockchain errors
    BlockchainError,
    ChainNotSupportedError,
    # Compliance errors
    ComplianceError,
    # Network errors
    ConnectionError,
    # Error utilities
    ErrorCode,
    ErrorSeverity,
    GasEstimationError,
    GatewayTimeoutError,
    # Payment errors
    HoldAlreadyCapturedError,
    HoldAlreadyVoidedError,
    HoldError,
    HoldExpiredError,
    # Balance
    InsufficientBalanceError,
    KYCRequiredError,
    NetworkError,
    # Resources
    NotFoundError,
    PaymentError,
    PolicyViolationError,
    # Rate limiting
    RateLimitError,
    SanctionsCheckFailedError,
    SardisError,
    ServerError,
    ServiceUnavailableError,
    TimeoutError,
    TransactionFailedError,
    # Validation
    ValidationError,
    error_from_code,
)
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
from .models.policy import (
    ApplyPolicyFromNLResponse,
    ParsedPolicy,
    PolicyCheckResponse,
    PolicyExample,
    PolicyPreviewResponse,
)
from .models.treasury import (
    CreateExternalBankAccountRequest,
    ExternalBankAccount,
    FinancialAccount,
    SyncAccountHolderRequest,
    TreasuryAddress,
    TreasuryBalance,
    TreasuryPaymentRequest,
    TreasuryPaymentResponse,
    VerifyMicroDepositsRequest,
)
from .models.wallet import (
    CreateWalletRequest,
    TokenBalance,
    TokenLimit,
    Wallet,
    WalletBalance,
    WalletCreate,
    WalletTransferRequest,
    WalletTransferResponse,
)
from .models.webhook import (
    CreateWebhookRequest,
    UpdateWebhookRequest,
    Webhook,
    WebhookDelivery,
    WebhookEvent,
    WebhookEventType,
)

# Pagination
from .pagination import (
    AsyncPaginator,
    Page,
    PageInfo,
    SyncPaginator,
    create_page_from_response,
)

__all__ = [
    "APIError",
    # Agent models
    "Agent",
    "AgentCreate",
    "AgentUpdate",
    "ApplyPolicyFromNLResponse",
    "AsyncBulkExecutor",
    "AsyncPaginator",
    "AsyncSardisClient",
    # Authentication errors
    "AuthenticationError",
    "BadGatewayError",
    # Blockchain errors
    "BlockchainError",
    "BulkConfig",
    "BulkOperationResult",
    "BulkOperationSummary",
    "CaptureHoldRequest",
    # Card models
    "Card",
    "CardTransaction",
    "Chain",
    "ChainEnum",
    "ChainNotSupportedError",
    # Compliance errors
    "ComplianceError",
    "ConnectionError",
    "CreateAgentRequest",
    "CreateExternalBankAccountRequest",
    "CreateHoldRequest",
    "CreateHoldResponse",
    "CreateOfferRequest",
    "CreateReviewRequest",
    "CreateServiceRequest",
    "CreateWalletRequest",
    "CreateWebhookRequest",
    # Error utilities
    "ErrorCode",
    "ErrorSeverity",
    "ExecuteAP2Request",
    "ExecuteAP2Response",
    "ExecuteMandateRequest",
    "ExecutePaymentRequest",
    "ExecutePaymentResponse",
    "ExperimentalChain",
    "ExternalBankAccount",
    # Treasury models
    "FinancialAccount",
    "GasEstimationError",
    "GatewayTimeoutError",
    # Hold models
    "Hold",
    "HoldAlreadyCapturedError",
    "HoldAlreadyVoidedError",
    "HoldCreate",
    "HoldError",
    "HoldExpiredError",
    "HoldStatus",
    # Balance errors
    "InsufficientBalanceError",
    "KYCRequiredError",
    "LogLevel",
    "MPCProvider",
    # Network errors
    "NetworkError",
    # Resource errors
    "NotFoundError",
    "OfferStatus",
    "OperationResult",
    # Bulk operations
    "OperationStatus",
    "Page",
    # Pagination
    "PageInfo",
    # Policy models
    "ParsedPolicy",
    # Payment models
    "Payment",
    # Payment errors
    "PaymentError",
    "PaymentStatus",
    "PolicyCheckResponse",
    "PolicyExample",
    "PolicyPreviewResponse",
    "PolicyViolationError",
    "PoolConfig",
    # Rate limiting
    "RateLimitError",
    "RequestContext",
    # Configuration
    "RetryConfig",
    "SanctionsCheckFailedError",
    # Clients
    "SardisClient",
    # Base errors
    "SardisError",
    # Base models
    "SardisModel",
    # Server errors
    "ServerError",
    # Marketplace models
    "Service",
    "ServiceCategory",
    "ServiceOffer",
    "ServiceReview",
    "ServiceStatus",
    "ServiceUnavailableError",
    "SimulateCardPurchaseResponse",
    "SyncAccountHolderRequest",
    "SyncBulkExecutor",
    "SyncPaginator",
    "TimeoutConfig",
    "TimeoutError",
    "Token",
    "TokenBalance",
    "TokenInfo",
    "TokenLimit",
    "TransactionFailedError",
    "TreasuryAddress",
    "TreasuryBalance",
    "TreasuryPaymentRequest",
    "TreasuryPaymentResponse",
    "UpdateWebhookRequest",
    # Validation errors
    "ValidationError",
    "VerifyMicroDepositsRequest",
    # Wallet models
    "Wallet",
    "WalletBalance",
    "WalletCreate",
    "WalletTransferRequest",
    "WalletTransferResponse",
    # Webhook models
    "Webhook",
    "WebhookDelivery",
    "WebhookEvent",
    "WebhookEventType",
    # Version
    "__version__",
    "bulk_execute_async",
    "bulk_execute_sync",
    "create_page_from_response",
    "error_from_code",
]

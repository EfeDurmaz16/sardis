"""
Sardis Python SDK - Production-Grade Client

A comprehensive SDK for interacting with the Sardis stablecoin execution layer.

Features:
- Connection pooling via httpx
- Sync and Async clients
- Configurable retry with exponential backoff
- Request/response logging
- Per-request timeout configuration
- Automatic token refresh
- Comprehensive error handling

Example usage:
    ```python
    from sardis_sdk import SardisClient, AsyncSardisClient

    # Async client (recommended)
    async with AsyncSardisClient(
        api_key="your-api-key",
        base_url="https://api.sardis.sh",
    ) as client:
        result = await client.payments.execute_mandate(mandate)

    # Sync client
    with SardisClient(
        api_key="your-api-key",
        base_url="https://api.sardis.sh",
    ) as client:
        result = client.payments.execute_mandate(mandate)
    ```
"""
from __future__ import annotations

import asyncio
import logging
import random
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncIterator,
    Callable,
    Dict,
    Generic,
    Iterator,
    List,
    Literal,
    Optional,
    TypeVar,
    Union,
    overload,
)

import httpx

from .models.errors import (
    APIError,
    AuthenticationError,
    ConnectionError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    SardisError,
    TimeoutError,
    ValidationError,
)

if TYPE_CHECKING:
    from .resources.agents import AgentsResource, AsyncAgentsResource
    from .resources.cards import AsyncCardsResource, CardsResource
    from .resources.groups import AsyncGroupsResource, GroupsResource
    from .resources.holds import AsyncHoldsResource, HoldsResource
    from .resources.ledger import AsyncLedgerResource, LedgerResource
    from .resources.marketplace import AsyncMarketplaceResource, MarketplaceResource
    from .resources.payments import AsyncPaymentsResource, PaymentsResource
    from .resources.policies import AsyncPoliciesResource, PoliciesResource
    from .resources.transactions import AsyncTransactionsResource, TransactionsResource
    from .resources.treasury import AsyncTreasuryResource, TreasuryResource
    from .resources.wallets import AsyncWalletsResource, WalletsResource
    from .resources.webhooks import AsyncWebhooksResource, WebhooksResource

# Configure module logger
logger = logging.getLogger("sardis_sdk")

# Type variable for generic responses
T = TypeVar("T")

# SDK Version
__version__ = "1.0.0"


class LogLevel(str, Enum):
    """Log levels for request/response logging."""

    NONE = "none"
    BASIC = "basic"  # Log method, URL, status
    HEADERS = "headers"  # Log headers too
    BODY = "body"  # Log full request/response bodies


@dataclass(frozen=True)
class RetryConfig:
    """Configuration for retry behavior.

    Attributes:
        max_retries: Maximum number of retry attempts (default: 3)
        initial_delay: Initial delay between retries in seconds (default: 0.5)
        max_delay: Maximum delay between retries in seconds (default: 30.0)
        exponential_base: Base for exponential backoff (default: 2.0)
        jitter: Whether to add random jitter to delays (default: True)
        retry_on_status: HTTP status codes to retry on
        retry_on_exceptions: Exception types to retry on
    """

    max_retries: int = 3
    initial_delay: float = 0.5
    max_delay: float = 30.0
    exponential_base: float = 2.0
    jitter: bool = True
    retry_on_status: tuple[int, ...] = (429, 500, 502, 503, 504)
    retry_on_exceptions: tuple[type[Exception], ...] = (
        httpx.TimeoutException,
        httpx.ConnectError,
        httpx.ReadError,
        httpx.WriteError,
    )

    def calculate_delay(self, attempt: int) -> float:
        """Calculate delay for a given retry attempt."""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        if self.jitter:
            delay = delay * (0.5 + random.random())
        return delay


@dataclass
class TimeoutConfig:
    """Configuration for request timeouts.

    Attributes:
        connect: Timeout for establishing connection (seconds)
        read: Timeout for reading response (seconds)
        write: Timeout for writing request (seconds)
        pool: Timeout for acquiring connection from pool (seconds)
    """

    connect: float = 10.0
    read: float = 30.0
    write: float = 30.0
    pool: float = 10.0

    def to_httpx_timeout(self) -> httpx.Timeout:
        """Convert to httpx Timeout object."""
        return httpx.Timeout(
            connect=self.connect,
            read=self.read,
            write=self.write,
            pool=self.pool,
        )


@dataclass
class PoolConfig:
    """Configuration for connection pooling.

    Attributes:
        max_connections: Maximum number of connections in pool
        max_keepalive_connections: Maximum keepalive connections
        keepalive_expiry: Time to keep idle connections alive (seconds)
    """

    max_connections: int = 100
    max_keepalive_connections: int = 20
    keepalive_expiry: float = 30.0

    def to_httpx_limits(self) -> httpx.Limits:
        """Convert to httpx Limits object."""
        return httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry,
        )


@dataclass
class TokenInfo:
    """Information about an API token.

    Attributes:
        access_token: The current access token
        refresh_token: Optional refresh token
        expires_at: When the token expires (if known)
        token_type: Type of token (usually "Bearer")
    """

    access_token: str
    refresh_token: Optional[str] = None
    expires_at: Optional[datetime] = None
    token_type: str = "Bearer"

    @property
    def is_expired(self) -> bool:
        """Check if the token is expired."""
        if self.expires_at is None:
            return False
        # Consider token expired 5 minutes before actual expiry
        return datetime.utcnow() >= self.expires_at - timedelta(minutes=5)


@dataclass
class RequestContext:
    """Context for a single request.

    Attributes:
        request_id: Unique identifier for the request
        timeout: Optional per-request timeout override
        idempotency_key: Optional idempotency key for POST/PUT requests
        metadata: Additional metadata to include in logs
    """

    request_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timeout: Optional[TimeoutConfig] = None
    idempotency_key: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class RequestLogger:
    """Logger for HTTP requests and responses."""

    def __init__(self, log_level: LogLevel = LogLevel.BASIC):
        self.log_level = log_level
        self._logger = logging.getLogger("sardis_sdk.http")

    def log_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        context: Optional[RequestContext] = None,
    ) -> None:
        """Log an outgoing request."""
        if self.log_level == LogLevel.NONE:
            return

        request_id = context.request_id if context else "unknown"

        if self.log_level == LogLevel.BASIC:
            self._logger.info(
                "[%s] Request: %s %s",
                request_id,
                method,
                url,
            )
        elif self.log_level == LogLevel.HEADERS:
            self._logger.info(
                "[%s] Request: %s %s\nHeaders: %s",
                request_id,
                method,
                url,
                self._sanitize_headers(headers or {}),
            )
        elif self.log_level == LogLevel.BODY:
            self._logger.info(
                "[%s] Request: %s %s\nHeaders: %s\nBody: %s",
                request_id,
                method,
                url,
                self._sanitize_headers(headers or {}),
                self._truncate_body(body),
            )

    def log_response(
        self,
        status_code: int,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[Any] = None,
        duration_ms: float = 0,
        context: Optional[RequestContext] = None,
    ) -> None:
        """Log an incoming response."""
        if self.log_level == LogLevel.NONE:
            return

        request_id = context.request_id if context else "unknown"

        if self.log_level == LogLevel.BASIC:
            self._logger.info(
                "[%s] Response: %d (%dms)",
                request_id,
                status_code,
                duration_ms,
            )
        elif self.log_level == LogLevel.HEADERS:
            self._logger.info(
                "[%s] Response: %d (%dms)\nHeaders: %s",
                request_id,
                status_code,
                duration_ms,
                dict(headers) if headers else {},
            )
        elif self.log_level == LogLevel.BODY:
            self._logger.info(
                "[%s] Response: %d (%dms)\nHeaders: %s\nBody: %s",
                request_id,
                status_code,
                duration_ms,
                dict(headers) if headers else {},
                self._truncate_body(body),
            )

    def log_retry(
        self,
        attempt: int,
        delay: float,
        reason: str,
        context: Optional[RequestContext] = None,
    ) -> None:
        """Log a retry attempt."""
        request_id = context.request_id if context else "unknown"
        self._logger.warning(
            "[%s] Retry attempt %d after %.2fs: %s",
            request_id,
            attempt,
            delay,
            reason,
        )

    def _sanitize_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Remove sensitive headers from logs."""
        sensitive_keys = {"authorization", "x-api-key", "api-key", "cookie", "set-cookie"}
        return {
            k: "[REDACTED]" if k.lower() in sensitive_keys else v
            for k, v in headers.items()
        }

    def _truncate_body(self, body: Any, max_length: int = 1000) -> str:
        """Truncate body for logging."""
        if body is None:
            return "null"
        body_str = str(body)
        if len(body_str) > max_length:
            return body_str[:max_length] + "... [truncated]"
        return body_str


class BaseClient:
    """Base class with shared configuration for sync and async clients."""

    DEFAULT_BASE_URL = "https://api.sardis.sh"

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        retry: Optional[RetryConfig] = None,
        pool: Optional[PoolConfig] = None,
        log_level: LogLevel = LogLevel.BASIC,
        token_refresh_callback: Optional[Callable[[], str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the base client.

        Args:
            api_key: Your Sardis API key (required)
            base_url: API base URL (default: https://api.sardis.sh)
            timeout: Request timeout configuration
            retry: Retry configuration
            pool: Connection pool configuration
            log_level: Logging verbosity level
            token_refresh_callback: Optional callback to refresh API token
            default_headers: Additional headers to include in all requests
        """
        if not api_key:
            raise ValueError("API key is required")

        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

        # Configure timeout
        if timeout is None:
            self._timeout = TimeoutConfig()
        elif isinstance(timeout, (int, float)):
            self._timeout = TimeoutConfig(
                connect=float(timeout),
                read=float(timeout),
                write=float(timeout),
            )
        else:
            self._timeout = timeout

        # Configure retry
        self._retry = retry or RetryConfig()

        # Configure pool
        self._pool = pool or PoolConfig()

        # Configure logging
        self._request_logger = RequestLogger(log_level)

        # Token refresh
        self._token_refresh_callback = token_refresh_callback
        self._token_info: Optional[TokenInfo] = None

        # Default headers
        self._default_headers = {
            "X-API-Key": self._api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": f"sardis-sdk-python/{__version__}",
            **(default_headers or {}),
        }

    def _get_headers(
        self,
        context: Optional[RequestContext] = None,
        extra_headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """Build headers for a request."""
        headers = self._default_headers.copy()

        if context:
            headers["X-Request-ID"] = context.request_id
            if context.idempotency_key:
                headers["Idempotency-Key"] = context.idempotency_key

        if extra_headers:
            headers.update(extra_headers)

        return headers

    def _build_url(self, path: str) -> str:
        """Build full URL from path."""
        if path.startswith(("http://", "https://")):
            return path

        # Add /api/v2/ prefix for resource paths
        if not path.startswith("/"):
            path = f"/api/v2/{path}"

        return f"{self._base_url}{path}"

    def _handle_error_response(
        self,
        response: httpx.Response,
        context: Optional[RequestContext] = None,
    ) -> None:
        """Handle error responses and raise appropriate exceptions."""
        status_code = response.status_code
        request_id = context.request_id if context else None

        try:
            body = response.json()
        except Exception:
            body = {"detail": response.text}

        # Some frameworks return validation errors as a bare list.
        if isinstance(body, list):
            body = {"detail": body}

        # Extract error details
        error_data = body.get("error", body.get("detail", body))

        if isinstance(error_data, str):
            message = error_data
            code = None
            details = None
        elif isinstance(error_data, list):
            message = "Validation Error"
            code = "VALIDATION_ERROR"
            details = {"errors": error_data}
        else:
            message = error_data.get("message", "Unknown error")
            code = error_data.get("code")
            details = error_data.get("details")

        # Map status codes to exceptions
        if status_code == 401:
            raise AuthenticationError(message, request_id=request_id)
        elif status_code == 403:
            raise AuthenticationError(
                message or "Forbidden",
                code="FORBIDDEN",
                request_id=request_id,
            )
        elif status_code == 404:
            raise NotFoundError(
                resource_type="Resource",
                resource_id="unknown",
                message=message,
                request_id=request_id,
            )
        elif status_code == 422:
            raise ValidationError(message, details=details, request_id=request_id)
        elif status_code == 429:
            retry_after = int(response.headers.get("Retry-After", "5"))
            raise RateLimitError(
                message or "Rate limit exceeded",
                retry_after=retry_after,
                request_id=request_id,
            )
        else:
            raise APIError(
                message=message,
                status_code=status_code,
                code=code,
                details=details,
                request_id=request_id,
            )


class AsyncSardisClient(BaseClient):
    """Asynchronous Sardis API client with connection pooling and retry logic.

    This is the recommended client for production use. It provides:
    - Connection pooling for better performance
    - Automatic retries with exponential backoff
    - Request/response logging
    - Per-request timeout configuration
    - Automatic token refresh

    Example:
        ```python
        async with AsyncSardisClient(api_key="your-key") as client:
            agents = await client.agents.list()
            wallet = await client.wallets.get("wallet_123")
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BaseClient.DEFAULT_BASE_URL,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        retry: Optional[RetryConfig] = None,
        pool: Optional[PoolConfig] = None,
        log_level: LogLevel = LogLevel.BASIC,
        token_refresh_callback: Optional[Callable[[], str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the async client.

        Args:
            api_key: Your Sardis API key (required)
            base_url: API base URL (default: https://api.sardis.sh)
            timeout: Request timeout configuration
            retry: Retry configuration
            pool: Connection pool configuration
            log_level: Logging verbosity level
            token_refresh_callback: Optional callback to refresh API token
            default_headers: Additional headers to include in all requests
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            retry=retry,
            pool=pool,
            log_level=log_level,
            token_refresh_callback=token_refresh_callback,
            default_headers=default_headers,
        )

        self._client: Optional[httpx.AsyncClient] = None

        # Initialize resources lazily
        self._agents: Optional["AsyncAgentsResource"] = None
        self._wallets: Optional["AsyncWalletsResource"] = None
        self._payments: Optional["AsyncPaymentsResource"] = None
        self._holds: Optional["AsyncHoldsResource"] = None
        self._cards: Optional["AsyncCardsResource"] = None
        self._policies: Optional["AsyncPoliciesResource"] = None
        self._webhooks: Optional["AsyncWebhooksResource"] = None
        self._marketplace: Optional["AsyncMarketplaceResource"] = None
        self._transactions: Optional["AsyncTransactionsResource"] = None
        self._ledger: Optional["AsyncLedgerResource"] = None
        self._groups: Optional["AsyncGroupsResource"] = None
        self._treasury: Optional["AsyncTreasuryResource"] = None

    @property
    def groups(self) -> "AsyncGroupsResource":
        """Access the groups resource."""
        if self._groups is None:
            from .resources.groups import AsyncGroupsResource
            self._groups = AsyncGroupsResource(self)
        return self._groups

    @property
    def agents(self) -> "AsyncAgentsResource":
        """Access the agents resource."""
        if self._agents is None:
            from .resources.agents import AsyncAgentsResource
            self._agents = AsyncAgentsResource(self)
        return self._agents

    @property
    def wallets(self) -> "AsyncWalletsResource":
        """Access the wallets resource."""
        if self._wallets is None:
            from .resources.wallets import AsyncWalletsResource
            self._wallets = AsyncWalletsResource(self)
        return self._wallets

    @property
    def payments(self) -> "AsyncPaymentsResource":
        """Access the payments resource."""
        if self._payments is None:
            from .resources.payments import AsyncPaymentsResource
            self._payments = AsyncPaymentsResource(self)
        return self._payments

    @property
    def holds(self) -> "AsyncHoldsResource":
        """Access the holds resource."""
        if self._holds is None:
            from .resources.holds import AsyncHoldsResource
            self._holds = AsyncHoldsResource(self)
        return self._holds

    @property
    def cards(self) -> "AsyncCardsResource":
        """Access the cards resource."""
        if self._cards is None:
            from .resources.cards import AsyncCardsResource
            self._cards = AsyncCardsResource(self)
        return self._cards

    @property
    def policies(self) -> "AsyncPoliciesResource":
        """Access the policies resource."""
        if self._policies is None:
            from .resources.policies import AsyncPoliciesResource
            self._policies = AsyncPoliciesResource(self)
        return self._policies

    @property
    def webhooks(self) -> "AsyncWebhooksResource":
        """Access the webhooks resource."""
        if self._webhooks is None:
            from .resources.webhooks import AsyncWebhooksResource
            self._webhooks = AsyncWebhooksResource(self)
        return self._webhooks

    @property
    def marketplace(self) -> "AsyncMarketplaceResource":
        """Access the marketplace resource."""
        if self._marketplace is None:
            from .resources.marketplace import AsyncMarketplaceResource
            self._marketplace = AsyncMarketplaceResource(self)
        return self._marketplace

    @property
    def transactions(self) -> "AsyncTransactionsResource":
        """Access the transactions resource."""
        if self._transactions is None:
            from .resources.transactions import AsyncTransactionsResource
            self._transactions = AsyncTransactionsResource(self)
        return self._transactions

    @property
    def ledger(self) -> "AsyncLedgerResource":
        """Access the ledger resource."""
        if self._ledger is None:
            from .resources.ledger import AsyncLedgerResource
            self._ledger = AsyncLedgerResource(self)
        return self._ledger

    @property
    def treasury(self) -> "AsyncTreasuryResource":
        """Access the treasury resource."""
        if self._treasury is None:
            from .resources.treasury import AsyncTreasuryResource
            self._treasury = AsyncTreasuryResource(self)
        return self._treasury

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            try:
                self._client = httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout.to_httpx_timeout(),
                    limits=self._pool.to_httpx_limits(),
                    http2=True,  # Enable HTTP/2 for better performance
                )
            except ImportError:
                logger.warning(
                    "HTTP/2 dependencies not available; falling back to HTTP/1.1"
                )
                self._client = httpx.AsyncClient(
                    base_url=self._base_url,
                    timeout=self._timeout.to_httpx_timeout(),
                    limits=self._pool.to_httpx_limits(),
                    http2=False,
                )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        context: Optional[RequestContext] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            params: Query parameters
            json: JSON body
            headers: Additional headers
            context: Request context for logging and tracking
            timeout: Per-request timeout override

        Returns:
            Response JSON as dictionary

        Raises:
            SardisError: On API errors
            TimeoutError: On request timeout
            NetworkError: On network errors
        """
        context = context or RequestContext()
        client = await self._get_client()
        url = self._build_url(path)
        request_headers = self._get_headers(context, headers)

        # Determine timeout
        if timeout is not None:
            if isinstance(timeout, (int, float)):
                request_timeout = httpx.Timeout(timeout)
            else:
                request_timeout = timeout.to_httpx_timeout()
        elif context.timeout:
            request_timeout = context.timeout.to_httpx_timeout()
        else:
            request_timeout = self._timeout.to_httpx_timeout()

        last_error: Optional[Exception] = None

        for attempt in range(self._retry.max_retries + 1):
            start_time = time.monotonic()

            try:
                # Log request
                self._request_logger.log_request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    body=json,
                    context=context,
                )

                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=request_headers,
                    timeout=request_timeout,
                )

                duration_ms = (time.monotonic() - start_time) * 1000

                # Log response
                try:
                    response_body = response.json() if response.content else None
                except Exception:
                    response_body = response.text

                self._request_logger.log_response(
                    status_code=response.status_code,
                    url=url,
                    headers=dict(response.headers),
                    body=response_body,
                    duration_ms=duration_ms,
                    context=context,
                )

                # Check for retryable status codes
                if response.status_code in self._retry.retry_on_status:
                    if attempt < self._retry.max_retries:
                        delay = self._retry.calculate_delay(attempt)

                        # Special handling for rate limits
                        if response.status_code == 429:
                            retry_after = int(response.headers.get("Retry-After", str(delay)))
                            delay = max(delay, retry_after)

                        self._request_logger.log_retry(
                            attempt=attempt + 1,
                            delay=delay,
                            reason=f"Status {response.status_code}",
                            context=context,
                        )
                        await asyncio.sleep(delay)
                        continue

                # Handle error responses
                if response.status_code >= 400:
                    self._handle_error_response(response, context)

                return response.json()

            except self._retry.retry_on_exceptions as e:
                last_error = e

                if attempt < self._retry.max_retries:
                    delay = self._retry.calculate_delay(attempt)
                    self._request_logger.log_retry(
                        attempt=attempt + 1,
                        delay=delay,
                        reason=str(e),
                        context=context,
                    )
                    await asyncio.sleep(delay)
                    continue

                # Convert to appropriate error type
                if isinstance(e, httpx.TimeoutException):
                    raise TimeoutError(
                        f"Request timed out after {request_timeout}",
                        request_id=context.request_id,
                    ) from e
                elif isinstance(e, httpx.ConnectError):
                    raise ConnectionError(
                        f"Failed to connect to {url}",
                        request_id=context.request_id,
                    ) from e
                else:
                    raise NetworkError(
                        f"Network error: {e}",
                        request_id=context.request_id,
                    ) from e

            except SardisError:
                raise

            except Exception as e:
                raise SardisError(
                    f"Unexpected error: {e}",
                    request_id=context.request_id,
                ) from e

        # Should not reach here, but handle edge case
        if last_error:
            raise NetworkError(
                f"Max retries exceeded: {last_error}",
                request_id=context.request_id,
            ) from last_error

        raise SardisError(
            "Unexpected error in request retry loop",
            request_id=context.request_id,
        )

    async def health(self) -> Dict[str, Any]:
        """Check API health status.

        Returns:
            Health status information
        """
        return await self._request("GET", "/health")

    async def execute_payment(
        self,
        mandate: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Legacy convenience wrapper for executing a single mandate."""
        return await self._request(
            "POST",
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
            timeout=timeout,
        )

    async def execute_ap2_payment(
        self,
        bundle: Dict[str, Any],
        timeout: Optional[Union[float, "TimeoutConfig"]] = None,
    ) -> Dict[str, Any]:
        """Legacy convenience wrapper for executing an AP2 bundle."""
        return await self._request(
            "POST",
            "/api/v2/ap2/payments/execute",
            json=bundle,
            timeout=timeout,
        )

    async def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "AsyncSardisClient":
        """Async context manager entry."""
        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Async context manager exit."""
        await self.close()


class SardisClient(BaseClient):
    """Synchronous Sardis API client with connection pooling and retry logic.

    This client wraps the async client for synchronous usage.
    For better performance in async applications, use AsyncSardisClient.

    Example:
        ```python
        with SardisClient(api_key="your-key") as client:
            agents = client.agents.list()
            wallet = client.wallets.get("wallet_123")
        ```
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = BaseClient.DEFAULT_BASE_URL,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
        retry: Optional[RetryConfig] = None,
        pool: Optional[PoolConfig] = None,
        log_level: LogLevel = LogLevel.BASIC,
        token_refresh_callback: Optional[Callable[[], str]] = None,
        default_headers: Optional[Dict[str, str]] = None,
    ):
        """Initialize the sync client.

        Args:
            api_key: Your Sardis API key (required)
            base_url: API base URL (default: https://api.sardis.sh)
            timeout: Request timeout configuration
            retry: Retry configuration
            pool: Connection pool configuration
            log_level: Logging verbosity level
            token_refresh_callback: Optional callback to refresh API token
            default_headers: Additional headers to include in all requests
        """
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            retry=retry,
            pool=pool,
            log_level=log_level,
            token_refresh_callback=token_refresh_callback,
            default_headers=default_headers,
        )

        self._client: Optional[httpx.Client] = None

        # Initialize resources lazily
        self._agents: Optional["AgentsResource"] = None
        self._wallets: Optional["WalletsResource"] = None
        self._payments: Optional["PaymentsResource"] = None
        self._holds: Optional["HoldsResource"] = None
        self._cards: Optional["CardsResource"] = None
        self._policies: Optional["PoliciesResource"] = None
        self._webhooks: Optional["WebhooksResource"] = None
        self._marketplace: Optional["MarketplaceResource"] = None
        self._transactions: Optional["TransactionsResource"] = None
        self._ledger: Optional["LedgerResource"] = None
        self._groups: Optional["GroupsResource"] = None
        self._treasury: Optional["TreasuryResource"] = None

    @property
    def groups(self) -> "GroupsResource":
        """Access the groups resource."""
        if self._groups is None:
            from .resources.groups import GroupsResource
            self._groups = GroupsResource(self)
        return self._groups

    @property
    def agents(self) -> "AgentsResource":
        """Access the agents resource."""
        if self._agents is None:
            from .resources.agents import AgentsResource
            self._agents = AgentsResource(self)
        return self._agents

    @property
    def wallets(self) -> "WalletsResource":
        """Access the wallets resource."""
        if self._wallets is None:
            from .resources.wallets import WalletsResource
            self._wallets = WalletsResource(self)
        return self._wallets

    @property
    def payments(self) -> "PaymentsResource":
        """Access the payments resource."""
        if self._payments is None:
            from .resources.payments import PaymentsResource
            self._payments = PaymentsResource(self)
        return self._payments

    @property
    def holds(self) -> "HoldsResource":
        """Access the holds resource."""
        if self._holds is None:
            from .resources.holds import HoldsResource
            self._holds = HoldsResource(self)
        return self._holds

    @property
    def cards(self) -> "CardsResource":
        """Access the cards resource."""
        if self._cards is None:
            from .resources.cards import CardsResource
            self._cards = CardsResource(self)
        return self._cards

    @property
    def policies(self) -> "PoliciesResource":
        """Access the policies resource."""
        if self._policies is None:
            from .resources.policies import PoliciesResource
            self._policies = PoliciesResource(self)
        return self._policies

    @property
    def webhooks(self) -> "WebhooksResource":
        """Access the webhooks resource."""
        if self._webhooks is None:
            from .resources.webhooks import WebhooksResource
            self._webhooks = WebhooksResource(self)
        return self._webhooks

    @property
    def marketplace(self) -> "MarketplaceResource":
        """Access the marketplace resource."""
        if self._marketplace is None:
            from .resources.marketplace import MarketplaceResource
            self._marketplace = MarketplaceResource(self)
        return self._marketplace

    @property
    def transactions(self) -> "TransactionsResource":
        """Access the transactions resource."""
        if self._transactions is None:
            from .resources.transactions import TransactionsResource
            self._transactions = TransactionsResource(self)
        return self._transactions

    @property
    def ledger(self) -> "LedgerResource":
        """Access the ledger resource."""
        if self._ledger is None:
            from .resources.ledger import LedgerResource
            self._ledger = LedgerResource(self)
        return self._ledger

    @property
    def treasury(self) -> "TreasuryResource":
        """Access the treasury resource."""
        if self._treasury is None:
            from .resources.treasury import TreasuryResource
            self._treasury = TreasuryResource(self)
        return self._treasury

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client with connection pooling."""
        if self._client is None or self._client.is_closed:
            try:
                self._client = httpx.Client(
                    base_url=self._base_url,
                    timeout=self._timeout.to_httpx_timeout(),
                    limits=self._pool.to_httpx_limits(),
                    http2=True,
                )
            except ImportError:
                logger.warning(
                    "HTTP/2 dependencies not available; falling back to HTTP/1.1"
                )
                self._client = httpx.Client(
                    base_url=self._base_url,
                    timeout=self._timeout.to_httpx_timeout(),
                    limits=self._pool.to_httpx_limits(),
                    http2=False,
                )
        return self._client

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        context: Optional[RequestContext] = None,
        timeout: Optional[Union[float, TimeoutConfig]] = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request with retry logic.

        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path
            params: Query parameters
            json: JSON body
            headers: Additional headers
            context: Request context for logging and tracking
            timeout: Per-request timeout override

        Returns:
            Response JSON as dictionary

        Raises:
            SardisError: On API errors
            TimeoutError: On request timeout
            NetworkError: On network errors
        """
        context = context or RequestContext()
        client = self._get_client()
        url = self._build_url(path)
        request_headers = self._get_headers(context, headers)

        # Determine timeout
        if timeout is not None:
            if isinstance(timeout, (int, float)):
                request_timeout = httpx.Timeout(timeout)
            else:
                request_timeout = timeout.to_httpx_timeout()
        elif context.timeout:
            request_timeout = context.timeout.to_httpx_timeout()
        else:
            request_timeout = self._timeout.to_httpx_timeout()

        last_error: Optional[Exception] = None

        for attempt in range(self._retry.max_retries + 1):
            start_time = time.monotonic()

            try:
                # Log request
                self._request_logger.log_request(
                    method=method,
                    url=url,
                    headers=request_headers,
                    body=json,
                    context=context,
                )

                response = client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json,
                    headers=request_headers,
                    timeout=request_timeout,
                )

                duration_ms = (time.monotonic() - start_time) * 1000

                # Log response
                try:
                    response_body = response.json() if response.content else None
                except Exception:
                    response_body = response.text

                self._request_logger.log_response(
                    status_code=response.status_code,
                    url=url,
                    headers=dict(response.headers),
                    body=response_body,
                    duration_ms=duration_ms,
                    context=context,
                )

                # Check for retryable status codes
                if response.status_code in self._retry.retry_on_status:
                    if attempt < self._retry.max_retries:
                        delay = self._retry.calculate_delay(attempt)

                        # Special handling for rate limits
                        if response.status_code == 429:
                            retry_after = int(response.headers.get("Retry-After", str(delay)))
                            delay = max(delay, retry_after)

                        self._request_logger.log_retry(
                            attempt=attempt + 1,
                            delay=delay,
                            reason=f"Status {response.status_code}",
                            context=context,
                        )
                        time.sleep(delay)
                        continue

                # Handle error responses
                if response.status_code >= 400:
                    self._handle_error_response(response, context)

                return response.json()

            except self._retry.retry_on_exceptions as e:
                last_error = e

                if attempt < self._retry.max_retries:
                    delay = self._retry.calculate_delay(attempt)
                    self._request_logger.log_retry(
                        attempt=attempt + 1,
                        delay=delay,
                        reason=str(e),
                        context=context,
                    )
                    time.sleep(delay)
                    continue

                # Convert to appropriate error type
                if isinstance(e, httpx.TimeoutException):
                    raise TimeoutError(
                        f"Request timed out after {request_timeout}",
                        request_id=context.request_id,
                    ) from e
                elif isinstance(e, httpx.ConnectError):
                    raise ConnectionError(
                        f"Failed to connect to {url}",
                        request_id=context.request_id,
                    ) from e
                else:
                    raise NetworkError(
                        f"Network error: {e}",
                        request_id=context.request_id,
                    ) from e

            except SardisError:
                raise

            except Exception as e:
                raise SardisError(
                    f"Unexpected error: {e}",
                    request_id=context.request_id,
                ) from e

        # Should not reach here, but handle edge case
        if last_error:
            raise NetworkError(
                f"Max retries exceeded: {last_error}",
                request_id=context.request_id,
            ) from last_error

        raise SardisError(
            "Unexpected error in request retry loop",
            request_id=context.request_id,
        )

    def health(self) -> Dict[str, Any]:
        """Check API health status.

        Returns:
            Health status information
        """
        return self._request("GET", "/health")

    def execute_payment(
        self,
        mandate: Dict[str, Any],
        timeout: Optional[Union[float, TimeoutConfig]] = None,
    ) -> Dict[str, Any]:
        """Legacy convenience wrapper for executing a single mandate."""
        return self._request(
            "POST",
            "/api/v2/mandates/execute",
            json={"mandate": mandate},
            timeout=timeout,
        )

    def execute_ap2_payment(
        self,
        bundle: Dict[str, Any],
        timeout: Optional[Union[float, TimeoutConfig]] = None,
    ) -> Dict[str, Any]:
        """Legacy convenience wrapper for executing an AP2 bundle."""
        return self._request(
            "POST",
            "/api/v2/ap2/payments/execute",
            json=bundle,
            timeout=timeout,
        )

    def close(self) -> None:
        """Close the HTTP client and release resources."""
        if self._client and not self._client.is_closed:
            self._client.close()
            self._client = None

    def __enter__(self) -> "SardisClient":
        """Context manager entry."""
        return self

    def __exit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[BaseException],
        exc_tb: Optional[Any],
    ) -> None:
        """Context manager exit."""
        self.close()

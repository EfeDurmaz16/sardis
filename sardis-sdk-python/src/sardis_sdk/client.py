"""
Sardis Python SDK

A comprehensive SDK for interacting with the Sardis stablecoin execution layer.

Example usage:
    ```python
    from sardis_sdk import SardisClient
    
    async with SardisClient(
        base_url="https://api.sardis.network",
        api_key="your-api-key",
    ) as client:
        # Execute a payment
        result = await client.payments.execute_mandate(mandate)
        
        # Create a hold
        hold = await client.holds.create(
            wallet_id="wallet_123",
            amount=Decimal("100.00"),
        )
        
        # List marketplace services
        services = await client.marketplace.list_services()
    ```
"""
from __future__ import annotations

import asyncio
from typing import Any, Optional

import httpx

from .models.errors import APIError, AuthenticationError, RateLimitError
from .resources.holds import HoldsResource
from .resources.ledger import LedgerResource
from .resources.marketplace import MarketplaceResource
from .resources.payments import PaymentsResource
from .resources.transactions import TransactionsResource
from .resources.webhooks import WebhooksResource


class SardisClient:
    """
    Sardis API client.
    
    Provides access to all Sardis API resources:
    - payments: Execute mandates and AP2 payment bundles
    - holds: Create, capture, and void pre-authorization holds
    - webhooks: Manage webhook subscriptions
    - marketplace: A2A service discovery and offers
    - transactions: Gas estimation and transaction status
    - ledger: Query ledger entries
    
    Args:
        base_url: Sardis API base URL
        api_key: Your API key
        timeout: Request timeout in seconds (default: 30)
        max_retries: Maximum number of retries for failed requests (default: 3)
    """
    
    DEFAULT_BASE_URL = "https://api.sardis.network"
    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    
    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        api_key: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
    ):
        if not api_key:
            raise ValueError("API key is required")
        
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        
        # Initialize resources
        self.payments = PaymentsResource(self)
        self.holds = HoldsResource(self)
        self.webhooks = WebhooksResource(self)
        self.marketplace = MarketplaceResource(self)
        self.transactions = TransactionsResource(self)
        self.ledger = LedgerResource(self)
    
    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "X-API-Key": self._api_key,
                    "Content-Type": "application/json",
                    "User-Agent": "sardis-sdk-python/0.1.0",
                },
                timeout=self._timeout,
            )
        return self._client
    
    async def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Make an HTTP request with retry logic."""
        client = await self._get_client()
        
        last_error: Optional[Exception] = None
        
        for attempt in range(self._max_retries):
            try:
                response = await client.request(
                    method=method,
                    url=path,
                    params=params,
                    json=json,
                )
                
                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    if attempt < self._max_retries - 1:
                        await asyncio.sleep(retry_after)
                        continue
                    raise RateLimitError(
                        "Rate limit exceeded",
                        retry_after=retry_after,
                    )
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise AuthenticationError()
                
                # Handle other errors
                if response.status_code >= 400:
                    try:
                        body = response.json()
                    except Exception:
                        body = {"detail": response.text}
                    raise APIError.from_response(response.status_code, body)
                
                return response.json()
                
            except httpx.TimeoutException as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                raise
            except httpx.RequestError as e:
                last_error = e
                if attempt < self._max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise
        
        if last_error:
            raise last_error
        raise RuntimeError("Unexpected error in request retry loop")
    
    async def health(self) -> dict[str, Any]:
        """Check API health status."""
        return await self._request("GET", "/health")
    
    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
    
    async def __aenter__(self) -> "SardisClient":
        """Async context manager entry."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit."""
        await self.close()
    
    # ==================== Legacy Methods (for backwards compatibility) ====================
    
    async def execute_payment(self, mandate: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a single payment mandate.
        
        Deprecated: Use `client.payments.execute_mandate()` instead.
        """
        return (await self.payments.execute_mandate(mandate)).to_dict()
    
    async def execute_ap2_payment(self, bundle: dict[str, Any]) -> dict[str, Any]:
        """
        Execute a full AP2 mandate bundle.
        
        Deprecated: Use `client.payments.execute_ap2_bundle()` instead.
        """
        return (await self.payments.execute_ap2_bundle(bundle)).to_dict()

"""Striga API HTTP client with HMAC-SHA256 request signing."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from .config import StrigaConfig
from .exceptions import (
    StrigaAuthError,
    StrigaError,
    StrigaRateLimitError,
    StrigaValidationError,
)

logger = logging.getLogger(__name__)


class StrigaClient:
    """
    Core HTTP client for Striga API.

    Implements HMAC-SHA256 request signing per Striga's auth spec.
    Pattern follows BridgeOfframpProvider._make_request.
    """

    def __init__(self, config: StrigaConfig):
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client

    def _sign_request(
        self, timestamp: str, method: str, path: str, body: str = ""
    ) -> str:
        """Generate HMAC-SHA256 signature for API request."""
        message = f"{timestamp}{method}{path}{body}"
        return hmac.new(
            self._config.api_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Striga API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            path: API path (e.g., /v1/wallets)
            body: Optional JSON body
            params: Optional query parameters

        Returns:
            Parsed JSON response

        Raises:
            StrigaAuthError: On 401/403
            StrigaValidationError: On 400/422
            StrigaRateLimitError: On 429
            StrigaError: On other errors
        """
        client = await self._get_client()
        timestamp = str(int(time.time()))
        body_str = json.dumps(body) if body else ""

        signature = self._sign_request(timestamp, method.upper(), path, body_str)

        headers = {
            "Content-Type": "application/json",
            "Api-Key": self._config.api_key,
            "Api-Timestamp": timestamp,
            "Api-Signature": signature,
        }

        url = f"{self._config.base_url}{path}"

        try:
            if method.upper() == "GET":
                response = await client.get(url, headers=headers, params=params)
            elif method.upper() == "DELETE":
                response = await client.delete(url, headers=headers)
            elif method.upper() == "PUT":
                response = await client.put(url, content=body_str, headers=headers)
            else:
                response = await client.post(url, content=body_str, headers=headers)

            self._handle_error_response(response)
            return response.json()

        except (StrigaError, StrigaAuthError, StrigaValidationError, StrigaRateLimitError):
            raise
        except httpx.HTTPStatusError as e:
            raise StrigaError(
                f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            raise StrigaError(f"Request failed: {e}") from e

    def _handle_error_response(self, response: httpx.Response) -> None:
        """Check response for errors and raise appropriate exceptions."""
        if response.is_success:
            return

        try:
            error_body = response.json()
        except Exception:
            error_body = {"message": response.text}

        message = error_body.get("message", f"HTTP {response.status_code}")
        status = response.status_code

        if status in (401, 403):
            raise StrigaAuthError(message, status_code=status, response=error_body)
        elif status == 429:
            raise StrigaRateLimitError(message, status_code=status, response=error_body)
        elif status in (400, 422):
            raise StrigaValidationError(message, status_code=status, response=error_body)
        else:
            raise StrigaError(message, status_code=status, response=error_body)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

"""Lightspark Grid API HTTP client."""
from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

import httpx

from .config import LightsparkConfig
from .exceptions import (
    GridAuthError,
    GridError,
    GridRateLimitError,
    GridValidationError,
)

logger = logging.getLogger(__name__)


class GridClient:
    """
    HTTP client for Lightspark Grid API.

    Implements quote→execute flow with X-Grid-Signature webhook verification.
    """

    def __init__(self, config: LightsparkConfig):
        self._config = config
        self._http_client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30)
        return self._http_client

    def _auth_headers(self) -> dict[str, str]:
        """Generate authentication headers."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self._config.api_key}",
        }

    async def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make authenticated request to Grid API.

        Args:
            method: HTTP method
            path: API path
            body: Optional JSON body
            params: Optional query parameters

        Returns:
            Parsed JSON response
        """
        client = await self._get_client()
        headers = self._auth_headers()
        url = f"{self._config.base_url}{path}"
        body_str = json.dumps(body) if body else None

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

        except (GridError, GridAuthError, GridValidationError, GridRateLimitError):
            raise
        except httpx.HTTPStatusError as e:
            raise GridError(
                f"HTTP error: {e.response.status_code}",
                status_code=e.response.status_code,
            ) from e
        except Exception as e:
            raise GridError(f"Request failed: {e}") from e

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
            raise GridAuthError(message, status_code=status, response=error_body)
        elif status == 429:
            raise GridRateLimitError(message, status_code=status, response=error_body)
        elif status in (400, 422):
            raise GridValidationError(message, status_code=status, response=error_body)
        else:
            raise GridError(message, status_code=status, response=error_body)

    async def close(self) -> None:
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()

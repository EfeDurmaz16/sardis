"""API client for Sardis CLI."""
from __future__ import annotations

from typing import Any, Dict, Optional

import httpx


class APIError(Exception):
    """API error with status code and message."""
    
    def __init__(self, status_code: int, message: str, details: Any = None):
        self.status_code = status_code
        self.message = message
        self.details = details
        super().__init__(f"[{status_code}] {message}")


class SardisAPIClient:
    """HTTP client for Sardis API."""
    
    def __init__(
        self,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: float = 30.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
    
    @property
    def client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            headers = {"Content-Type": "application/json"}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"
            
            self._client = httpx.Client(
                base_url=self.base_url,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client
    
    def _handle_response(self, response: httpx.Response) -> Dict[str, Any]:
        """Handle API response and raise errors if needed."""
        if response.status_code >= 400:
            try:
                error_data = response.json()
                message = error_data.get("detail", error_data.get("message", "Unknown error"))
            except Exception:
                message = response.text or "Unknown error"
            
            raise APIError(response.status_code, message)
        
        return response.json()
    
    def get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Make GET request."""
        response = self.client.get(path, params=params)
        return self._handle_response(response)
    
    def post(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make POST request."""
        response = self.client.post(path, json=data)
        return self._handle_response(response)
    
    def patch(self, path: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make PATCH request."""
        response = self.client.patch(path, json=data)
        return self._handle_response(response)
    
    def delete(self, path: str) -> Dict[str, Any]:
        """Make DELETE request."""
        response = self.client.delete(path)
        return self._handle_response(response)
    
    def close(self) -> None:
        """Close HTTP client."""
        if self._client:
            self._client.close()
            self._client = None


def get_client(ctx) -> SardisAPIClient:
    """Get API client from context."""
    config = ctx.obj["config"]
    
    api_key = config.get("api_key")
    if not api_key:
        raise click.ClickException("Not authenticated. Run 'sardis login' first.")
    
    return SardisAPIClient(
        base_url=config.get("api_base_url", "https://api.sardis.network"),
        api_key=api_key,
    )


"""Custom OpenAPI schema generation with security schemes and metadata."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from .middleware import API_VERSION


def custom_openapi(app: FastAPI) -> Dict[str, Any]:
    """Generate custom OpenAPI schema with security schemes."""
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title="Sardis Stablecoin Execution API",
        version=API_VERSION,
        description="""
## Overview

The Sardis API provides a comprehensive platform for stablecoin payment execution
with built-in compliance, security, and auditability.

## Authentication

All API endpoints require authentication via API key:

```
X-API-Key: sk_live_your_api_key_here
```

## Rate Limits

- Standard endpoints: 100 requests/minute, 1000 requests/hour
- Admin endpoints: 10 requests/minute
- Burst: Up to 20 requests in quick succession

## Error Responses

All errors follow RFC 7807 Problem Details format:

```json
{
  "type": "https://api.sardis.sh/errors/validation-error",
  "title": "Validation Error",
  "status": 422,
  "detail": "One or more fields failed validation",
  "instance": "/api/v2/mandates",
  "request_id": "req_abc123",
  "errors": [...]
}
```

## Versioning

Current API version: v2. The API version is included in all response headers:
`X-API-Version: {version}`
        """,
        routes=app.routes,
    )

    # Security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication. Format: sk_live_xxxxx",
        },
        "BearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT token for dashboard authentication",
        },
        "WebhookSignature": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Sardis-Signature",
            "description": "HMAC-SHA256 webhook signature. Format: t=<timestamp>,v1=<signature>",
        },
    }

    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    openapi_schema["servers"] = [
        {"url": "https://api.sardis.sh", "description": "Production server"},
        {"url": "https://api.staging.sardis.sh", "description": "Staging server"},
        {"url": "http://localhost:8000", "description": "Local development"},
    ]

    openapi_schema["info"]["contact"] = {
        "name": "Sardis API Support",
        "email": "support@sardis.sh",
        "url": "https://docs.sardis.sh",
    }
    openapi_schema["info"]["license"] = {
        "name": "Proprietary",
        "url": "https://sardis.sh/terms",
    }

    openapi_schema["tags"] = [
        {"name": "health", "description": "Health check endpoints"},
        {"name": "mandates", "description": "Payment mandate management"},
        {"name": "ap2", "description": "Agent-to-Agent Protocol v2"},
        {"name": "mvp", "description": "Minimum Viable Protocol operations"},
        {"name": "ledger", "description": "Ledger and transaction history"},
        {"name": "holds", "description": "Pre-authorization holds"},
        {"name": "approvals", "description": "Human approval workflows for agent actions"},
        {"name": "webhooks", "description": "Webhook subscription management"},
        {"name": "transactions", "description": "Transaction status and gas estimation"},
        {"name": "marketplace", "description": "A2A service discovery"},
        {"name": "wallets", "description": "Wallet management"},
        {"name": "agents", "description": "AI agent configuration"},
        {"name": "api-keys", "description": "API key management"},
        {"name": "cards", "description": "Virtual card management"},
        {"name": "checkout", "description": "Agentic checkout flow"},
        {"name": "policies", "description": "Natural language policy parsing"},
        {"name": "compliance", "description": "KYC and sanctions screening"},
        {"name": "admin", "description": "Administrative operations"},
        {"name": "auth", "description": "Authentication endpoints"},
        {"name": "ramp", "description": "Fiat on-ramp and off-ramp"},
    ]

    app.openapi_schema = openapi_schema
    return app.openapi_schema

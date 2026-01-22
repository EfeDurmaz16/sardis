#!/usr/bin/env python3
"""
Generate OpenAPI specification from Sardis API routes.

This script creates an openapi.json file that can be used for:
- API documentation
- Client SDK generation
- API testing tools
"""
from __future__ import annotations

import json
import os
import sys

# Set test environment to avoid database connections
os.environ["SARDIS_ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = "memory://"
os.environ["SARDIS_CHAIN_MODE"] = "simulated"

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sardis_api.main import create_app


def generate_openapi():
    """Generate OpenAPI spec from the FastAPI app."""
    app = create_app()
    openapi_schema = app.openapi()

    # Enhance the schema with additional info
    openapi_schema["info"]["title"] = "Sardis API"
    openapi_schema["info"]["description"] = """
# Sardis - Payment OS for AI Agents

Sardis provides secure payment infrastructure for AI agents with:

- **MPC Wallets**: Non-custodial wallets using multi-party computation
- **Policy Engine**: Spending limits, vendor allowlists, rate controls
- **On-Chain Execution**: Real stablecoin transfers on Base, Ethereum, Polygon
- **Audit Trail**: Immutable ledger with Merkle tree anchoring

## Authentication

All API requests require an API key passed via the `X-API-Key` header:

```
X-API-Key: sk_live_your_api_key
```

## Rate Limits

- 100 requests per minute per API key
- 1000 requests per hour per API key
- Burst allowance of 20 requests

## Environments

- **Production**: `https://api.sardis.network`
- **Staging**: `https://api.staging.sardis.network`
- **Local**: `http://localhost:8000`
"""
    openapi_schema["info"]["version"] = "2.0.0"
    openapi_schema["info"]["contact"] = {
        "name": "Sardis Support",
        "email": "support@sardis.network",
        "url": "https://sardis.network/docs",
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.sardis.network",
            "description": "Production",
        },
        {
            "url": "https://api.staging.sardis.network",
            "description": "Staging",
        },
        {
            "url": "http://localhost:8000",
            "description": "Local Development",
        },
    ]

    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "ApiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key",
            "description": "API key for authentication",
        }
    }

    # Apply security globally
    openapi_schema["security"] = [{"ApiKeyAuth": []}]

    # Add tags with descriptions
    openapi_schema["tags"] = [
        {"name": "health", "description": "Health check endpoints"},
        {"name": "wallets", "description": "Wallet management operations"},
        {"name": "mandates", "description": "Payment mandate operations"},
        {"name": "holds", "description": "Pre-authorization (hold) operations"},
        {"name": "ledger", "description": "Transaction ledger queries"},
        {"name": "webhooks", "description": "Webhook subscription management"},
        {"name": "marketplace", "description": "A2A service marketplace"},
        {"name": "agents", "description": "Agent identity management"},
        {"name": "cards", "description": "Virtual card operations"},
        {"name": "checkout", "description": "Agentic checkout flow"},
        {"name": "api-keys", "description": "API key management"},
    ]

    return openapi_schema


def main():
    """Main entry point."""
    openapi_schema = generate_openapi()

    # Output to stdout or file
    output_path = os.path.join(
        os.path.dirname(__file__), "..", "openapi.json"
    )

    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI spec generated at: {output_path}")

    # Also generate YAML version
    try:
        import yaml

        yaml_path = output_path.replace(".json", ".yaml")
        with open(yaml_path, "w") as f:
            yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True)
        print(f"OpenAPI YAML generated at: {yaml_path}")
    except ImportError:
        print("Note: Install pyyaml for YAML output")


if __name__ == "__main__":
    main()

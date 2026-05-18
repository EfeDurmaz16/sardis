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
import warnings
from argparse import ArgumentParser
from pathlib import Path

# Set local environment to avoid database/network connections.
os.environ.setdefault("SARDIS_ENVIRONMENT", "dev")
os.environ.setdefault("DATABASE_URL", "memory://")
os.environ.setdefault("SARDIS_CHAIN_MODE", "simulated")
os.environ.setdefault("SARDIS_SECRET_KEY", "openapi-generation-local-secret-key")
os.environ.setdefault("JWT_SECRET_KEY", "openapi-generation-local-jwt-secret-key")

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sardis_api.main import create_app


def generate_openapi():
    """Generate OpenAPI spec from the FastAPI app."""
    app = create_app()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        openapi_schema = app.openapi()

    duplicate_operation_warnings = [
        str(warning.message)
        for warning in caught
        if "Duplicate Operation ID" in str(warning.message)
    ]
    if duplicate_operation_warnings:
        details = "\n".join(f"- {message}" for message in duplicate_operation_warnings)
        raise RuntimeError(f"OpenAPI duplicate operation IDs detected:\n{details}")

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
X-API-Key: <your-api-key>
```

## Rate Limits

- 100 requests per minute per API key
- 1000 requests per hour per API key
- Burst allowance of 20 requests

## Environments

- **Production**: `https://api.sardis.sh`
- **Staging**: `https://api.staging.sardis.sh`
- **Local**: `http://localhost:8000`
"""
    openapi_schema["info"]["version"] = "2.0.0"
    openapi_schema["info"]["contact"] = {
        "name": "Sardis Support",
        "email": "support@sardis.sh",
        "url": "https://sardis.sh/docs",
    }
    openapi_schema["info"]["license"] = {
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    }

    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.sardis.sh",
            "description": "Production",
        },
        {
            "url": "https://api.staging.sardis.sh",
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
    parser = ArgumentParser(description="Generate or validate the Sardis API OpenAPI schema.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Generate the schema in memory and exit without writing files.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to packages/sardis-api/openapi.json.",
    )
    args = parser.parse_args()

    openapi_schema = generate_openapi()
    path_count = len(openapi_schema.get("paths", {}))
    schema_count = len(openapi_schema.get("components", {}).get("schemas", {}))

    if args.check:
        print(f"OpenAPI schema generated successfully: {path_count} paths, {schema_count} schemas")
        return

    # Output to stdout or file
    output_path = Path(args.output) if args.output else Path(__file__).resolve().parents[1] / "openapi.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        json.dump(openapi_schema, f, indent=2)

    print(f"OpenAPI spec generated at: {output_path}")

    # Also generate YAML version
    try:
        import yaml

        yaml_path = output_path.with_suffix(".yaml")
        with yaml_path.open("w") as f:
            yaml.dump(openapi_schema, f, default_flow_style=False, allow_unicode=True)
        print(f"OpenAPI YAML generated at: {yaml_path}")
    except ImportError:
        print("Note: Install pyyaml for YAML output")


if __name__ == "__main__":
    main()

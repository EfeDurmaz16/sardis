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


DEFAULT_OUTPUT_PATH = Path(__file__).resolve().parents[1] / "openapi.json"
DEFAULT_SNAPSHOT_PATH = Path(__file__).resolve().parents[1] / "openapi" / "openapi.routes.snapshot.json"


def _canonical_json(schema: dict) -> str:
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def contract_manifest(openapi_schema: dict) -> dict:
    """Return a stable route-level API contract manifest.

    The full FastAPI component schema currently has duplicate model class names
    in different modules, which can make component bodies and `$ref` names
    unstable across Python processes. This manifest intentionally tracks the
    stable public route surface: path, method, operationId, tags, parameters,
    request media types, and response status/media types.
    """
    paths: list[dict] = []
    for path, path_item in sorted(openapi_schema.get("paths", {}).items()):
        for method, operation in sorted(path_item.items()):
            if method.lower() not in {"get", "post", "put", "patch", "delete", "options", "head"}:
                continue
            request_body = operation.get("requestBody", {}) if isinstance(operation, dict) else {}
            request_content = request_body.get("content", {}) if isinstance(request_body, dict) else {}
            responses = operation.get("responses", {}) if isinstance(operation, dict) else {}
            paths.append(
                {
                    "method": method.upper(),
                    "path": path,
                    "operation_id": operation.get("operationId"),
                    "tags": sorted(operation.get("tags", [])),
                    "parameters": [
                        {
                            "name": param.get("name"),
                            "in": param.get("in"),
                            "required": bool(param.get("required", False)),
                        }
                        for param in operation.get("parameters", [])
                    ],
                    "request_body": sorted(request_content),
                    "responses": {
                        status_code: sorted(response.get("content", {}))
                        for status_code, response in sorted(responses.items())
                    },
                }
            )
    return {
        "openapi": openapi_schema.get("openapi"),
        "info": {
            "title": openapi_schema.get("info", {}).get("title"),
            "version": openapi_schema.get("info", {}).get("version"),
        },
        "path_count": len(paths),
        "paths": paths,
    }


def generate_openapi():
    """Generate OpenAPI spec from the FastAPI app."""
    from sardis_api.main import create_app

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
    if os.environ.get("PYTHONHASHSEED") != "0":
        env = dict(os.environ)
        env["PYTHONHASHSEED"] = "0"
        os.execvpe(sys.executable, [sys.executable, *sys.argv], env)

    parser = ArgumentParser(description="Generate or validate the Sardis API OpenAPI schema.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Generate the schema in memory and compare it with the checked snapshot.",
    )
    parser.add_argument(
        "--update-snapshot",
        action="store_true",
        help="Write the generated route contract manifest to the checked OpenAPI snapshot.",
    )
    parser.add_argument(
        "--snapshot",
        default=str(DEFAULT_SNAPSHOT_PATH),
        help="Snapshot JSON path used by --check and --update-snapshot.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to packages/api/openapi.json.",
    )
    args = parser.parse_args()

    openapi_schema = generate_openapi()
    path_count = len(openapi_schema.get("paths", {}))
    schema_count = len(openapi_schema.get("components", {}).get("schemas", {}))

    if args.check:
        snapshot_path = Path(args.snapshot)
        if not snapshot_path.exists():
            raise SystemExit(
                f"OpenAPI snapshot is missing: {snapshot_path}. "
                "Run generate_openapi.py --update-snapshot after reviewing the API surface."
            )
        expected = snapshot_path.read_text()
        actual = _canonical_json(contract_manifest(openapi_schema))
        if actual != expected:
            raise SystemExit(
                f"OpenAPI route snapshot is out of date: {snapshot_path}. "
                "Review the API diff, then run generate_openapi.py --update-snapshot."
            )
        print(f"OpenAPI schema generated successfully: {path_count} paths, {schema_count} schemas")
        return

    if args.update_snapshot:
        snapshot_path = Path(args.snapshot)
        snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        snapshot_path.write_text(_canonical_json(contract_manifest(openapi_schema)))
        print(f"OpenAPI route snapshot updated at: {snapshot_path}")
        print(f"OpenAPI schema generated successfully: {path_count} paths, {schema_count} schemas")
        return

    # Output to stdout or file
    output_path = Path(args.output) if args.output else DEFAULT_OUTPUT_PATH
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w") as f:
        f.write(_canonical_json(openapi_schema))

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

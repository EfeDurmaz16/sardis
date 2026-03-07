"""Secrets provider abstraction for Sardis.

Supports multiple secret backends:
- env: Read from environment variables (default, for local dev)
- gcp: Google Secret Manager (for Cloud Run / GCP deployments)
- aws: AWS Systems Manager Parameter Store (for AWS deployments)

Usage:
    provider = get_secrets_provider()
    db_url = await provider.get("DATABASE_URL")

Configuration via environment variables:
    SARDIS_SECRETS_PROVIDER=env|gcp|aws  (default: env)
    SARDIS_SECRETS_GCP_PROJECT=my-project  (required for gcp)
    SARDIS_SECRETS_AWS_REGION=us-east-1  (required for aws)
    SARDIS_SECRETS_PREFIX=sardis/prod/  (optional key prefix)

IMPORTANT: In production, use Cloud Run secret injection or a cloud
secrets manager. Never store production secrets in .env files on disk.
"""
from __future__ import annotations

import logging
import os
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)


class SecretsProvider(ABC):
    """Abstract base class for secrets providers."""

    @abstractmethod
    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Retrieve a secret by key."""
        ...

    @abstractmethod
    async def get_required(self, key: str) -> str:
        """Retrieve a required secret. Raises if missing."""
        ...

    async def close(self) -> None:
        """Clean up provider resources."""
        pass


class EnvSecretsProvider(SecretsProvider):
    """Read secrets from environment variables (default for dev)."""

    def __init__(self, prefix: str = ""):
        self._prefix = prefix

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return os.getenv(f"{self._prefix}{key}", default)

    async def get_required(self, key: str) -> str:
        value = os.getenv(f"{self._prefix}{key}")
        if not value:
            raise ValueError(f"Required secret '{self._prefix}{key}' not found in environment")
        return value


class GCPSecretsProvider(SecretsProvider):
    """Read secrets from Google Secret Manager.

    Requires: google-cloud-secret-manager package.
    """

    def __init__(self, project_id: str, prefix: str = ""):
        self._project_id = project_id
        self._prefix = prefix
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google.cloud import secretmanager
                self._client = secretmanager.SecretManagerServiceAsyncClient()
            except ImportError:
                raise ImportError(
                    "google-cloud-secret-manager is required for GCP secrets provider. "
                    "Install with: pip install google-cloud-secret-manager"
                )
        return self._client

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        secret_id = f"{self._prefix}{key}".replace("_", "-").lower()
        name = f"projects/{self._project_id}/secrets/{secret_id}/versions/latest"
        try:
            client = self._get_client()
            response = await client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except Exception as e:
            logger.debug("GCP secret '%s' not found: %s", secret_id, e)
            return default

    async def get_required(self, key: str) -> str:
        value = await self.get(key)
        if value is None:
            raise ValueError(f"Required secret '{self._prefix}{key}' not found in GCP Secret Manager")
        return value

    async def close(self) -> None:
        if self._client is not None:
            await self._client.__aexit__(None, None, None)
            self._client = None


class AWSSecretsProvider(SecretsProvider):
    """Read secrets from AWS Systems Manager Parameter Store.

    Requires: boto3 package.
    """

    def __init__(self, region: str = "us-east-1", prefix: str = ""):
        self._region = region
        self._prefix = prefix
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client("ssm", region_name=self._region)
            except ImportError:
                raise ImportError(
                    "boto3 is required for AWS secrets provider. "
                    "Install with: pip install boto3"
                )
        return self._client

    async def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        param_name = f"/{self._prefix}{key}" if self._prefix else f"/{key}"
        try:
            import asyncio
            client = self._get_client()
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.get_parameter(Name=param_name, WithDecryption=True),
            )
            return response["Parameter"]["Value"]
        except Exception as e:
            logger.debug("AWS SSM parameter '%s' not found: %s", param_name, e)
            return default

    async def get_required(self, key: str) -> str:
        value = await self.get(key)
        if value is None:
            raise ValueError(f"Required secret '{self._prefix}{key}' not found in AWS SSM")
        return value


@lru_cache(maxsize=1)
def get_secrets_provider() -> SecretsProvider:
    """Get the configured secrets provider.

    Reads SARDIS_SECRETS_PROVIDER env var to determine backend:
    - "env" (default): Environment variables
    - "gcp": Google Secret Manager
    - "aws": AWS SSM Parameter Store
    """
    provider_type = os.getenv("SARDIS_SECRETS_PROVIDER", "env").strip().lower()
    prefix = os.getenv("SARDIS_SECRETS_PREFIX", "")

    if provider_type == "gcp":
        project_id = os.getenv("SARDIS_SECRETS_GCP_PROJECT", "")
        if not project_id:
            raise ValueError("SARDIS_SECRETS_GCP_PROJECT required for GCP secrets provider")
        logger.info("Using GCP Secret Manager (project=%s)", project_id)
        return GCPSecretsProvider(project_id=project_id, prefix=prefix)

    if provider_type == "aws":
        region = os.getenv("SARDIS_SECRETS_AWS_REGION", "us-east-1")
        logger.info("Using AWS SSM Parameter Store (region=%s)", region)
        return AWSSecretsProvider(region=region, prefix=prefix)

    if provider_type != "env":
        logger.warning("Unknown secrets provider '%s', falling back to env", provider_type)

    return EnvSecretsProvider(prefix=prefix)


__all__ = [
    "SecretsProvider",
    "EnvSecretsProvider",
    "GCPSecretsProvider",
    "AWSSecretsProvider",
    "get_secrets_provider",
]

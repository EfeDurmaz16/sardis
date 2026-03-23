"""Infisical secrets management adapter for Sardis.

Replaces os.getenv() with centralized, rotatable secrets.

Setup:
    pip install infisical-python

Environment variables:
    INFISICAL_CLIENT_ID — Machine identity client ID
    INFISICAL_CLIENT_SECRET — Machine identity client secret
    INFISICAL_PROJECT_ID — Infisical project ID
    INFISICAL_ENVIRONMENT — Environment slug (dev/staging/prod)
    SARDIS_INFISICAL_ENABLED — Set to "1" to enable
"""
from __future__ import annotations

import logging
import os
from typing import Any

_logger = logging.getLogger(__name__)
_client = None
_cache: dict[str, str] = {}
_enabled = False


def init_infisical() -> None:
    """Initialize Infisical client. No-op if not configured."""
    global _client, _enabled

    if os.getenv("SARDIS_INFISICAL_ENABLED", "").strip() not in ("1", "true", "yes"):
        return

    try:
        from infisical_client import ClientSettings, InfisicalClient

        _client = InfisicalClient(ClientSettings(
            client_id=os.getenv("INFISICAL_CLIENT_ID", ""),
            client_secret=os.getenv("INFISICAL_CLIENT_SECRET", ""),
        ))
        _enabled = True
        _logger.info("Infisical secrets manager initialized")
    except ImportError:
        _logger.info("Infisical not installed, using os.getenv() fallback")
    except Exception as e:
        _logger.warning("Infisical init failed: %s", e)


def get_secret(key: str, default: str = "") -> str:
    """Get a secret from Infisical (with os.getenv fallback).

    Caches values in memory to avoid repeated API calls.
    """
    # Check cache first
    if key in _cache:
        return _cache[key]

    # Try Infisical
    if _enabled and _client is not None:
        try:
            from infisical_client import GetSecretOptions
            secret = _client.getSecret(options=GetSecretOptions(
                environment=os.getenv("INFISICAL_ENVIRONMENT", "prod"),
                project_id=os.getenv("INFISICAL_PROJECT_ID", ""),
                secret_name=key,
            ))
            if secret and secret.secret_value:
                _cache[key] = secret.secret_value
                return secret.secret_value
        except Exception as e:
            _logger.debug("Infisical get_secret(%s) failed, falling back to env: %s", key, e)

    # Fallback to environment variable
    value = os.getenv(key, default)
    _cache[key] = value
    return value

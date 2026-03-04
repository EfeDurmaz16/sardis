"""Sardis API - FastAPI gateway for Sardis stablecoin execution.

This package provides the REST API for the Sardis payment infrastructure:
- Mandate processing (Intent/Cart/Payment)
- Wallet operations and orchestration
- Ledger queries and compliance feeds
- Agent management and policies

Version: 0.3.1
"""

from typing import Any

__version__ = "0.3.1"


def create_app(*args: Any, **kwargs: Any):
    """Lazy import wrapper to avoid importing heavy chain deps on package import."""
    from .main import create_app as _create_app

    return _create_app(*args, **kwargs)

__all__ = [
    "__version__",
    "create_app",
]

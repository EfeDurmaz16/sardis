"""Sardis API - FastAPI gateway for Sardis stablecoin execution.

This package provides the REST API for the Sardis payment infrastructure:
- Mandate processing (Intent/Cart/Payment)
- Wallet operations and orchestration
- Ledger queries and compliance feeds
- Agent management and policies

Version: 0.1.0
"""

from .main import app, create_app

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "app",
    "create_app",
]

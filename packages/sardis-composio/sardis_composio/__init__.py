"""Sardis payment tools for Composio.

WARNING: This package does not integrate with the Composio framework.
These are plain functions wrapping the Sardis SDK. Consider using
sardis-sdk directly for the same functionality.
"""
import warnings

warnings.warn(
    "sardis-composio does not integrate with the Composio framework. "
    "These are plain functions. Consider using sardis-sdk directly.",
    DeprecationWarning,
    stacklevel=2,
)

from sardis_composio.tools import (
    SARDIS_TOOLS,
    sardis_check_balance,
    sardis_check_policy,
    sardis_pay,
)

__all__ = [
    "sardis_pay",
    "sardis_check_balance",
    "sardis_check_policy",
    "SARDIS_TOOLS",
]

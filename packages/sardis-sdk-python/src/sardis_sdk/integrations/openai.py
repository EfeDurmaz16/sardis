"""
OpenAI Function Calling integration for Sardis SDK.

DEPRECATED: This module is a compatibility shim. Use sardis-openai directly:
    pip install sardis-openai

    from sardis_openai import get_sardis_tools, handle_tool_call, SardisToolHandler
"""
from __future__ import annotations

import warnings

warnings.warn(
    "sardis_sdk.integrations.openai is deprecated. "
    "Use sardis-openai package directly: pip install sardis-openai\n"
    "  from sardis_openai import get_sardis_tools, handle_tool_call",
    DeprecationWarning,
    stacklevel=2,
)

try:
    from sardis_openai import (
        get_sardis_tools,
        handle_tool_call,
        SardisToolHandler,
        SARDIS_TOOL_DEFINITIONS,
    )
except ImportError:
    raise ImportError(
        "sardis-openai package is required for OpenAI integration. "
        "Install it with: pip install sardis-openai"
    )

# Backward compatibility aliases
get_openai_tools = get_sardis_tools
get_openai_function_schema = get_sardis_tools
handle_function_call = handle_tool_call

__all__ = [
    "get_openai_tools",
    "get_openai_function_schema",
    "get_sardis_tools",
    "handle_function_call",
    "handle_tool_call",
    "SardisToolHandler",
    "SARDIS_TOOL_DEFINITIONS",
]

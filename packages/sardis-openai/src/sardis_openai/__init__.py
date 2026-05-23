"""Sardis OpenAI integration - Function calling tools for AI agent payments.

Provides OpenAI-compatible function definitions and handlers for Sardis
payment operations. Works with the OpenAI Assistants API and Chat Completions.

Usage:
    from sardis_openai import get_sardis_tools, handle_tool_call, SardisToolHandler

    # Get tool definitions for OpenAI
    tools = get_sardis_tools()

    # Use with Chat Completions
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[...],
        tools=tools,
    )

    # Handle tool calls
    handler = SardisToolHandler(api_key="sk_...")
    for tool_call in response.choices[0].message.tool_calls:
        result = await handler.handle(tool_call)
"""

import warnings

warnings.warn(
    "sardis-openai is deprecated and superseded by sardis-openai-agents "
    "(~10x more installs). Please migrate: `pip install sardis-openai-agents`. "
    "The OpenAI Assistants API that this package targets is itself being "
    "deprecated by OpenAI in favor of the Responses / Agents API. "
    "See https://github.com/EfeDurmaz16/sardis/blob/main/packages/sardis-openai/README.md "
    "for the migration guide. This package will be yanked from PyPI after a "
    "30-day deprecation window.",
    DeprecationWarning,
    stacklevel=2,
)

from .handler import SardisToolHandler, handle_tool_call
from .tools import SARDIS_TOOL_DEFINITIONS, get_sardis_tools

__all__ = [
    "get_sardis_tools",
    "handle_tool_call",
    "SardisToolHandler",
    "SARDIS_TOOL_DEFINITIONS",
]

__version__ = "1.0.0"

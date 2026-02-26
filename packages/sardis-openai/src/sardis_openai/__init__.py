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

from .tools import get_sardis_tools, SARDIS_TOOL_DEFINITIONS
from .handler import SardisToolHandler, handle_tool_call

__all__ = [
    "get_sardis_tools",
    "handle_tool_call",
    "SardisToolHandler",
    "SARDIS_TOOL_DEFINITIONS",
]

__version__ = "1.0.0"

"""
Sardis SDK integrations - compatibility shims.

DEPRECATED: Use standalone packages instead:
    pip install sardis-openai     # OpenAI function calling
    pip install sardis-langchain  # LangChain tools
"""
from .llamaindex import get_llamaindex_tool
from .openai import get_openai_function_schema, get_openai_tools

__all__ = [
    "get_llamaindex_tool",
    "get_openai_function_schema",
    "get_openai_tools",
]


def __getattr__(name: str):
    if name in ("SardisTool", "SardisPolicyCheckTool", "SardisToolkit"):
        try:
            from .langchain import SardisPolicyCheckTool, SardisTool, SardisToolkit
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Install sardis-langchain for LangChain integration: pip install sardis-langchain"
            ) from e
        return {"SardisTool": SardisTool, "SardisPolicyCheckTool": SardisPolicyCheckTool, "SardisToolkit": SardisToolkit}[name]
    raise AttributeError(name)

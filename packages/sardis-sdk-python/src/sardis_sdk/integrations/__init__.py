"""
Sardis SDK integrations - compatibility shims.

DEPRECATED: Use standalone packages instead:
    pip install sardis-openai     # OpenAI function calling
    pip install sardis-langchain  # LangChain tools
"""
from .openai import get_openai_function_schema, get_openai_tools
from .llamaindex import get_llamaindex_tool

__all__ = [
    "get_openai_function_schema",
    "get_openai_tools",
    "get_llamaindex_tool",
]


def __getattr__(name: str):
    if name in ("SardisTool", "SardisPolicyCheckTool", "SardisToolkit"):
        try:
            from .langchain import SardisTool, SardisPolicyCheckTool, SardisToolkit  # noqa: PLC0415
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Install sardis-langchain for LangChain integration: pip install sardis-langchain"
            ) from e
        return {"SardisTool": SardisTool, "SardisPolicyCheckTool": SardisPolicyCheckTool, "SardisToolkit": SardisToolkit}[name]
    raise AttributeError(name)

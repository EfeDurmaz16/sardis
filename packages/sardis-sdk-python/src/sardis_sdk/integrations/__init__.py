from .openai import get_openai_function_schema
from .llamaindex import get_llamaindex_tool

__all__ = [
    "get_openai_function_schema",
    "get_llamaindex_tool",
]


def __getattr__(name: str):
    if name in ("SardisTool", "SardisPolicyCheckTool"):
        try:
            from .langchain import SardisPolicyCheckTool, SardisTool  # noqa: PLC0415
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                "Optional dependency missing: install `langchain` to use sardis_sdk.integrations.langchain."
            ) from e
        return {"SardisTool": SardisTool, "SardisPolicyCheckTool": SardisPolicyCheckTool}[name]
    raise AttributeError(name)

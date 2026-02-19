"""High-level toolkit for integrating Sardis payments into Claude agents.

:class:`SardisToolkit` is the main entry point.  It wraps tool definitions
and result handling into a single object that plugs directly into the
Anthropic Messages API.

Minimal example::

    from sardis import SardisClient
    from sardis_agent_sdk import SardisToolkit

    sardis = SardisClient(api_key="sk_test_demo")
    wallet = sardis.wallets.create(name="agent-wallet", chain="base")

    toolkit = SardisToolkit(client=sardis, wallet_id=wallet.id)

    # Pass tool definitions to the Claude API
    tools = toolkit.get_tools()

    # After receiving a response with tool_use blocks:
    for block in response.content:
        if block.type == "tool_use":
            result = toolkit.handle_tool_call(block)
            messages.append({"role": "user", "content": [result]})

Full agent loop::

    import anthropic
    from sardis import SardisClient
    from sardis_agent_sdk import SardisToolkit

    sardis = SardisClient(api_key="sk_test_demo")
    wallet = sardis.wallets.create(name="shopping-agent", chain="base")
    toolkit = SardisToolkit(client=sardis, wallet_id=wallet.id)

    anthropic_client = anthropic.Anthropic()
    result = toolkit.run_agent_loop(
        client=anthropic_client,
        model="claude-sonnet-4-5-20250929",
        system_prompt="You are a shopping assistant with a Sardis wallet.",
        user_message="Buy me a $20 API credit from openai.com",
    )
"""

from __future__ import annotations

import json
from typing import Any, Optional

from sardis import SardisClient

from .handlers import SardisToolHandler
from .tools import ALL_TOOLS, READ_ONLY_TOOLS


class SardisToolkit:
    """Ready-to-use toolkit for Anthropic Claude agents.

    Args:
        client: A configured :class:`sardis.SardisClient` instance.
        wallet_id: The wallet ID this toolkit operates on.
        read_only: If ``True``, only expose read-only tools (balance,
            policy check, transaction history).  Useful for observer
            agents that should not be able to spend.
    """

    def __init__(
        self,
        client: SardisClient,
        wallet_id: str,
        *,
        read_only: bool = False,
    ) -> None:
        self.client = client
        self.wallet_id = wallet_id
        self.read_only = read_only
        self.handler = SardisToolHandler(client=client, wallet_id=wallet_id)

    # ------------------------------------------------------------------
    # Tool definitions
    # ------------------------------------------------------------------

    def get_tools(self) -> list[dict[str, Any]]:
        """Return tool definitions for ``client.messages.create(tools=...)``.

        If *read_only* is ``True``, only balance, policy check, and
        transaction listing tools are included.
        """
        if self.read_only:
            return list(READ_ONLY_TOOLS)
        return list(ALL_TOOLS)

    # ------------------------------------------------------------------
    # Tool call processing
    # ------------------------------------------------------------------

    def handle_tool_call(self, tool_use_block: Any) -> dict[str, Any]:
        """Process a tool_use block and return a tool_result block.

        Accepts either a dict or an Anthropic SDK ``ToolUseBlock`` object.
        Returns a dict suitable for appending to the messages list::

            {"type": "tool_result", "tool_use_id": "...", "content": "..."}

        Args:
            tool_use_block: A ``tool_use`` content block from a Claude
                response.  Can be an Anthropic SDK object (with ``.id``,
                ``.name``, ``.input`` attributes) or a plain dict.
        """
        if isinstance(tool_use_block, dict):
            block_dict = tool_use_block
        else:
            # Anthropic SDK ToolUseBlock object
            block_dict = {
                "type": "tool_use",
                "id": tool_use_block.id,
                "name": tool_use_block.name,
                "input": tool_use_block.input,
            }

        return self.handler.process_tool_use_block(block_dict)

    # ------------------------------------------------------------------
    # Convenience: full agent loop
    # ------------------------------------------------------------------

    def run_agent_loop(
        self,
        client: Any,
        model: str,
        system_prompt: str,
        user_message: str,
        *,
        max_turns: int = 10,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Run a complete agent loop with automatic tool handling.

        This convenience method handles the full messages loop:

        1. Send user message to Claude with Sardis tools
        2. If Claude responds with tool_use, process it
        3. Send tool results back and repeat
        4. Return final text response

        Args:
            client: An ``anthropic.Anthropic()`` client instance.
            model: Model name (e.g. ``"claude-sonnet-4-5-20250929"``).
            system_prompt: System prompt for the agent.
            user_message: The user's message to start the conversation.
            max_turns: Maximum number of tool-use round trips.
            max_tokens: Maximum tokens per response.

        Returns:
            A dict with:
              - ``"response"``: The final text response from Claude.
              - ``"messages"``: The full message history.
              - ``"tool_calls"``: List of all tool calls made.
              - ``"turns"``: Number of turns taken.
        """
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": user_message},
        ]
        tool_calls: list[dict[str, Any]] = []
        tools = self.get_tools()

        for turn in range(max_turns):
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                tools=tools,
                messages=messages,
            )

            # Collect text and tool_use blocks
            assistant_content: list[Any] = []
            tool_use_blocks: list[Any] = []

            for block in response.content:
                if hasattr(block, "type"):
                    if block.type == "text":
                        assistant_content.append(block)
                    elif block.type == "tool_use":
                        assistant_content.append(block)
                        tool_use_blocks.append(block)

            # Append the full assistant message
            messages.append({"role": "assistant", "content": response.content})

            # If no tool use, we are done
            if not tool_use_blocks:
                final_text = ""
                for block in response.content:
                    if hasattr(block, "type") and block.type == "text":
                        final_text += block.text
                return {
                    "response": final_text,
                    "messages": messages,
                    "tool_calls": tool_calls,
                    "turns": turn + 1,
                }

            # Process each tool call and collect results
            tool_results: list[dict[str, Any]] = []
            for block in tool_use_blocks:
                result = self.handle_tool_call(block)
                tool_results.append(result)
                tool_calls.append({
                    "tool_name": block.name,
                    "tool_input": block.input,
                    "result": json.loads(result.get("content", "{}")),
                })

            # Send tool results back
            messages.append({"role": "user", "content": tool_results})

            # If the model signals end_turn with tool results, continue
            if response.stop_reason == "end_turn":
                # Model said end_turn but also made tool calls — process results
                # and let the model generate a final response
                continue

        # Max turns exceeded — return what we have
        final_text = ""
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                content = msg.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if hasattr(block, "type") and block.type == "text":
                            final_text += block.text
                break

        return {
            "response": final_text or "(max turns reached without final response)",
            "messages": messages,
            "tool_calls": tool_calls,
            "turns": max_turns,
        }

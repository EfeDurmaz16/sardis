"""
OpenAI Assistant with Sardis Wallet

An OpenAI function calling agent with Sardis payment capabilities.

Setup:
    pip install sardis-openai openai

Usage:
    export SARDIS_API_KEY="sk_..."
    export OPENAI_API_KEY="sk-..."
    python main.py
"""
import json
import os

import openai
from sardis_openai import get_sardis_tools, SardisToolHandler


async def main():
    # Setup
    client = openai.AsyncOpenAI()
    handler = SardisToolHandler(api_key=os.environ["SARDIS_API_KEY"])
    tools = get_sardis_tools()

    messages = [
        {"role": "system", "content": "You are a helpful assistant with a payment wallet. "
         "You can check balances and make payments using USDC."},
        {"role": "user", "content": "Check my balance and then pay $10 to 0x742d35Cc...for API credits"},
    ]

    # Conversation loop
    while True:
        response = await client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            tools=tools,
        )

        message = response.choices[0].message
        messages.append(message.model_dump())

        if message.tool_calls:
            for tool_call in message.tool_calls:
                result = await handler.handle(tool_call)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result),
                })
        else:
            print(f"Assistant: {message.content}")
            break


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

"""
Gemini Shopping Agent Example

A Google Gemini agent that can make purchases using Sardis.

Setup:
    pip install sardis-adk google-generativeai

Usage:
    export SARDIS_API_KEY="sk_..."
    export GOOGLE_API_KEY="..."
    python main.py
"""
import os

import google.generativeai as genai
from sardis_adk import get_sardis_gemini_tools, handle_gemini_function_call
from sardis import SardisClient


def main():
    # Configure Gemini
    genai.configure(api_key=os.environ["GOOGLE_API_KEY"])

    # Initialize Sardis
    sardis = SardisClient(api_key=os.environ["SARDIS_API_KEY"])
    wallet = sardis.wallets.create(
        name="gemini-shopper",
        chain="base",
        policy="Max $200/day, online merchants only"
    )

    # Get Sardis tools for Gemini
    sardis_tools = get_sardis_gemini_tools()

    # Create model with tools
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        tools=[sardis_tools],
        system_instruction="You are a shopping assistant with a crypto wallet. "
        "You can make payments for purchases using USDC.",
    )

    chat = model.start_chat()

    # Send request
    response = chat.send_message(
        "I need to buy $50 worth of OpenAI API credits. Check if my policy allows it, then make the payment."
    )

    # Handle function calls
    for part in response.parts:
        if hasattr(part, "function_call") and part.function_call:
            result = handle_gemini_function_call(
                sardis, wallet.id, part.function_call
            )
            print(f"Tool result: {result}")

    print(f"\nAssistant: {response.text}")


if __name__ == "__main__":
    main()

"""
LangChain Payment Agent Example

Demonstrates an AI agent that can make payments using Sardis + LangChain.

Setup:
    pip install sardis-langchain langchain langchain-openai

Usage:
    export SARDIS_API_KEY="sk_..."
    export OPENAI_API_KEY="sk-..."
    python main.py
"""
import os

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_openai_functions_agent
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

from sardis import SardisClient
from sardis_langchain import SardisToolkit


def main():
    # Initialize Sardis
    sardis = SardisClient(api_key=os.environ["SARDIS_API_KEY"])

    # Create agent wallet with spending policy
    wallet = sardis.wallets.create(
        name="langchain-payment-agent",
        chain="base",
        policy="Max $100/day, only for API services and cloud hosting"
    )
    print(f"Wallet created: {wallet.id} ({wallet.address})")

    # Create LangChain tools
    toolkit = SardisToolkit(client=sardis, wallet_id=wallet.id)
    tools = toolkit.get_tools()

    # Setup LangChain agent
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    prompt = ChatPromptTemplate.from_messages([
        ("system", """You are a payment agent that can execute crypto payments.
        You have a Sardis wallet with USDC on Base chain.
        Always check the spending policy before making payments.
        Confirm the amount and recipient before executing."""),
        MessagesPlaceholder(variable_name="chat_history", optional=True),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_functions_agent(llm, tools, prompt)
    executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    # Run the agent
    result = executor.invoke({
        "input": "Check my balance, then pay $25 USDC to 0x742d35Cc6634C0532925a3b844Bc9e7595f2bD28 for API credits"
    })

    print(f"\nResult: {result['output']}")


if __name__ == "__main__":
    main()

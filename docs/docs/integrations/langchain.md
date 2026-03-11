# LangChain Integration

Enable LangChain agents to make real payments through Sardis with built-in tools and callbacks.

## Installation

```bash
pip install sardis-langchain
```

Or install with the full Sardis SDK:

```bash
pip install sardis[langchain]
```

## Quick Start

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from sardis_langchain import SardisToolkit

# Initialize Sardis toolkit
toolkit = SardisToolkit(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

# Get tools
tools = toolkit.get_tools()

# Create agent
llm = ChatOpenAI(model="gpt-4o", temperature=0)
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a payment assistant with access to Sardis payment tools."),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Execute payment
result = executor.invoke({"input": "Pay $50 USDC to 0x1234...5678 for API credits"})
print(result["output"])
```

## Available Tools

The Sardis LangChain toolkit provides 5 core tools:

### 1. SardisPaymentTool

Execute payments from the agent's wallet.

```python
from sardis_langchain import SardisPaymentTool

payment_tool = SardisPaymentTool(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

# Agent can call this tool
result = payment_tool._run(
    to="0x1234...5678",
    amount=50.0,
    token="USDC",
    purpose="API credits"
)
```

### 2. SardisBalanceTool

Check wallet balances.

```python
from sardis_langchain import SardisBalanceTool

balance_tool = SardisBalanceTool(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

result = balance_tool._run(token="USDC")
# Returns: "Balance: 1500.00 USDC"
```

### 3. SardisTransactionHistoryTool

Query transaction history.

```python
from sardis_langchain import SardisTransactionHistoryTool

history_tool = SardisTransactionHistoryTool(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

result = history_tool._run(limit=10)
# Returns last 10 transactions
```

### 4. SardisPolicyTool

Check or update spending policies.

```python
from sardis_langchain import SardisPolicyTool

policy_tool = SardisPolicyTool(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

result = policy_tool._run()
# Returns current policy: "Max $500/day, only SaaS vendors"
```

### 5. SardisTrustScoreTool

Get KYA trust score.

```python
from sardis_langchain import SardisTrustScoreTool

trust_tool = SardisTrustScoreTool(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

result = trust_tool._run()
# Returns: "Trust Score: 85/100 (Good)"
```

## Using the Toolkit

The toolkit bundles all tools together:

```python
from sardis_langchain import SardisToolkit

toolkit = SardisToolkit(
    api_key="sk_...",
    wallet_id="wallet_abc123"
)

# Get all tools at once
tools = toolkit.get_tools()

# Filter specific tools
payment_tools = toolkit.get_tools(include=["payment", "balance"])

# Exclude certain tools
limited_tools = toolkit.get_tools(exclude=["policy"])
```

## Custom Agent Example

Build a procurement agent with LangChain:

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from sardis_langchain import SardisToolkit

# Initialize
llm = ChatOpenAI(model="gpt-4o", temperature=0)
toolkit = SardisToolkit(api_key="sk_...", wallet_id="wallet_abc123")
tools = toolkit.get_tools()

# Custom system prompt
system_prompt = """
You are a procurement agent with a Sardis wallet.

Your responsibilities:
- Purchase approved services when requested
- Stay within spending policy ($500/day)
- Only buy from approved vendors (OpenAI, AWS, Stripe)
- Provide transaction confirmations

When asked to make a purchase:
1. Check current balance
2. Verify amount is within policy
3. Execute payment
4. Return transaction hash
"""

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
    MessagesPlaceholder(variable_name="agent_scratchpad"),
])

agent = create_openai_functions_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

# Use the agent
result = executor.invoke({
    "input": "Purchase $100 of OpenAI API credits"
})
```

## Callbacks

Sardis provides LangChain callbacks for monitoring:

```python
from sardis_langchain import SardisCallbackHandler
from langchain.agents import AgentExecutor

# Create callback handler
sardis_callback = SardisCallbackHandler(
    api_key="sk_...",
    log_payments=True,
    log_policy_checks=True
)

# Add to agent executor
executor = AgentExecutor(
    agent=agent,
    tools=tools,
    callbacks=[sardis_callback],
    verbose=True
)

# Callback logs:
# - Tool calls
# - Payment executions
# - Policy validations
# - Trust score changes
```

## LCEL (LangChain Expression Language)

Use Sardis with LCEL chains:

```python
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_openai import ChatOpenAI
from langchain_core.output_parsers import StrOutputParser
from sardis_langchain import SardisPaymentTool

llm = ChatOpenAI(model="gpt-4o")
payment_tool = SardisPaymentTool(api_key="sk_...", wallet_id="wallet_abc123")

chain = (
    RunnableParallel({
        "balance": lambda x: payment_tool.get_balance(),
        "input": RunnablePassthrough()
    })
    | llm
    | StrOutputParser()
)

result = chain.invoke("Should I buy $50 of API credits?")
```

## Multi-Agent Systems

Create multi-agent teams with shared Sardis budgets:

```python
from langchain.agents import create_openai_functions_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from sardis_langchain import SardisToolkit

# Agent 1: Research (low budget)
research_toolkit = SardisToolkit(
    api_key="sk_...",
    wallet_id="wallet_research"  # Policy: $50/day
)
research_tools = research_toolkit.get_tools()
research_agent = create_openai_functions_agent(
    ChatOpenAI(model="gpt-4o"),
    research_tools,
    research_prompt
)
research_executor = AgentExecutor(agent=research_agent, tools=research_tools)

# Agent 2: Procurement (high budget)
procurement_toolkit = SardisToolkit(
    api_key="sk_...",
    wallet_id="wallet_procurement"  # Policy: $5000/day
)
procurement_tools = procurement_toolkit.get_tools()
procurement_agent = create_openai_functions_agent(
    ChatOpenAI(model="gpt-4o"),
    procurement_tools,
    procurement_prompt
)
procurement_executor = AgentExecutor(agent=procurement_agent, tools=procurement_tools)

# Coordinate agents
def coordinate_purchase(item, amount):
    if amount < 100:
        return research_executor.invoke({"input": f"Buy {item} for ${amount}"})
    else:
        return procurement_executor.invoke({"input": f"Buy {item} for ${amount}"})
```

## LangGraph Integration

Use Sardis in LangGraph workflows:

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from sardis_langchain import SardisToolkit

class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], "The messages"]
    payment_status: str

toolkit = SardisToolkit(api_key="sk_...", wallet_id="wallet_abc123")

def payment_node(state: AgentState):
    # Check balance
    balance = toolkit.get_balance()

    # Execute payment if sufficient
    if balance > 50:
        result = toolkit.execute_payment(
            to="0x...",
            amount=50,
            token="USDC"
        )
        state["payment_status"] = "success"
    else:
        state["payment_status"] = "insufficient_funds"

    return state

# Build graph
graph = StateGraph(AgentState)
graph.add_node("payment", payment_node)
graph.set_entry_point("payment")
graph.add_edge("payment", END)

app = graph.compile()
result = app.invoke({"messages": [], "payment_status": ""})
```

## ReAct Agent Pattern

Sardis works great with ReAct (Reasoning + Acting) agents:

```python
from langchain.agents import create_react_agent, AgentExecutor
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from sardis_langchain import SardisToolkit

llm = ChatOpenAI(model="gpt-4o", temperature=0)
toolkit = SardisToolkit(api_key="sk_...", wallet_id="wallet_abc123")
tools = toolkit.get_tools()

react_prompt = PromptTemplate.from_template("""
Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Question: {input}
Thought: {agent_scratchpad}
""")

agent = create_react_agent(llm, tools, react_prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({
    "input": "Check my balance and if I have enough, pay $50 to OpenAI"
})
```

## Async Support

Sardis tools support async execution:

```python
from sardis_langchain import SardisPaymentTool

payment_tool = SardisPaymentTool(api_key="sk_...", wallet_id="wallet_abc123")

# Async execution
result = await payment_tool._arun(
    to="0x...",
    amount=50,
    token="USDC"
)
```

## Error Handling

```python
from sardis_langchain import SardisToolkit, SardisException

toolkit = SardisToolkit(api_key="sk_...", wallet_id="wallet_abc123")

try:
    result = toolkit.execute_payment(
        to="0x...",
        amount=10000,  # Exceeds policy
        token="USDC"
    )
except SardisException as e:
    if e.type == "policy_violation":
        print(f"Policy error: {e.message}")
    elif e.type == "insufficient_balance":
        print(f"Balance error: {e.message}")
    else:
        print(f"Error: {e.message}")
```

## Memory Integration

Use with LangChain memory:

```python
from langchain.memory import ConversationBufferMemory
from langchain.agents import AgentExecutor
from sardis_langchain import SardisToolkit

# Add memory for transaction history
memory = ConversationBufferMemory(
    memory_key="chat_history",
    return_messages=True
)

toolkit = SardisToolkit(api_key="sk_...", wallet_id="wallet_abc123")
tools = toolkit.get_tools()

executor = AgentExecutor(
    agent=agent,
    tools=tools,
    memory=memory,
    verbose=True
)

# Agent remembers previous transactions
executor.invoke({"input": "Pay $50 to OpenAI"})
executor.invoke({"input": "What was the last payment I made?"})
# Agent can recall: "You paid $50 to OpenAI"
```

## Best Practices

1. **Use specific wallet IDs** - One wallet per agent/use case
2. **Set conservative policies** - Start restrictive, expand later
3. **Enable callbacks** - Monitor all payment activity
4. **Handle errors gracefully** - Catch policy violations
5. **Use async for performance** - Parallel tool execution
6. **Test in simulation mode** - Validate before production
7. **Monitor trust scores** - Track agent behavior

## Examples

See full examples in the [Sardis LangChain Examples](https://github.com/sardis-labs/sardis/tree/main/examples/langchain) repository:

- Basic payment agent
- Multi-agent procurement team
- ReAct reasoning agent
- LangGraph payment workflow
- Async batch payments

## Next Steps

- [MCP Server](mcp.md) - Claude Desktop integration
- [Spending Policies](../concepts/policies.md) - Define guardrails
- [API Reference](../api/rest.md) - Direct API access
- [Python SDK](../sdks/python.md) - SDK reference

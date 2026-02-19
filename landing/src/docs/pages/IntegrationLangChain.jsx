export default function DocsIntegrationLangChain() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">LangChain Integration</h1>
        <p className="text-xl text-muted-foreground">
          Add payment capabilities to your LangChain agents with native tool support.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-langchain`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The LangChain integration provides a complete toolkit of payment tools that work seamlessly with LangChain agents.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisToolkit</h3>
        <p className="text-muted-foreground mb-4">
          The main entry point for adding Sardis capabilities to your LangChain agents.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from sardis_langchain import SardisToolkit

# Initialize the toolkit
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Get all Sardis tools
tools = toolkit.get_tools()

# Create your agent
llm = ChatOpenAI(model="gpt-4")
agent = create_react_agent(llm, tools, prompt)
agent_executor = AgentExecutor(agent=agent, tools=tools)

# Run with payment capabilities
result = agent_executor.invoke({
    "input": "Pay $20 to OpenAI for API credits"
})`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <p className="text-muted-foreground mb-4">
          The toolkit provides 5 specialized tools for payment operations:
        </p>

        <h3 className="text-lg font-bold font-display mb-3">SardisPayTool</h3>
        <p className="text-muted-foreground mb-4">
          Execute payments with automatic policy validation.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input schema
{
  "merchant": "api.openai.com",
  "amount": "20.00",
  "token": "USDC",
  "chain": "base",
  "purpose": "API credits for GPT-4"
}

# Tool output
{
  "payment_id": "pay_xyz789",
  "status": "completed",
  "tx_hash": "0x1234...",
  "amount": "20.00",
  "token": "USDC"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisBalanceTool</h3>
        <p className="text-muted-foreground mb-4">
          Check wallet balances across all supported chains.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input (optional filters)
{
  "chain": "base",  # Optional
  "token": "USDC"   # Optional
}

# Tool output
{
  "balances": [
    {
      "chain": "base",
      "token": "USDC",
      "balance": "1250.00",
      "usd_value": "1250.00"
    }
  ],
  "total_usd": "1250.00"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisPolicyCheckTool</h3>
        <p className="text-muted-foreground mb-4">
          Validate if a payment would be allowed before execution.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input
{
  "merchant": "aws.amazon.com",
  "amount": "500.00",
  "purpose": "EC2 instance costs"
}

# Tool output
{
  "allowed": false,
  "reason": "Daily spending limit of $100 would be exceeded"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisSetPolicyTool</h3>
        <p className="text-muted-foreground mb-4">
          Update spending policies with natural language descriptions.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input
{
  "policy": "Allow up to $100 per day for OpenAI, max $20 per transaction"
}

# Tool output
{
  "policy_id": "pol_abc123",
  "status": "active",
  "rules": [
    {
      "type": "daily_limit",
      "merchant_pattern": "*.openai.com",
      "amount": "100.00"
    },
    {
      "type": "transaction_limit",
      "merchant_pattern": "*.openai.com",
      "amount": "20.00"
    }
  ]
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">SardisTransactionsTool</h3>
        <p className="text-muted-foreground mb-4">
          Query transaction history with flexible filtering.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input (all optional)
{
  "merchant": "api.openai.com",
  "start_date": "2024-01-01",
  "end_date": "2024-01-31",
  "limit": 10
}

# Tool output
{
  "transactions": [
    {
      "payment_id": "pay_xyz789",
      "merchant": "api.openai.com",
      "amount": "20.00",
      "token": "USDC",
      "status": "completed",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "total_count": 42
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Observability with Callbacks
        </h2>

        <p className="text-muted-foreground mb-4">
          Track payment events and agent behavior with the SardisCallbackHandler.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_langchain import SardisToolkit, SardisCallbackHandler

toolkit = SardisToolkit(api_key="sk_live_...", agent_id="agent_abc123")
callback = SardisCallbackHandler()

agent_executor = AgentExecutor(
    agent=agent,
    tools=toolkit.get_tools(),
    callbacks=[callback]
)

result = agent_executor.invoke({"input": "Pay $50 to AWS"})

# Access tracked events
print(callback.payment_events)  # All payment attempts
print(callback.policy_checks)   # All policy validations
print(callback.errors)          # All failures`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: ReAct Agent
        </h2>

        <p className="text-muted-foreground mb-4">
          Complete example of a ReAct agent with payment capabilities.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from langchain.agents import AgentExecutor, create_react_agent
from langchain_openai import ChatOpenAI
from langchain.prompts import PromptTemplate
from sardis_langchain import SardisToolkit

# Initialize
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

llm = ChatOpenAI(model="gpt-4", temperature=0)

# Create ReAct prompt
template = """Answer the following questions as best you can. You have access to payment tools.

Tools:
{tools}

Use this format:
Question: the input question
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (repeat Thought/Action/Action Input/Observation)
Thought: I now know the final answer
Final Answer: the final answer

Question: {input}
{agent_scratchpad}"""

prompt = PromptTemplate.from_template(template)

# Create agent
agent = create_react_agent(llm, toolkit.get_tools(), prompt)
agent_executor = AgentExecutor(
    agent=agent,
    tools=toolkit.get_tools(),
    verbose=True,
    handle_parsing_errors=True
)

# Execute complex task
result = agent_executor.invoke({
    "input": "Check my balance, then pay $20 to OpenAI if I have enough funds"
})

print(result["output"])`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Custom Chain
        </h2>

        <p className="text-muted-foreground mb-4">
          Build custom chains with Sardis tools using LCEL (LangChain Expression Language).
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from sardis_langchain import SardisToolkit

toolkit = SardisToolkit(api_key="sk_live_...", agent_id="agent_abc123")
tools = toolkit.get_tools()

# Get specific tools
pay_tool = next(t for t in tools if t.name == "sardis_pay")
balance_tool = next(t for t in tools if t.name == "sardis_check_balance")

llm = ChatOpenAI(model="gpt-4")

# Build a custom payment chain
payment_chain = (
    RunnablePassthrough.assign(
        balance=lambda x: balance_tool.invoke({})
    )
    | RunnablePassthrough.assign(
        should_pay=lambda x: llm.invoke(
            f"Should I pay {x['amount']} to {x['merchant']}? "
            f"Current balance: {x['balance']}"
        )
    )
    | RunnablePassthrough.assign(
        result=lambda x: pay_tool.invoke({
            "merchant": x["merchant"],
            "amount": x["amount"],
            "token": "USDC",
            "chain": "base",
            "purpose": x.get("purpose", "Payment")
        }) if "yes" in x["should_pay"].content.lower() else None
    )
)

# Execute
result = payment_chain.invoke({
    "merchant": "api.openai.com",
    "amount": "20.00",
    "purpose": "API credits"
})

print(result["result"])`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Always use the SardisCallbackHandler for production deployments to track payment events</li>
          <li>Set appropriate spending policies before deploying autonomous agents</li>
          <li>Use the policy check tool to validate payments before execution in multi-step workflows</li>
          <li>Configure verbose=True during development to see the agent's reasoning process</li>
          <li>Handle tool errors gracefully with handle_parsing_errors=True</li>
        </ul>
      </section>
    </article>
  );
}

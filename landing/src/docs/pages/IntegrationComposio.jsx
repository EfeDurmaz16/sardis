export default function DocsIntegrationComposio() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Composio Integration</h1>
        <p className="text-xl text-muted-foreground">
          Register Sardis payment tools with Composio to give any LLM agent policy-controlled payment capabilities.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-composio`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The Composio integration exposes three Sardis payment functions through a plain Python
          dict (SARDIS_TOOLS) that can be registered with any Composio toolset. Each function
          returns structured dicts for easy downstream processing.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SARDIS_TOOLS</h3>
        <p className="text-muted-foreground mb-4">
          A dict mapping tool names to callable functions, ready to register with Composio.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import os
from composio_openai import ComposioToolSet, App
from sardis_composio import SARDIS_TOOLS

os.environ["SARDIS_API_KEY"] = "sk_live_..."
os.environ["SARDIS_WALLET_ID"] = "wallet_abc123"

# Register Sardis as a custom tool provider
toolset = ComposioToolSet()
toolset.add_tool(SARDIS_TOOLS["sardis_pay"])
toolset.add_tool(SARDIS_TOOLS["sardis_check_balance"])
toolset.add_tool(SARDIS_TOOLS["sardis_check_policy"])

tools = toolset.get_tools()`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <p className="text-muted-foreground mb-4">
          Three functions are exported. All accept optional api_key and wallet_id parameters
          for per-call credential overrides, or fall back to SARDIS_API_KEY and SARDIS_WALLET_ID env vars.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_pay</h3>
        <p className="text-muted-foreground mb-4">
          Execute a policy-controlled payment. Returns a structured dict with status, tx_id,
          amount, and merchant.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_composio import sardis_pay

result = sardis_pay(
    amount=50.00,
    merchant="api.openai.com",
    purpose="GPT-4 API credits",
    # api_key="sk_live_...",   # optional override
    # wallet_id="wallet_...",  # optional override
)

# Return value
{
    "success": True,
    "status": "APPROVED",       # or "BLOCKED"
    "tx_id": "pay_xyz789",
    "message": "",
    "amount": 50.0,
    "merchant": "api.openai.com",
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_balance</h3>
        <p className="text-muted-foreground mb-4">
          Check wallet balance and remaining spending limit.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_composio import sardis_check_balance

result = sardis_check_balance(token="USDC")

# Return value
{
    "success": True,
    "balance": 500.0,
    "remaining": 100.0,
    "token": "USDC",
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_policy</h3>
        <p className="text-muted-foreground mb-4">
          Dry-run policy check — returns whether a payment would pass, and why.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_composio import sardis_check_policy

result = sardis_check_policy(amount=50.00, merchant="api.openai.com")

# Return value (allowed)
{
    "allowed": True,
    "reason": "Allowed: $50.0 to api.openai.com",
    "balance": 500.0,
    "remaining": 100.0,
}

# Return value (blocked)
{
    "allowed": False,
    "reason": "Would exceed limits: $200.0 to api.openai.com",
    "balance": 500.0,
    "remaining": 100.0,
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: LangChain + Composio
        </h2>

        <p className="text-muted-foreground mb-4">
          Using Sardis tools with a LangChain agent through Composio's toolset.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import os
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate
from composio_langchain import ComposioToolSet
from sardis_composio import SARDIS_TOOLS

os.environ["SARDIS_API_KEY"] = "sk_live_..."
os.environ["SARDIS_WALLET_ID"] = "wallet_abc123"

toolset = ComposioToolSet()
for tool_fn in SARDIS_TOOLS.values():
    toolset.add_tool(tool_fn)

tools = toolset.get_tools()
llm = ChatOpenAI(model="gpt-4o")

prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a payment agent. Check policy before every payment."),
    ("human", "{input}"),
    ("placeholder", "{agent_scratchpad}"),
])

agent = create_tool_calling_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

result = executor.invoke({"input": "Check my balance and then pay $30 to Anthropic"})
print(result["output"])`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Direct Function Use
        </h2>

        <p className="text-muted-foreground mb-4">
          The tools can also be called directly without any framework — useful for testing and scripts.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_composio import sardis_check_policy, sardis_pay

# Check policy first
policy = sardis_check_policy(
    amount=50.00,
    merchant="api.openai.com",
    api_key="sk_live_...",
    wallet_id="wallet_abc123",
)

if policy["allowed"]:
    result = sardis_pay(
        amount=50.00,
        merchant="api.openai.com",
        purpose="API credits",
        api_key="sk_live_...",
        wallet_id="wallet_abc123",
    )
    print(f"Payment {result['status']}: tx {result['tx_id']}")
else:
    print(f"Payment blocked: {policy['reason']}")`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Use SARDIS_API_KEY and SARDIS_WALLET_ID env vars to avoid hardcoding credentials</li>
          <li>Call sardis_check_policy before sardis_pay for safer agentic workflows</li>
          <li>The SARDIS_TOOLS dict can be iterated to register all tools at once</li>
          <li>Per-call api_key and wallet_id overrides allow multi-tenant use from one process</li>
          <li>Return dicts are JSON-serializable and safe to pass between agent steps</li>
        </ul>
      </section>
    </article>
  );
}

export default function DocsIntegrationOpenAIAgents() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">OpenAI Agents SDK Integration</h1>
        <p className="text-xl text-muted-foreground">
          Add payment capabilities to OpenAI Agents SDK agents with native function_tool support.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-openai-agents`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The OpenAI Agents SDK integration wraps Sardis payment operations as native
          function_tool decorated functions, so they work seamlessly with the Agents SDK's
          tool-calling loop.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">get_sardis_tools()</h3>
        <p className="text-muted-foreground mb-4">
          Returns all three Sardis tools ready to pass to an Agent. Configure credentials
          once with configure() or via environment variables.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from agents import Agent, Runner
from sardis_openai_agents import configure, get_sardis_tools

# Configure credentials (or use SARDIS_API_KEY + SARDIS_WALLET_ID env vars)
configure(api_key="sk_live_...", wallet_id="wallet_abc123")

agent = Agent(
    name="ProcurementAgent",
    instructions="""You are a procurement agent with access to a Sardis payment wallet.
Always check policy before executing a payment. Never exceed spending limits.""",
    tools=get_sardis_tools(),
)

result = await Runner.run(agent, "Pay $50 to api.openai.com for API credits")
print(result.final_output)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <p className="text-muted-foreground mb-4">
          Three tools are available, each decorated with @function_tool for automatic schema generation.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_pay</h3>
        <p className="text-muted-foreground mb-4">
          Execute a policy-controlled payment from the agent's wallet. Spending limits are
          checked automatically before execution.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool signature
sardis_pay(amount: float, merchant: str, purpose: str = "Payment") -> str

# Example outputs
"APPROVED: $50.00 to api.openai.com (tx: pay_xyz789)"
"BLOCKED by policy: Daily limit of $100 would be exceeded"`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_balance</h3>
        <p className="text-muted-foreground mb-4">
          Check current wallet balance and remaining spending limit.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool signature
sardis_check_balance(token: str = "USDC") -> str

# Example output
"Balance: $500.00 USDC | Remaining limit: $100.00"`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_policy</h3>
        <p className="text-muted-foreground mb-4">
          Dry-run policy check — verify whether a payment would pass before executing it.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool signature
sardis_check_policy(amount: float, merchant: str) -> str

# Example outputs
"WOULD BE ALLOWED: $50.00 to api.openai.com"
"WOULD BE BLOCKED: $50.00 exceeds remaining limit $20.00"`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Configuration
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">configure()</h3>
        <p className="text-muted-foreground mb-4">
          Call configure() before get_sardis_tools() to set credentials programmatically.
          Alternatively, set SARDIS_API_KEY and SARDIS_WALLET_ID environment variables
          and skip configure() entirely.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_openai_agents import configure

# Programmatic configuration
configure(api_key="sk_live_...", wallet_id="wallet_abc123")

# Environment variable configuration (no configure() call needed)
# export SARDIS_API_KEY=sk_live_...
# export SARDIS_WALLET_ID=wallet_abc123`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Interactive Payment Agent
        </h2>

        <p className="text-muted-foreground mb-4">
          Complete interactive agent that checks policy before every payment.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import asyncio
from agents import Agent, Runner
from sardis_openai_agents import get_sardis_tools

SYSTEM_PROMPT = """You are a procurement agent with access to a Sardis payment wallet.
You can check your balance, verify spending policy, and execute payments.
Always check policy before executing a payment. Never exceed spending limits."""

async def main():
    agent = Agent(
        name="ProcurementAgent",
        instructions=SYSTEM_PROMPT,
        tools=get_sardis_tools(),
    )

    print("Sardis Payment Agent ready. Type 'quit' to exit.\\n")

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() in ("quit", "exit"):
            break

        result = await Runner.run(agent, user_input)
        print(f"Agent: {result.final_output}\\n")

asyncio.run(main())`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Handoff Workflow
        </h2>

        <p className="text-muted-foreground mb-4">
          Use handoffs to create a two-agent workflow where a planner delegates to a payment agent.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from agents import Agent, Runner, handoff
from sardis_openai_agents import get_sardis_tools

# Specialist payment agent
payment_agent = Agent(
    name="PaymentSpecialist",
    instructions="Execute payments only after verifying policy. Report tx IDs.",
    tools=get_sardis_tools(),
)

# Orchestrator that hands off to payment agent
orchestrator = Agent(
    name="Orchestrator",
    instructions="""Plan tasks and delegate payments to the PaymentSpecialist.
    Never execute payments yourself.""",
    handoffs=[handoff(payment_agent)],
)

result = await Runner.run(
    orchestrator,
    "I need to pay $30 to Anthropic for Claude API credits"
)
print(result.final_output)`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Always include sardis_check_policy in the agent instructions to enforce pre-payment checks</li>
          <li>Use environment variables for credentials to keep API keys out of source code</li>
          <li>For multi-agent setups, use handoffs so only one specialist agent has payment tools</li>
          <li>Set wallet spending policies before deploying agents to production</li>
          <li>configure() is idempotent — calling it multiple times updates the shared default client</li>
        </ul>
      </section>
    </article>
  );
}

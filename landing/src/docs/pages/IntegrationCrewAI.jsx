export default function DocsIntegrationCrewAI() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">CrewAI Integration</h1>
        <p className="text-xl text-muted-foreground">
          Build multi-agent finance teams with shared budgets and payment capabilities.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-crewai`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The CrewAI integration provides pre-built agents, tasks, and tools optimized for multi-agent financial workflows.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">create_sardis_tools()</h3>
        <p className="text-muted-foreground mb-4">
          Generate all Sardis tools for use with any CrewAI agent.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from crewai import Agent, Task, Crew
from sardis_crewai import create_sardis_tools

# Create Sardis tools
sardis_tools = create_sardis_tools(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Create a custom agent with payment capabilities
finance_agent = Agent(
    role="Finance Manager",
    goal="Manage company expenses efficiently",
    backstory="Expert financial analyst with budget oversight",
    tools=sardis_tools,
    verbose=True
)

# Define a task
task = Task(
    description="Pay $100 to AWS for cloud hosting",
    agent=finance_agent,
    expected_output="Payment confirmation with transaction ID"
)

# Execute
crew = Crew(agents=[finance_agent], tasks=[task])
result = crew.kickoff()
print(result)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Pre-Built Agent Factories
        </h2>

        <p className="text-muted-foreground mb-4">
          Use specialized agent factories for common financial roles.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">create_payment_agent()</h3>
        <p className="text-muted-foreground mb-4">
          Agent optimized for executing payments and managing transactions.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_crewai import create_payment_agent

payment_agent = create_payment_agent(
    api_key="sk_live_...",
    agent_id="agent_abc123",
    llm="gpt-4"  # Optional, defaults to gpt-4
)

# Pre-configured with:
# - Payment execution tool
# - Balance checking tool
# - Policy validation tool
# - Transaction history tool`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">create_auditor_agent()</h3>
        <p className="text-muted-foreground mb-4">
          Read-only agent for financial oversight and compliance monitoring.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_crewai import create_auditor_agent

auditor = create_auditor_agent(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Pre-configured with:
# - Transaction history (read-only)
# - Balance checking (read-only)
# - Policy review (read-only)
# - No payment execution capability`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">create_treasury_agent()</h3>
        <p className="text-muted-foreground mb-4">
          Agent focused on budget management and policy administration.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_crewai import create_treasury_agent

treasury = create_treasury_agent(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Pre-configured with:
# - Policy creation and updates
# - Budget allocation
# - Spending limit management
# - Balance monitoring across chains`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Pre-Built Task Templates
        </h2>

        <p className="text-muted-foreground mb-4">
          Common task templates for financial workflows.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_crewai import (
    create_payment_task,
    create_audit_task,
    create_budget_review_task
)

# Payment execution task
pay_task = create_payment_task(
    merchant="api.openai.com",
    amount="50.00",
    purpose="API credits",
    agent=payment_agent
)

# Audit task
audit_task = create_audit_task(
    start_date="2024-01-01",
    end_date="2024-01-31",
    agent=auditor,
    context=[pay_task]  # Runs after payment
)

# Budget review task
review_task = create_budget_review_task(
    period="monthly",
    agent=treasury
)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Multi-Agent Finance Team
        </h2>

        <p className="text-muted-foreground mb-4">
          Complete example of a collaborative finance team with shared budget.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from crewai import Crew, Process
from sardis_crewai import (
    create_payment_agent,
    create_auditor_agent,
    create_treasury_agent,
    create_payment_task,
    create_audit_task
)

# Initialize agents
payment_agent = create_payment_agent(
    api_key="sk_live_...",
    agent_id="agent_payments"
)

auditor = create_auditor_agent(
    api_key="sk_live_...",
    agent_id="agent_auditor"
)

treasury = create_treasury_agent(
    api_key="sk_live_...",
    agent_id="agent_treasury"
)

# Define tasks
set_budget = Task(
    description="""
    Set a monthly budget policy:
    - Max $500 per day for cloud infrastructure (AWS, GCP)
    - Max $100 per day for AI APIs (OpenAI, Anthropic)
    - Max $50 per transaction for development tools
    """,
    agent=treasury,
    expected_output="Policy configuration summary"
)

make_payment = create_payment_task(
    merchant="api.openai.com",
    amount="75.00",
    purpose="GPT-4 API credits for production",
    agent=payment_agent
)

audit_transactions = create_audit_task(
    start_date="2024-01-01",
    end_date="2024-01-31",
    agent=auditor,
    context=[make_payment]
)

# Create crew with sequential process
finance_crew = Crew(
    agents=[treasury, payment_agent, auditor],
    tasks=[set_budget, make_payment, audit_transactions],
    process=Process.sequential,
    verbose=True
)

# Execute the workflow
result = finance_crew.kickoff()

print("\\n=== Finance Team Results ===")
print(result)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Hierarchical Teams
        </h2>

        <p className="text-muted-foreground mb-4">
          Use hierarchical process for manager-based approval workflows.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from crewai import Crew, Process, Agent
from sardis_crewai import create_payment_agent, create_sardis_tools

# Create payment agents for different departments
eng_payment_agent = create_payment_agent(
    api_key="sk_live_...",
    agent_id="agent_eng",
    llm="gpt-4"
)

marketing_payment_agent = create_payment_agent(
    api_key="sk_live_...",
    agent_id="agent_marketing",
    llm="gpt-4"
)

# Create CFO manager agent
cfo = Agent(
    role="CFO and Finance Manager",
    goal="Approve and oversee all company expenditures",
    backstory="Senior executive with final approval authority",
    tools=create_sardis_tools(
        api_key="sk_live_...",
        agent_id="agent_cfo"
    ),
    verbose=True
)

# Tasks
eng_task = Task(
    description="Pay $200 to AWS for EC2 instances",
    agent=eng_payment_agent,
    expected_output="Payment confirmation"
)

marketing_task = Task(
    description="Pay $150 to Google Ads",
    agent=marketing_payment_agent,
    expected_output="Payment confirmation"
)

# Hierarchical crew with CFO as manager
crew = Crew(
    agents=[eng_payment_agent, marketing_payment_agent, cfo],
    tasks=[eng_task, marketing_task],
    process=Process.hierarchical,
    manager_agent=cfo,
    verbose=True
)

result = crew.kickoff()
print(result)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Shared Budget Pattern
        </h2>

        <p className="text-muted-foreground mb-4">
          Multiple agents can share the same wallet by using the same agent_id.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_crewai import create_payment_agent

# Shared agent_id = shared wallet and budget
SHARED_AGENT_ID = "agent_team_shared"

agent_1 = create_payment_agent(
    api_key="sk_live_...",
    agent_id=SHARED_AGENT_ID  # Same ID
)

agent_2 = create_payment_agent(
    api_key="sk_live_...",
    agent_id=SHARED_AGENT_ID  # Same ID
)

# Both agents:
# - Draw from the same wallet balance
# - Subject to the same spending policies
# - Transactions appear in shared history`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Use create_treasury_agent() to set budgets before deploying payment agents</li>
          <li>Include create_auditor_agent() for compliance monitoring in production crews</li>
          <li>Share agent_id across agents that should share a budget and policy</li>
          <li>Use Process.hierarchical for approval workflows with a manager agent</li>
          <li>Set verbose=True during development to see inter-agent communication</li>
          <li>Use context parameter in tasks to create dependencies between agents</li>
        </ul>
      </section>
    </article>
  );
}

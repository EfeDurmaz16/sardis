export default function DocsIntegrationADK() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Google ADK Integration</h1>
        <p className="text-xl text-muted-foreground">
          Add payment capabilities to Gemini agents using Google's Agent Development Kit.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-adk`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The ADK integration provides Sardis tools as FunctionTool instances compatible with Google's Agent Development Kit.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisToolkit</h3>
        <p className="text-muted-foreground mb-4">
          Initialize the toolkit and get ADK-compatible FunctionTool instances.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from google import genai
from google.genai.types import FunctionCall
from sardis_adk import SardisToolkit

# Initialize the toolkit
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Get all Sardis tools as FunctionTool instances
tools = toolkit.get_tools()

# Create Gemini client with tools
client = genai.Client(api_key="your_google_api_key")
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Pay $20 to OpenAI for API credits",
    config={"tools": tools}
)

print(response.text)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <p className="text-muted-foreground mb-4">
          The toolkit provides 5 tools as plain Python functions wrapped in FunctionTool:
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_pay</h3>
        <p className="text-muted-foreground mb-4">
          Execute a payment to a merchant.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import sardis_pay, configure

# Configure module-level state
configure(api_key="sk_live_...", agent_id="agent_abc123")

# Call directly
result = sardis_pay(
    merchant="api.openai.com",
    amount="20.00",
    token="USDC",
    chain="base",
    purpose="API credits"
)

# Returns
{
    "payment_id": "pay_xyz789",
    "status": "completed",
    "tx_hash": "0x1234...",
    "amount": "20.00",
    "token": "USDC"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_balance</h3>
        <p className="text-muted-foreground mb-4">
          Get wallet balances across all chains.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import sardis_check_balance

result = sardis_check_balance(
    chain="base",  # Optional
    token="USDC"   # Optional
)

# Returns
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

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_policy</h3>
        <p className="text-muted-foreground mb-4">
          Validate if a payment would be allowed.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import sardis_check_policy

result = sardis_check_policy(
    merchant="aws.amazon.com",
    amount="500.00",
    purpose="EC2 hosting"
)

# Returns
{
    "allowed": false,
    "reason": "Daily limit of $100 would be exceeded"
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_set_policy</h3>
        <p className="text-muted-foreground mb-4">
          Update spending policies.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import sardis_set_policy

result = sardis_set_policy(
    policy="Allow up to $100 per day for OpenAI, max $20 per transaction"
)

# Returns
{
    "policy_id": "pol_abc123",
    "status": "active",
    "rules": [...]
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_list_transactions</h3>
        <p className="text-muted-foreground mb-4">
          Query transaction history.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import sardis_list_transactions

result = sardis_list_transactions(
    merchant="api.openai.com",  # Optional
    start_date="2024-01-01",    # Optional
    end_date="2024-01-31",      # Optional
    limit=10                     # Optional
)

# Returns
{
    "transactions": [...],
    "total_count": 42
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Module Configuration
        </h2>

        <p className="text-muted-foreground mb-4">
          Use configure() to set module-level state for direct function calls.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_adk import configure, sardis_pay, sardis_check_balance

# Configure once at startup
configure(
    api_key="sk_live_...",
    agent_id="agent_abc123",
    base_url="https://api.sardis.sh"  # Optional
)

# Now all functions use the configured state
balance = sardis_check_balance()
payment = sardis_pay(
    merchant="api.openai.com",
    amount="20.00",
    token="USDC",
    chain="base",
    purpose="API credits"
)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Gemini Agent with Payments
        </h2>

        <p className="text-muted-foreground mb-4">
          Complete example of a Gemini agent with payment capabilities.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import os
from google import genai
from sardis_adk import SardisToolkit

# Initialize
toolkit = SardisToolkit(
    api_key=os.environ["SARDIS_API_KEY"],
    agent_id="agent_gemini_payments"
)

client = genai.Client(api_key=os.environ["GOOGLE_API_KEY"])

# Create agent with tools
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="""
    You are a financial assistant. You can:
    1. Check balances
    2. Make payments
    3. Review spending policies

    User request: Check my balance, then pay $25 to Anthropic for Claude API.
    """,
    config={
        "tools": toolkit.get_tools(),
        "temperature": 0
    }
)

# Handle function calls
while response.candidates[0].content.parts:
    part = response.candidates[0].content.parts[0]

    if hasattr(part, 'function_call'):
        # Extract function call
        fn_call = part.function_call
        print(f"\\nCalling: {fn_call.name}")
        print(f"Args: {fn_call.args}")

        # Execute (toolkit handles the actual call)
        # In a real implementation, you'd execute the function
        # and feed the result back to the model
        break
    else:
        print(response.text)
        break`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Advanced: Manual Function Execution
        </h2>

        <p className="text-muted-foreground mb-4">
          For custom agent loops, you can manually execute function calls.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from google import genai
from google.genai.types import FunctionCall, FunctionResponse, Part
from sardis_adk import SardisToolkit, configure

# Configure
configure(api_key="sk_live_...", agent_id="agent_abc123")

toolkit = SardisToolkit()
client = genai.Client(api_key="your_google_api_key")

messages = []
user_query = "Pay $30 to OpenAI"

# Initial request
response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents=user_query,
    config={"tools": toolkit.get_tools()}
)

# Agent loop
while True:
    part = response.candidates[0].content.parts[0]

    # Check if it's a function call
    if hasattr(part, 'function_call'):
        fn_call = part.function_call

        # Execute the function
        fn_map = toolkit.get_function_map()
        result = fn_map[fn_call.name](**fn_call.args)

        # Send result back to model
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[
                user_query,
                Part.from_function_response(
                    FunctionResponse(
                        name=fn_call.name,
                        response=result
                    )
                )
            ],
            config={"tools": toolkit.get_tools()}
        )
    else:
        # Final answer
        print(response.text)
        break`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Use configure() at application startup to set credentials once</li>
          <li>Set temperature=0 for financial agents to ensure deterministic behavior</li>
          <li>Always validate function call results before sending back to the model</li>
          <li>Use sardis_check_policy before sardis_pay in multi-step workflows</li>
          <li>Handle function execution errors gracefully in your agent loop</li>
          <li>Use get_function_map() for manual function dispatch in custom loops</li>
        </ul>
      </section>
    </article>
  );
}

export default function DocsIntegrationAgentSDK() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Anthropic Agent SDK Integration</h1>
        <p className="text-xl text-muted-foreground">
          Build Claude-powered agents with native payment tools using Anthropic's Agent SDK.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-agent-sdk`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The Agent SDK integration provides Sardis tools as tool_use JSON definitions compatible with Claude's tool use pattern.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisToolkit</h3>
        <p className="text-muted-foreground mb-4">
          Initialize the toolkit and get tool definitions for Claude.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import anthropic
from sardis_agent_sdk import SardisToolkit

# Initialize the toolkit
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

# Get tool definitions for Claude
tools = toolkit.get_tools()

# Create Claude client
client = anthropic.Anthropic(api_key="your_anthropic_key")

# Send message with tools
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    tools=tools,
    messages=[{
        "role": "user",
        "content": "Pay $20 to OpenAI for API credits"
    }]
)

print(response.content)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Available Tools
        </h2>

        <p className="text-muted-foreground mb-4">
          The toolkit provides 6 tools as tool_use JSON schemas:
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_pay</h3>
        <p className="text-muted-foreground mb-4">
          Execute a payment to a merchant with policy validation.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool schema
{
    "name": "sardis_pay",
    "description": "Execute a payment to a merchant",
    "input_schema": {
        "type": "object",
        "properties": {
            "merchant": {"type": "string"},
            "amount": {"type": "string"},
            "token": {"type": "string"},
            "chain": {"type": "string"},
            "purpose": {"type": "string"}
        },
        "required": ["merchant", "amount", "token", "chain"]
    }
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_balance</h3>
        <p className="text-muted-foreground mb-4">
          Get current wallet balances.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool schema
{
    "name": "sardis_check_balance",
    "description": "Check wallet balance across chains",
    "input_schema": {
        "type": "object",
        "properties": {
            "chain": {"type": "string"},
            "token": {"type": "string"}
        }
    }
}`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">sardis_check_policy</h3>
        <p className="text-muted-foreground mb-4">
          Validate if a payment would be allowed.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_set_policy</h3>
        <p className="text-muted-foreground mb-4">
          Update spending policies with natural language.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_list_transactions</h3>
        <p className="text-muted-foreground mb-4">
          Query transaction history with filtering.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">sardis_create_hold</h3>
        <p className="text-muted-foreground mb-4">
          Create a payment hold that requires explicit release.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Tool input
{
    "merchant": "api.openai.com",
    "amount": "100.00",
    "token": "USDC",
    "chain": "base",
    "duration_hours": 24
}

# Tool output
{
    "hold_id": "hold_xyz789",
    "status": "active",
    "expires_at": "2024-01-16T10:30:00Z"
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Tool Execution
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">handle_tool_call()</h3>
        <p className="text-muted-foreground mb-4">
          Process tool_use blocks and execute Sardis operations.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import anthropic
from sardis_agent_sdk import SardisToolkit

toolkit = SardisToolkit(api_key="sk_live_...", agent_id="agent_abc123")
client = anthropic.Anthropic(api_key="your_anthropic_key")

# Initial request
response = client.messages.create(
    model="claude-3-7-sonnet-20250219",
    max_tokens=1024,
    tools=toolkit.get_tools(),
    messages=[{
        "role": "user",
        "content": "Pay $20 to OpenAI"
    }]
)

# Check for tool use
for block in response.content:
    if block.type == "tool_use":
        # Execute the tool
        result = toolkit.handle_tool_call(
            tool_name=block.name,
            tool_input=block.input
        )

        print(f"Tool: {block.name}")
        print(f"Result: {result}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Agent Loop
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">run_agent_loop()</h3>
        <p className="text-muted-foreground mb-4">
          Automated conversation loop with tool execution.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_agent_sdk import SardisToolkit

toolkit = SardisToolkit(api_key="sk_live_...", agent_id="agent_abc123")

# Run automated agent loop
final_response = toolkit.run_agent_loop(
    anthropic_api_key="your_anthropic_key",
    user_message="Check my balance, then pay $25 to Anthropic for Claude API",
    model="claude-3-7-sonnet-20250219",
    max_turns=10  # Prevent infinite loops
)

print(final_response)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example: Full Agent Loop
        </h2>

        <p className="text-muted-foreground mb-4">
          Complete implementation of an agent with manual tool handling.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import anthropic
from sardis_agent_sdk import SardisToolkit

# Initialize
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123"
)

client = anthropic.Anthropic(api_key="your_anthropic_key")

# Conversation state
messages = [{
    "role": "user",
    "content": "Check my balance, then pay $30 to OpenAI if I have enough"
}]

# Agent loop
while True:
    response = client.messages.create(
        model="claude-3-7-sonnet-20250219",
        max_tokens=2048,
        tools=toolkit.get_tools(),
        messages=messages
    )

    # Check stop reason
    if response.stop_reason == "end_turn":
        # Extract final text
        final_text = next(
            (block.text for block in response.content if hasattr(block, "text")),
            None
        )
        print(f"\\nFinal Answer: {final_text}")
        break

    # Process tool uses
    if response.stop_reason == "tool_use":
        # Add assistant message to history
        messages.append({
            "role": "assistant",
            "content": response.content
        })

        # Execute all tool calls
        tool_results = []
        for block in response.content:
            if block.type == "tool_use":
                print(f"\\nExecuting: {block.name}")
                print(f"Input: {block.input}")

                result = toolkit.handle_tool_call(
                    tool_name=block.name,
                    tool_input=block.input
                )

                print(f"Result: {result}")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": str(result)
                })

        # Add tool results to conversation
        messages.append({
            "role": "user",
            "content": tool_results
        })
    else:
        # Unexpected stop reason
        print(f"Stopped: {response.stop_reason}")
        break`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Read-Only Mode
        </h2>

        <p className="text-muted-foreground mb-4">
          Create observer agents that can query but not execute payments.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_agent_sdk import SardisToolkit

# Read-only toolkit for auditing/monitoring
toolkit = SardisToolkit(
    api_key="sk_live_...",
    agent_id="agent_abc123",
    read_only=True  # Disable payment execution
)

# Only includes:
# - sardis_check_balance
# - sardis_list_transactions
# - sardis_check_policy (validation only)
#
# Excludes:
# - sardis_pay
# - sardis_set_policy
# - sardis_create_hold

tools = toolkit.get_tools()
print(f"Available tools: {[t['name'] for t in tools]}")
# Output: ['sardis_check_balance', 'sardis_list_transactions', 'sardis_check_policy']`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Error Handling
        </h2>

        <p className="text-muted-foreground mb-4">
          Handle tool execution errors gracefully in your agent loop.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_agent_sdk import SardisToolkit, SardisError

toolkit = SardisToolkit(api_key="sk_live_...", agent_id="agent_abc123")

try:
    result = toolkit.handle_tool_call(
        tool_name="sardis_pay",
        tool_input={
            "merchant": "api.openai.com",
            "amount": "999999.00",  # Exceeds balance
            "token": "USDC",
            "chain": "base"
        }
    )
except SardisError as e:
    # Return error to Claude for reasoning
    error_result = {
        "type": "tool_result",
        "tool_use_id": block.id,
        "content": f"Error: {str(e)}",
        "is_error": True
    }

    # Claude will see the error and can retry or adjust`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Best Practices</h3>
        <ul className="text-muted-foreground text-sm space-y-2 list-disc list-inside">
          <li>Use run_agent_loop() for simple use cases, manual loops for custom behavior</li>
          <li>Set max_turns to prevent infinite loops in automated agent execution</li>
          <li>Use read_only=True for monitoring/auditing agents that should not execute payments</li>
          <li>Always pass tool execution errors back to Claude as tool_result blocks</li>
          <li>Use claude-3-7-sonnet-20250219 for best tool use accuracy</li>
          <li>Include conversation context in messages to help Claude reason about multi-step tasks</li>
          <li>Use sardis_create_hold for payments that require human approval workflows</li>
        </ul>
      </section>
    </article>
  );
}

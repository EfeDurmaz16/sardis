export default function DocsSDK() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">
            API REFERENCE
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">SDK Reference</h1>
        <p className="text-xl text-muted-foreground">
          Complete API reference for Python and TypeScript SDKs.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisClient</h3>
        <p className="text-muted-foreground mb-4">
          The main client for interacting with Sardis services.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_sdk import SardisClient

client = SardisClient(
    api_key="your_api_key",
    base_url="https://api.sardis.sh",  # Optional
    timeout=30,  # Optional, seconds
    max_retries=3  # Optional
)`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Payments</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Execute a single mandate
result = client.payments.execute_mandate({
    "psp_domain": "api.openai.com",
    "amount": "20.00",
    "token": "USDC",
    "chain": "base",
    "purpose": "API credits"
})

result.payment_id  # str
result.status      # "pending" | "processing" | "completed" | "failed"
result.tx_hash     # str | None`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Wallets</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Get wallet balance
balance = client.wallets.get_balance(wallet_id="wallet_xxx")

# Create a new wallet
wallet = client.wallets.create(
    agent_id="agent_xxx",
    currency="USDC",
    chain="base"
)

# List all wallets
wallets = client.wallets.list(agent_id="agent_xxx")`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Policy</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from decimal import Decimal

# Check if a payment would be allowed
check = client.policies.check(
    agent_id="agent_xxx",
    amount=Decimal("500.00"),
    currency="USD",
    merchant_id="amazon.com"
)

check.allowed        # bool
check.reason         # str (if blocked)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> TypeScript SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">SardisClient</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({
  apiKey: 'your_api_key',
  baseUrl: 'https://api.sardis.sh', // Optional
  timeout: 30000, // Optional, milliseconds
  maxRetries: 3 // Optional
});`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Payments</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`// Execute a payment mandate
const result = await client.payments.executeMandate({
  psp_domain: 'api.openai.com',
  amount: '20.00',
  token: 'USDC',
  chain: 'base',
  purpose: 'API credits'
});

// Result object
result.payment_id    // string
result.status        // string
result.tx_hash       // string | undefined`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Framework Integrations
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">LangChain (Python)</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis.integrations.langchain import SardisTool

# Add to your agent's tools
tools = [SardisTool()]

# The tool automatically handles:
# - Payment execution
# - Policy validation
# - Virtual card issuance`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Vercel AI SDK (TypeScript)</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { createSardisTools } from '@sardis/ai-sdk';
import { generateText } from 'ai';

const tools = createSardisTools(sardisClient);

const result = await generateText({
  model: openai('gpt-4'),
  tools,
  prompt: 'Pay $20 to OpenAI for API credits'
});`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">OpenAI Functions (Python)</h3>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis.integrations.openai import get_openai_function_schema

# Get the function schema for OpenAI
schema = get_openai_function_schema()

# Use with OpenAI's function calling
response = openai.chat.completions.create(
    model="gpt-4",
    messages=[...],
    functions=[schema]
)`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Error Handling</h3>
        <p className="text-muted-foreground text-sm mb-4">
          All SDK methods throw typed exceptions for error handling.
        </p>
        <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`from sardis_sdk import (
    PolicyViolationError,
    InsufficientBalanceError,
    AuthenticationError
)

try:
    result = client.payments.execute_mandate(...)
except PolicyViolationError as e:
    print(f"Blocked: {e}")
except InsufficientBalanceError:
    print("Not enough funds")`}</pre>
        </div>
      </section>
    </article>
  );
}

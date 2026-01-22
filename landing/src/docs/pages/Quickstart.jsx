export default function DocsQuickstart() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            GETTING STARTED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Quick Start</h1>
        <p className="text-xl text-muted-foreground">
          Get Sardis running in under 5 minutes.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Zero Integration (MCP)
        </h2>
        <p className="text-muted-foreground mb-4">
          The fastest way to start using Sardis with Claude Desktop or Cursor.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npx @sardis/mcp-server start</div>
          </div>
        </div>

        <p className="text-muted-foreground mt-4 mb-4">
          Then add to your <code className="px-1 py-0.5 bg-muted font-mono text-sm">claude_desktop_config.json</code>:
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Installation</h3>
        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ pip install sardis</div>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Basic Usage</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

# Initialize client
client = SardisClient(api_key="your_api_key")

# Create a payment
result = await client.payments.create(
    vendor="OpenAI",
    amount=20.00,
    purpose="GPT-4 API credits"
)

print(f"Success: {result.approved}")
print(f"Card: {result.card_number}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> TypeScript SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Installation</h3>
        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk</div>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Basic Usage</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

// Initialize client
const client = new SardisClient({ apiKey: 'your_api_key' });

// Create a payment
const result = await client.payments.create({
  vendor: 'OpenAI',
  amount: 20.00,
  purpose: 'GPT-4 API credits'
});

console.log('Success:', result.approved);
console.log('Card:', result.cardNumber);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Run the Demo
        </h2>

        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ python examples/simple_payment.py</div>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">Expected output:</p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <pre className="text-[var(--sardis-canvas)]">{`1. Creating wallet with $50 USDC...
2. Executing payment of $2 to OpenAI API...
3. Checking wallet balance...
✓ Demo completed successfully!`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Next Steps</h3>
        <ul className="space-y-2 text-muted-foreground text-sm">
          <li>→ Learn about the <a href="/docs/architecture" className="text-[var(--sardis-orange)] hover:underline">Architecture</a></li>
          <li>→ Explore the <a href="/docs/sdk" className="text-[var(--sardis-orange)] hover:underline">SDK Reference</a></li>
          <li>→ Read the <a href="/docs/whitepaper" className="text-[var(--sardis-orange)] hover:underline">Whitepaper</a></li>
        </ul>
      </section>
    </article>
  );
}

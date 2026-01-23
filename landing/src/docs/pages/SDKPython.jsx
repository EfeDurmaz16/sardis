export default function DocsSDKPython() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Python SDK</h1>
        <p className="text-xl text-muted-foreground">Full-featured async SDK for Python.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ pip install sardis-sdk</div>
            <div className="text-muted-foreground mt-2"># or with uv</div>
            <div className="text-[var(--sardis-orange)]">$ uv add sardis-sdk</div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Create a wallet
    wallet = await client.wallets.create(
        agent_id="my-agent",
        chain="base",
    )

    # Execute a payment
    result = await client.payments.execute({
        "wallet_id": wallet.id,
        "destination": "0x...",
        "amount_minor": 5_000_000,
        "token": "USDC",
    })`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Resources
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Resource</th>
                <th className="px-4 py-2 text-left border-b border-border">Methods</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, get, list, get_balance, fund</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.payments</td><td className="px-4 py-2 border-b border-border text-muted-foreground">execute, execute_mandate</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, capture, release, get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">get, list</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.policies</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create, update, validate</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.ucp</td><td className="px-4 py-2 border-b border-border text-muted-foreground">create_checkout, complete_checkout, get_order</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">client.a2a</td><td className="px-4 py-2 border-b border-border text-muted-foreground">discover_agent, send_payment_request</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Error Handling
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis.errors import (
    SardisError,
    AuthenticationError,
    PolicyViolationError,
    InsufficientBalanceError,
)

try:
    result = await client.payments.execute(...)
except AuthenticationError:
    print("Invalid API key")
except PolicyViolationError as e:
    print(f"Blocked by policy: {e.message}")
except InsufficientBalanceError:
    print("Not enough funds")
except SardisError as e:
    print(f"API error: {e.code}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Environment Variables
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Set environment variable
export SARDIS_API_KEY="sk_..."

# Client will use it automatically
client = SardisClient()`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}

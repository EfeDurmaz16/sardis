export default function DocsA2A() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">PROTOCOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">A2A Protocol</h1>
        <p className="text-xl text-muted-foreground">Agent-to-Agent - Multi-agent communication and payment coordination.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Agent Cards
        </h2>
        <p className="text-muted-foreground mb-4">
          Agents publish their capabilities at <code className="px-1 py-0.5 bg-muted font-mono text-sm">/.well-known/agent-card.json</code>
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "name": "Shopping Agent",
  "url": "https://agent.example.com",
  "capabilities": [
    "payment.execute",
    "checkout.create",
    "mandate.ingest"
  ],
  "payment": {
    "tokens": ["USDC", "USDT"],
    "chains": ["base", "polygon"],
    "protocols": ["AP2", "x402"]
  }
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Message Types
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Type</th>
                <th className="px-4 py-2 text-left border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">PAYMENT_REQUEST</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Request payment execution</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">PAYMENT_RESPONSE</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Payment result with tx_hash</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">CREDENTIAL_REQUEST</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Verify credentials/mandates</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">CHECKOUT_INITIATE</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Start UCP checkout</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Discover agent
    agent = await client.a2a.discover_agent(
        "https://merchant-agent.example.com"
    )

    # Send payment request
    response = await client.a2a.send_payment_request(
        recipient_url=agent.url,
        amount_minor=5_000_000,
        token="USDC",
        chain="base",
    )
    print(f"Payment: {response.tx_hash}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MCP Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_discover_agent</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Discover agent capabilities</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_agent_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get agent card</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_send_message</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Send A2A message</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_request_payment</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Request payment from agent</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

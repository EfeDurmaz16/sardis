export default function DocsMCPServer() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">MCP Server</h1>
        <p className="text-xl text-muted-foreground">36+ tools for Claude, Cursor, and MCP-compatible AI.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Claude Desktop</h3>
            <p className="text-muted-foreground text-sm mb-3">Add to <code className="px-1 py-0.5 bg-muted font-mono text-xs">~/.config/claude/config.json</code>:</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": { "SARDIS_API_KEY": "sk_..." }
    }
  }
}`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Cursor</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`{
  "mcp.servers": {
    "sardis": {
      "command": "npx @sardis/mcp-server start",
      "env": { "SARDIS_API_KEY": "sk_..." }
    }
  }
}`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Payment Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Execute a payment from a wallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_check_policy</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Validate payment against policy</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_transaction</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get transaction details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List wallet transactions</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Wallet Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create a new wallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List all wallets</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_balance</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet balance</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_fund_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Fund wallet (testnet)</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Hold Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create a fund hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_capture_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Capture a hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_release_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Release/void a hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_extend_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Extend hold expiration</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> UCP Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Start a checkout session</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Modify checkout items</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_complete_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Complete and pay</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_apply_discount</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Apply discount code</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_order</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get order details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_track_fulfillment</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Track shipment</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> A2A Tools
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

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Usage Example
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`User: Pay $10 to OpenAI for API credits

Claude: I'll execute that payment for you.
[Uses sardis_pay tool]
Payment completed! Transaction hash: 0x123...`}</pre>
          </div>
        </div>
      </section>
    </article>
  );
}

export default function DocsMCPServer() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-cyan-500/10 border border-cyan-500/30 text-cyan-500">SDKS & TOOLS</span>
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">v0.2.7</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">MCP Server</h1>
        <p className="text-xl text-muted-foreground">
          52 tools for Claude, Cursor, and MCP-compatible AI assistants. Zero-code payment integration.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Setup
        </h2>

        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Bootstrap (Recommended)</h3>
            <p className="text-muted-foreground text-sm mb-3">
              Generate a local config scaffold first:
            </p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">$ npx @sardis/mcp-server init --mode simulated</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Claude Desktop</h3>
            <p className="text-muted-foreground text-sm mb-3">
              Add to <code className="px-1 py-0.5 bg-muted font-mono text-xs">~/Library/Application Support/Claude/claude_desktop_config.json</code> (macOS):
            </p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start", "--env-file", ".env.sardis"],
      "env": {
        "SARDIS_API_KEY": "sk_...",
        "SARDIS_BASE_URL": "https://sardis.sh/api/v2"
      }
    }
  }
}`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Cursor</h3>
            <p className="text-muted-foreground text-sm mb-3">
              Add to <code className="px-1 py-0.5 bg-muted font-mono text-xs">~/.cursor/mcp.json</code>:
            </p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start", "--env-file", ".env.sardis"],
      "env": {
        "SARDIS_API_KEY": "sk_..."
      }
    }
  }
}`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Wallet Tools (8)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create new MPC wallet with optional policy</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet details by ID</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List all wallets for current user</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_balance</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet balance (unified USDC + USD)</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_address</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get deposit address for specific chain</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_policy</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Update wallet spending policy</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_check_policy</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Validate transaction against policy</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_archive_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Archive inactive wallet</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Payment Tools (7)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Execute payment from wallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay_invoice</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Pay structured invoice with line items</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_request_approval</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Request human approval for large transaction</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List transaction history</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_transaction</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get transaction details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_estimate_gas</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Estimate transaction gas fees</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_tx_status</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Check on-chain transaction status</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Fiat Rails Tools (8)
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_fund_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Fund wallet from bank account (on-ramp)</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_withdraw_to_bank</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Withdraw to bank account (off-ramp)</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_fiat_quote</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get on/off-ramp quote with fees</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_funding_status</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Check funding operation status</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_link_bank_account</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Link bank account via Plaid</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_bank_accounts</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List linked bank accounts</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_kyc_status</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Check KYC verification status</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_initiate_kyc</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Start KYC verification flow</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Virtual Card Tools (5)
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Issue virtual card from wallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_cards</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List wallet's virtual cards</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get card details (PAN, expiry)</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_freeze_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Temporarily freeze card</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_cancel_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Permanently cancel card</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Hold Tools (5)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Reserve funds for future capture</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_capture_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Capture held funds (full or partial)</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_release_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Release/void a hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List active holds</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_extend_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Extend hold expiration</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> UCP Commerce Tools (6)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_ucp_discover</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Discover products from merchant</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Start checkout session</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Modify cart items</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_complete_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Complete and pay</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_order</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get order details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_track_fulfillment</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Track order shipment</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> A2A Agent Tools (4)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_discover_agent</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Discover agent via A2A protocol</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_agent_card</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get agent's capability card</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_send_a2a_message</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Send message to another agent</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_request_payment</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Request payment from agent</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Example Conversations
        </h2>

        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-3">Fund wallet from bank</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`User: Fund my wallet with $500 from my bank account

Claude: I'll fund your wallet with $500. Let me check your linked
bank accounts first.

[Uses sardis_list_bank_accounts]

You have Chase ****1234 linked. Proceeding with funding...

[Uses sardis_fund_wallet]

Done! Funding initiated:
- Amount: $500.00 USD
- Method: Bank Transfer (ACH)
- Expected arrival: 1-2 business days
- Funding ID: fund_abc123

Your wallet balance will update once the transfer completes.`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-3">Pay with virtual card</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs overflow-x-auto">
              <pre className="text-[var(--sardis-canvas)]">{`User: Create a virtual card to pay $50 for GitHub Copilot

Claude: I'll create a virtual card for GitHub Copilot.

[Uses sardis_create_card]

Virtual card created:
- Card: 4242 **** **** 1234
- Expiry: 01/27
- CVV: 456
- Limit: $50.00
- Merchant lock: github.com

You can use these details at github.com/billing. The card will
auto-convert USDC from your wallet at 1:1 when you pay.`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Need Help?</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Questions about MCP integration? Check our docs or reach out.
        </p>
        <div className="flex gap-3">
          <a
            href="https://github.com/EfeDurmaz16/sardis/tree/main/packages/sardis-mcp-server"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
          >
            View on GitHub
          </a>
          <a
            href="mailto:dev@sardis.sh"
            className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
          >
            Contact Support
          </a>
        </div>
      </section>
    </article>
  );
}

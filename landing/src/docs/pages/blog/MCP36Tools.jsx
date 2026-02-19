import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function MCP36Tools() {
  return (
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-10">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
      <header className="not-prose mb-10">
        <div className="flex items-center gap-3 mb-5">
          <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            TUTORIAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-5 leading-tight">
          MCP Server: 60+ Tools for AI Payments
        </h1>
        <div className="flex items-center gap-5 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1.5">
            <Calendar className="w-4 h-4" />
            January 27, 2026
          </span>
          <span className="flex items-center gap-1.5">
            <Clock className="w-4 h-4" />
            6 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none prose-p:leading-7 prose-li:leading-7">
        <p className="lead text-xl text-muted-foreground leading-8">
          Our MCP server has grown from 4 tools to 60+. From treasury ACH rails to virtual cards,
          learn how to give Claude or Cursor complete payment capabilities without writing any code.
        </p>

        <h2>The Evolution</h2>
        <p>
          When we launched the Sardis MCP server, it had four basic tools:
          get balance, make payment, list transactions, and request approval.
        </p>
        <p>
          Today, we're shipping 60+ tools that cover the full payment lifecycle—including
          the USD-first treasury lane (v0.8.9) for ACH fund/withdraw and virtual cards via Lithic.
          Your AI agent can now manage wallets, fund from banks, issue virtual cards, and
          pay anywhere Visa is accepted.
        </p>

        <h2>Quick Setup</h2>
        <p>Add this to your Claude Desktop or Cursor MCP configuration:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"],
      "env": {
        "SARDIS_API_KEY": "sk_..."
      }
    }
  }
}`}
          </pre>
        </div>

        <p>Restart your app, and you now have 60+ payment tools available.</p>

        <h2>Tool Categories</h2>

        <h3>Wallet Management (8 tools)</h3>
        <p>Complete wallet lifecycle management:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_wallet</td><td className="p-3 border-b border-border">Create new MPC wallet with policy</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_wallets</td><td className="p-3 border-b border-border">List all wallets</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_wallet</td><td className="p-3 border-b border-border">Get wallet details</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_balance</td><td className="p-3 border-b border-border">Check unified balance (USDC + USD)</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_address</td><td className="p-3 border-b border-border">Get wallet address for a chain</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_policy</td><td className="p-3 border-b border-border">Update spending policy</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_check_policy</td><td className="p-3 border-b border-border">Check if transaction passes policy</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_archive_wallet</td><td className="p-3 border-b border-border">Archive inactive wallet</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Treasury Rails (11 tools) <span className="text-emerald-500 text-sm">UPDATED in v0.8.9</span></h3>
        <p>Fund and withdraw via ACH with financial account and bank-link lifecycle support:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_sync_treasury_account_holder</td><td className="p-3 border-b border-border">Sync financial accounts from provider</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_financial_accounts</td><td className="p-3 border-b border-border">List ISSUING/OPERATING treasury accounts</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_link_external_bank_account</td><td className="p-3 border-b border-border">Link external bank account</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_verify_micro_deposits</td><td className="p-3 border-b border-border">Verify ownership via micro-deposits</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_fund_wallet</td><td className="p-3 border-b border-border">Create ACH collection (fund treasury)</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_withdraw_to_bank</td><td className="p-3 border-b border-border">Create ACH payment (withdraw)</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_funding_status</td><td className="p-3 border-b border-border">Get payment status by token</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_withdrawal_status</td><td className="p-3 border-b border-border">Get withdrawal status by token</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_treasury_balances</td><td className="p-3 border-b border-border">Get latest treasury balance snapshots</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Virtual Cards (5 tools) <span className="text-emerald-500 text-sm">NEW in v0.6</span></h3>
        <p>Issue and manage virtual cards backed by your wallet:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_card</td><td className="p-3 border-b border-border">Issue a virtual card</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_cards</td><td className="p-3 border-b border-border">List all cards</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_card</td><td className="p-3 border-b border-border">Get card details</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_freeze_card</td><td className="p-3 border-b border-border">Temporarily freeze card</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_cancel_card</td><td className="p-3 border-b border-border">Permanently cancel card</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Payments (7 tools)</h3>
        <p>Execute and manage crypto transactions:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay</td><td className="p-3 border-b border-border">Make a payment</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay_invoice</td><td className="p-3 border-b border-border">Pay a structured invoice</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_request_approval</td><td className="p-3 border-b border-border">Request human approval</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_transactions</td><td className="p-3 border-b border-border">View transaction history</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_transaction</td><td className="p-3 border-b border-border">Get transaction details</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_estimate_gas</td><td className="p-3 border-b border-border">Estimate transaction cost</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_tx_status</td><td className="p-3 border-b border-border">Check transaction status</td></tr>
            </tbody>
          </table>
        </div>

        <h2>Example: Full Payment Flow</h2>
        <p>
          Here's what Claude can do with these tools. Just say: "Fund my wallet with $100 from
          my bank, then pay $50 for OpenAI credits using a virtual card"
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`1. sardis_list_financial_accounts → Find ISSUING/OPERATING account
2. sardis_fund_wallet → Fund $100 from linked external bank account
3. sardis_get_funding_status → Wait for funding to complete
4. sardis_get_treasury_balances → Verify treasury snapshot
5. sardis_create_card → Issue virtual card (limit: $50)
6. Returns: Card number, expiry, CVV for use at openai.com

The agent handles the entire flow, including:
- Replay-safe payment status tracking
- Policy validation at each step
- Waiting for funding confirmation
- Card issuance with merchant lock`}
          </pre>
        </div>

        <h2>Unified Balance</h2>
        <p>
          Unified balance means one policy budget across USD and stablecoin rails.
          You can fund with fiat or USDC, and Sardis chooses the configured route.
          Cross-rail conversion is quote-driven and can be batched to reduce cost.
        </p>

        <div className="not-prose p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mb-6">
          <div className="flex gap-3">
            <div className="text-[var(--sardis-orange)] mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
              </svg>
            </div>
            <div>
              <div className="font-bold text-[var(--sardis-orange)] mb-1">Pro Tips</div>
              <ul className="text-sm text-muted-foreground space-y-1 list-disc list-inside">
                <li>Use <code>sardis_check_policy</code> before large transactions</li>
                <li>Issue single-use virtual cards for one-time purchases</li>
                <li>Link bank account once, fund multiple times</li>
                <li>Use <code>sardis_request_approval</code> for amounts near policy limits</li>
              </ul>
            </div>
          </div>
        </div>

        <h2>What's Next</h2>
        <p>
          We're working on:
        </p>
        <ul>
          <li><strong>Recurring payments:</strong> Set up automatic subscriptions</li>
          <li><strong>Multi-wallet transfers:</strong> Move funds between wallets</li>
          <li><strong>Spending reports:</strong> Generate analytics from MCP</li>
          <li><strong>Webhook management:</strong> Configure notifications from MCP</li>
        </ul>

        <p>
          Have a tool you'd like to see? Let us know on{' '}
          <a href="https://github.com/EfeDurmaz16/sardis/issues" className="text-[var(--sardis-orange)]">GitHub</a>.
        </p>

        <p>
          Read the full <Link to="/docs/mcp-server" className="text-[var(--sardis-orange)]">MCP Server documentation</Link> for
          detailed usage instructions.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Team
          </div>
          <button className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors">
            <Share2 className="w-4 h-4" />
            Share
          </button>
        </div>
      </footer>
    </article>
  );
}

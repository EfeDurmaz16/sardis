import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function MCP36Tools() {
  return (
    <article className="prose prose-invert max-w-none">
      {/* Back link */}
      <div className="not-prose mb-8">
        <Link
          to="/docs/blog"
          className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
        >
          <ArrowLeft className="w-4 h-4" />
          Back to Blog
        </Link>
      </div>

      {/* Header */}
      <header className="not-prose mb-8">
        <div className="flex items-center gap-3 mb-4">
          <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            TUTORIAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          MCP Server: 36+ Tools for AI Payments
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 18, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />5 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Our MCP server has expanded from 4 tools to 36+. From checkout sessions to
          agent discovery, learn how to add comprehensive payment capabilities to
          Claude Desktop and Cursor without writing code.
        </p>

        <h2>The Evolution</h2>
        <p>
          When we launched the Sardis MCP server six months ago, it had four tools:
          get balance, make payment, list transactions, and request approval. Simple,
          but limited.
        </p>
        <p>
          Today, we're shipping 36+ tools that cover the entire payment lifecycle.
          Your AI agent can now manage wallets, issue virtual cards, handle checkout
          flows, coordinate with other agents, and more - all through Claude Desktop
          or Cursor.
        </p>

        <h2>Quick Setup</h2>
        <p>Add this to your Claude Desktop or Cursor configuration:</p>

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

        <p>Restart your app, and you now have 36+ payment tools available.</p>

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
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_balance</td><td className="p-3 border-b border-border">Check wallet balance</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_address</td><td className="p-3 border-b border-border">Get wallet address for a chain</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_policy</td><td className="p-3 border-b border-border">Update spending policy</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_check_policy</td><td className="p-3 border-b border-border">Check if transaction passes policy</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_archive_wallet</td><td className="p-3 border-b border-border">Archive inactive wallet</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Payments (7 tools)</h3>
        <p>Execute and manage transactions:</p>

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

        <h3>Holds & Pre-authorization (5 tools)</h3>
        <p>Reserve funds before final purchase:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_hold</td><td className="p-3 border-b border-border">Create a hold on funds</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_capture_hold</td><td className="p-3 border-b border-border">Capture held funds</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_release_hold</td><td className="p-3 border-b border-border">Release a hold</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_holds</td><td className="p-3 border-b border-border">List active holds</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_hold</td><td className="p-3 border-b border-border">Get hold details</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Virtual Cards (5 tools)</h3>
        <p>Issue and manage virtual cards:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_issue_card</td><td className="p-3 border-b border-border">Issue a virtual card</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_cards</td><td className="p-3 border-b border-border">List all cards</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_card</td><td className="p-3 border-b border-border">Get card details</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_freeze_card</td><td className="p-3 border-b border-border">Temporarily freeze card</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_cancel_card</td><td className="p-3 border-b border-border">Permanently cancel card</td></tr>
            </tbody>
          </table>
        </div>

        <h3>UCP Commerce (4 tools)</h3>
        <p>Interact with UCP-enabled merchants:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_ucp_discover</td><td className="p-3 border-b border-border">Discover products from merchant</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_ucp_checkout</td><td className="p-3 border-b border-border">Create checkout session</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_ucp_confirm</td><td className="p-3 border-b border-border">Confirm and pay</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_ucp_cancel</td><td className="p-3 border-b border-border">Cancel checkout</td></tr>
            </tbody>
          </table>
        </div>

        <h3>A2A Agent Coordination (4 tools)</h3>
        <p>Communicate with other AI agents:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_a2a_discover</td><td className="p-3 border-b border-border">Find other A2A agents</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_a2a_request</td><td className="p-3 border-b border-border">Send payment request</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_a2a_respond</td><td className="p-3 border-b border-border">Respond to request</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_a2a_status</td><td className="p-3 border-b border-border">Check request status</td></tr>
            </tbody>
          </table>
        </div>

        <h3>Utilities (3 tools)</h3>
        <p>Helper tools for common operations:</p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Tool</th>
                <th className="text-left p-3 border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_prices</td><td className="p-3 border-b border-border">Get token prices</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_resolve_ens</td><td className="p-3 border-b border-border">Resolve ENS names</td></tr>
              <tr><td className="p-3 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_verify_address</td><td className="p-3 border-b border-border">Validate wallet address</td></tr>
            </tbody>
          </table>
        </div>

        <h2>Example Workflows</h2>

        <h3>Buying API Credits</h3>
        <p>
          Here's what Claude can do with these tools. Just say: "Buy $50 of OpenAI
          API credits"
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`1. sardis_get_balance → Check if wallet has sufficient funds
2. sardis_check_policy → Verify $50 is within policy limits
3. sardis_ucp_discover → Find OpenAI credit products
4. sardis_ucp_checkout → Create checkout session
5. sardis_ucp_confirm → Execute payment
6. Returns: Transaction hash and confirmation`}
          </pre>
        </div>

        <h3>Managing Subscriptions</h3>
        <p>
          "Cancel my unused subscriptions and reallocate the budget to cloud compute"
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`1. sardis_list_cards → Find active virtual cards
2. sardis_list_transactions → Analyze spending patterns
3. sardis_cancel_card → Cancel unused subscription cards
4. sardis_update_policy → Increase cloud compute allocation
5. sardis_create_hold → Reserve funds for next compute purchase`}
          </pre>
        </div>

        <h2>Best Practices</h2>

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
                <li>Always use <code>sardis_check_policy</code> before large transactions</li>
                <li>Use holds for multi-step purchases to reserve funds</li>
                <li>Issue single-use virtual cards for one-time purchases</li>
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
          <li><strong>Multi-wallet operations:</strong> Transfer between wallets</li>
          <li><strong>Reporting tools:</strong> Generate spending reports</li>
          <li><strong>Webhook management:</strong> Configure notifications from MCP</li>
        </ul>

        <p>
          Have a tool you'd like to see? Let us know on <a href="https://discord.gg/sardis" className="text-[var(--sardis-orange)]">Discord</a> or
          open an issue on <a href="https://github.com/sardis-pay" className="text-[var(--sardis-orange)]">GitHub</a>.
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

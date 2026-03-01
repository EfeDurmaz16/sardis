import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";

export default function SardisV05Protocols() {
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
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 border border-purple-500/30 text-purple-500">
            RELEASE
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Sardis v0.5: UCP and A2A Protocol Support
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 24, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />6 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Today we release Sardis v0.5 with full support for UCP (Universal Commerce Protocol)
          and A2A (Agent-to-Agent) protocol. Now your agents can participate in the broader
          AI agent economy with standardized checkout flows and multi-agent communication.
        </p>

        <h2>What's New in v0.5</h2>
        <p>
          This release marks a significant milestone in Sardis's journey to become the
          universal payment layer for AI agents. We've added two major protocol integrations:
        </p>

        <ul>
          <li>
            <strong>UCP (Universal Commerce Protocol):</strong> Standardized checkout flows
            that work across any merchant, any platform.
          </li>
          <li>
            <strong>A2A (Agent-to-Agent):</strong> Google's multi-agent communication protocol
            for coordinated transactions between AI agents.
          </li>
        </ul>

        <h2>UCP: Universal Commerce Protocol</h2>
        <p>
          UCP solves a fundamental problem in agent commerce: every merchant has a different
          checkout flow. Some require clicking through modals, others need form submissions,
          and many still rely on legacy payment pages.
        </p>
        <p>
          With UCP, merchants expose a standardized API that agents can interact with
          programmatically. The protocol defines three phases:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   DISCOVER  │ ──▶ │   CHECKOUT   │ ──▶ │   CONFIRM   │
│             │     │              │     │             │
│ Find items  │     │ Create cart  │     │ Execute pay │
│ Get pricing │     │ Apply policy │     │ Get receipt │
└─────────────┘     └──────────────┘     └─────────────┘`}
          </pre>
        </div>

        <p>Here's how it works with Sardis:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`from sardis import Sardis
from sardis.protocols import UCP

client = Sardis(api_key="sk_...")

# Discover products from a UCP-enabled merchant
products = await UCP.discover(
    merchant="https://api.example.com/ucp",
    query="cloud compute instances"
)

# Create checkout session
checkout = await UCP.checkout(
    merchant="https://api.example.com/ucp",
    items=[{"sku": "compute-m1", "qty": 1}],
    wallet=client.wallets.get("agent-wallet")
)

# Execute payment (policy-checked automatically)
result = await checkout.confirm()`}
          </pre>
        </div>

        <h2>A2A: Agent-to-Agent Protocol</h2>
        <p>
          A2A is Google's protocol for multi-agent communication. It enables complex
          scenarios where multiple agents need to coordinate on financial transactions.
        </p>
        <p>
          Consider a travel booking scenario: one agent finds flights, another finds hotels,
          and a third handles payments. A2A provides the communication layer for these agents
          to share context, negotiate prices, and execute coordinated purchases.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`from sardis.protocols import A2A

# Register as an A2A-capable agent
agent = A2A.Agent(
    name="payment-agent",
    capabilities=["pay", "refund", "balance"],
    wallet=client.wallets.get("treasury")
)

# Handle payment requests from other agents
@agent.on("payment_request")
async def handle_payment(request):
    # Policy check happens automatically
    result = await request.execute()
    return A2A.Response(
        status="completed",
        tx_hash=result.tx_hash
    )

# Start listening for A2A messages
await agent.serve()`}
          </pre>
        </div>

        <h2>Protocol Synergy</h2>
        <p>
          The real power comes from combining these protocols. An A2A agent swarm can
          use UCP to interact with merchants while Sardis ensures every payment stays
          within policy bounds.
        </p>

        <div className="not-prose p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mb-6">
          <div className="flex gap-3">
            <div className="text-[var(--sardis-orange)] mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="font-bold text-[var(--sardis-orange)] mb-1">Protocol Stack</div>
              <div className="text-sm text-muted-foreground">
                Sardis now supports the complete agent payment stack: AP2 for payment authorization,
                TAP for identity verification, UCP for commerce flows, and A2A for multi-agent coordination.
              </div>
            </div>
          </div>
        </div>

        <h2>Updated MCP Tools</h2>
        <p>
          Our MCP server has been updated with new tools for both protocols:
        </p>

        <ul>
          <li><code>sardis_ucp_discover</code> - Discover products from UCP merchants</li>
          <li><code>sardis_ucp_checkout</code> - Create checkout sessions</li>
          <li><code>sardis_ucp_confirm</code> - Execute UCP payments</li>
          <li><code>sardis_a2a_register</code> - Register as an A2A agent</li>
          <li><code>sardis_a2a_discover</code> - Find other A2A agents</li>
          <li><code>sardis_a2a_request</code> - Send payment requests to agents</li>
        </ul>

        <h2>Migration Guide</h2>
        <p>
          Upgrading to v0.5 is straightforward. The new protocols are additive -
          existing AP2 and TAP integrations continue to work unchanged.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400"># Python</div>
          <div className="text-[var(--sardis-canvas)]">pip install --upgrade sardis</div>
          <div className="text-emerald-400 mt-4"># TypeScript</div>
          <div className="text-[var(--sardis-canvas)]">npm install @sardis/sdk@latest</div>
          <div className="text-emerald-400 mt-4"># MCP Server</div>
          <div className="text-[var(--sardis-canvas)]">npx @sardis/mcp-server@latest start</div>
        </div>

        <h2>What's Next</h2>
        <p>
          With v0.5, Sardis supports all major agent payment protocols. Our next focus
          is deepening our compliance integrations for enterprise customers. Solana
          support is planned for Q3 2026 (requires Anchor programs); Cosmos is on the
          roadmap for a future release.
        </p>
        <p>
          We're also working on a visual policy builder that lets you design complex
          spending rules without writing code. Stay tuned for the announcement.
        </p>

        <p>
          Read the full <Link to="/docs/ucp" className="text-[var(--sardis-orange)]">UCP documentation</Link> or
          check out the <Link to="/docs/a2a" className="text-[var(--sardis-orange)]">A2A guide</Link> to
          get started.
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

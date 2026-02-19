import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function WhySardis() {
  return (
    <>
      <SEO
        title="Why Sardis: The Policy Firewall for Agent Payments"
        description="Sardis fills a critical gap in the agent payment landscape: natural language policy enforcement with non-custodial MPC security, virtual cards, and zero-config MCP server integration."
        path="/docs/blog/why-sardis"
        type="article"
        article={{ publishedDate: '2026-01-24' }}
        schemas={[
          createArticleSchema({
            title: 'Why Sardis: The Policy Firewall for Agent Payments',
            description: 'Sardis fills a critical gap in the agent payment landscape: natural language policy enforcement with non-custodial MPC security, virtual cards, and zero-config MCP server integration.',
            path: '/docs/blog/why-sardis',
            publishedDate: '2026-01-24',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Why Sardis' },
          ]),
        ]}
      />
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
          <span className="px-2 py-1 text-xs font-mono bg-blue-500/10 border border-blue-500/30 text-blue-500">
            TECHNICAL
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Why Sardis: The Policy Firewall for Agent Payments
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 24, 2026
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />7 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          The AI agent payment infrastructure market is nascent but rapidly evolving.
          We've analyzed the landscape and built Sardis to fill a critical gap:
          natural language policy enforcement with non-custodial security.
        </p>

        <h2>The Market Context</h2>
        <p>
          The agent economy is projected to reach $46 billion in agent-to-agent commerce
          within 3 years. Major players including Visa, Google, OpenAI, PayPal, and
          Mastercard are actively developing agent payment protocols (AP2, A2A, x402).
        </p>
        <p>
          This isn't a question of <em>if</em> agents will transact autonomously—it's
          a question of <em>how safely</em> they'll do it.
        </p>

        <h2>The Competitive Landscape</h2>
        <p>
          Several players have emerged to solve agent payments, each with distinct
          approaches:
        </p>

        <div className="not-prose overflow-x-auto mb-6">
          <table className="w-full text-sm border border-border">
            <thead className="bg-muted/50">
              <tr>
                <th className="text-left p-3 border-b border-border font-mono">Attribute</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Sardis</th>
                <th className="text-left p-3 border-b border-border font-mono">Locus</th>
                <th className="text-left p-3 border-b border-border font-mono">Payman</th>
                <th className="text-left p-3 border-b border-border font-mono">Skyfire</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td className="p-3 border-b border-border">Primary Focus</td>
                <td className="p-3 border-b border-border text-[var(--sardis-orange)] font-medium">Policy Firewall</td>
                <td className="p-3 border-b border-border">Control Layer</td>
                <td className="p-3 border-b border-border">Agent-to-Human</td>
                <td className="p-3 border-b border-border">Identity + Rails</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">NL Policies</td>
                <td className="p-3 border-b border-border text-emerald-400">Core Feature</td>
                <td className="p-3 border-b border-border text-muted-foreground">Basic limits</td>
                <td className="p-3 border-b border-border text-muted-foreground">Basic limits</td>
                <td className="p-3 border-b border-border text-muted-foreground">Spending caps</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">MPC Wallets</td>
                <td className="p-3 border-b border-border text-emerald-400">Yes (Turnkey)</td>
                <td className="p-3 border-b border-border text-muted-foreground">Unknown</td>
                <td className="p-3 border-b border-border text-red-400">No (custodial)</td>
                <td className="p-3 border-b border-border text-emerald-400">Yes</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">Chains</td>
                <td className="p-3 border-b border-border text-emerald-400">Base, Poly, ETH, Arb, OP</td>
                <td className="p-3 border-b border-border text-muted-foreground">Base only</td>
                <td className="p-3 border-b border-border text-muted-foreground">USDC + ACH</td>
                <td className="p-3 border-b border-border">Polygon, Base</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">Virtual Cards</td>
                <td className="p-3 border-b border-border text-emerald-400">Yes (Lithic)</td>
                <td className="p-3 border-b border-border text-red-400">No</td>
                <td className="p-3 border-b border-border text-red-400">No</td>
                <td className="p-3 border-b border-border text-red-400">No</td>
              </tr>
              <tr>
                <td className="p-3 border-b border-border">MCP Server</td>
                <td className="p-3 border-b border-border text-emerald-400">Zero-config</td>
                <td className="p-3 border-b border-border">Demo only</td>
                <td className="p-3 border-b border-border text-red-400">No</td>
                <td className="p-3 border-b border-border">Yes</td>
              </tr>
            </tbody>
          </table>
        </div>

        <h2>The Critical Gap: Policy Intelligence</h2>
        <p>
          Here's what we discovered analyzing the competition:
        </p>

        <div className="not-prose p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mb-6">
          <div className="flex gap-3">
            <div className="text-[var(--sardis-orange)] mt-0.5">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div>
              <div className="font-bold text-[var(--sardis-orange)] mb-1">Critical Insight</div>
              <div className="text-sm text-muted-foreground">
                All competitors are building payment rails or identity layers. None are
                building a comprehensive policy enforcement engine with natural language
                interfaces. This is Sardis's primary differentiation.
              </div>
            </div>
          </div>
        </div>

        <p>
          Competitors offer basic spending limits like "$50/day" or "$500/month."
          Sardis enables complex, context-aware policies in plain English:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-[var(--sardis-canvas)]">
            "Only pay approved vendors in software category, max $100 per transaction,
            require justification for purchases over $50, never pay on weekends"
          </div>
        </div>

        <p>This matters because:</p>
        <ul>
          <li><strong>Financial hallucinations are real:</strong> Agents can confidently make incorrect financial decisions</li>
          <li><strong>Enterprise compliance requires nuance:</strong> Not just spending caps, but category restrictions, time windows, approval workflows</li>
          <li><strong>Non-technical users need control:</strong> Finance teams shouldn't need to write code to set spending rules</li>
        </ul>

        <h2>Our Five Differentiators</h2>

        <h3>1. Natural Language Policy Engine</h3>
        <p>
          Our policy engine parses plain English into structured rules that are
          cryptographically enforced. Every transaction is checked against the policy
          before the MPC signing ceremony begins.
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
{`wallet = client.wallets.create(
    name="procurement-agent",
    chain="base",
    policy="""
        Max $500 per transaction.
        Daily limit $2000.
        Only approved vendors: aws.amazon.com, github.com, openai.com.
        Require approval for any purchase over $250.
        Block gambling, adult, and crypto exchange categories.
    """
)`}
          </pre>
        </div>

        <h3>2. Non-Custodial MPC Wallets</h3>
        <p>
          Unlike custodial solutions, Sardis never holds your private keys. We use
          Turnkey's MPC infrastructure to split keys across multiple parties. No single
          entity—not even Sardis—can move funds unilaterally.
        </p>
        <p>
          This has regulatory advantages too: non-custodial solutions face fewer
          money transmitter requirements in many jurisdictions.
        </p>

        <h3>3. Virtual Cards via Lithic</h3>
        <p>
          We're the only agent payment platform offering instant virtual card issuance.
          This bridges crypto wallets to traditional commerce—your agent can pay anywhere
          Visa is accepted.
        </p>
        <p>Use cases:</p>
        <ul>
          <li>SaaS subscriptions managed by agents</li>
          <li>One-time purchases on traditional e-commerce sites</li>
          <li>Per-card spending limits for additional control</li>
        </ul>

        <h3>4. Zero-Config MCP Server</h3>
        <p>
          One command to add payment capabilities to Claude Desktop or Cursor:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400">$ npx @sardis/mcp-server start</div>
          <div className="text-muted-foreground mt-2"># That's it. 60+ payment and treasury tools available.</div>
        </div>

        <p>
          No configuration files. No API key juggling. The MCP server handles
          authentication, policy enforcement, and transaction execution automatically.
        </p>

        <h3>5. Multi-Chain from Day One</h3>
        <p>
          While competitors focus on single chains (Locus: Base only, Skyfire: Polygon
          primary), Sardis supports Base, Polygon, Ethereum, Arbitrum, and Optimism
          from launch. Agents can optimize for speed, cost, or liquidity depending
          on the transaction.
        </p>

        <h2>Protocol Agnosticism</h2>
        <p>
          Rather than building proprietary protocols that lock in users, we're
          implementing the emerging standards:
        </p>
        <ul>
          <li><strong>AP2:</strong> The Google/PayPal/Visa/Mastercard mandate chain standard</li>
          <li><strong>TAP:</strong> Trust Anchor Protocol for agent identity</li>
          <li><strong>UCP:</strong> Universal Commerce Protocol for checkout flows</li>
          <li><strong>A2A:</strong> Google's agent-to-agent communication protocol</li>
          <li><strong>x402:</strong> Coinbase's HTTP 402 micropayment protocol</li>
        </ul>
        <p>
          Sardis works as a policy layer on top of any protocol. Don't pick winners—
          work with everyone. Become the must-have middleware regardless of which
          protocol wins.
        </p>

        <h2>Building Defensible Moats</h2>

        <h3>Policy Intelligence Network</h3>
        <p>
          Every policy processed improves our understanding of financial governance.
          Over time, this creates:
        </p>
        <ul>
          <li>Policy templates for common use cases</li>
          <li>Anomaly detection before transactions execute</li>
          <li>Compliance suggestions for regulatory requirements</li>
        </ul>

        <h3>Developer Experience</h3>
        <p>
          Sardis should be the easiest agent payment solution to integrate. Period.
        </p>
        <ul>
          <li>5 lines of code to add payments to any agent</li>
          <li>Zero-config MCP server</li>
          <li>Playground for policy testing without real funds</li>
          <li>Comprehensive documentation and examples</li>
        </ul>

        <h3>Hybrid Payments</h3>
        <p>
          No competitor offers both instant virtual cards AND multi-chain crypto.
          This hybrid approach enables:
        </p>
        <ul>
          <li>Any merchant: Cards work everywhere Visa is accepted</li>
          <li>Crypto efficiency: Low-cost settlement for high-volume micropayments</li>
          <li>Flexibility: Let the agent choose the optimal payment method</li>
        </ul>

        <h2>Getting Started</h2>
        <p>
          Ready to give your agents safe financial autonomy? Start with our
          <Link to="/docs/quickstart" className="text-[var(--sardis-orange)]"> quickstart guide</Link> or
          try the <Link to="/docs/mcp-server" className="text-[var(--sardis-orange)]">MCP server</Link> for
          zero-code integration with Claude Desktop.
        </p>
        <p>
          The agent economy needs trust infrastructure. Sardis provides that trust
          through policy intelligence, non-custodial security, and developer-first
          experience.
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
    </>
  );
}

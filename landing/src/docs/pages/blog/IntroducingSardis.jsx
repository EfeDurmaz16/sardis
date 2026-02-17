import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function IntroducingSardis() {
  return (
    <>
      <SEO
        title="Introducing Sardis: Secure Payments for AI Agents"
        description="Sardis provides MPC wallets and natural language policy enforcement so AI agents can transact autonomously while preventing financial hallucination errors."
        path="/docs/blog/introducing-sardis"
        type="article"
        article={{ publishedDate: '2025-01-15' }}
        schemas={[
          createArticleSchema({
            title: 'Introducing Sardis: Secure Payments for AI Agents',
            description: 'Sardis provides MPC wallets and natural language policy enforcement so AI agents can transact autonomously while preventing financial hallucination errors.',
            path: '/docs/blog/introducing-sardis',
            publishedDate: '2025-01-15',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Introducing Sardis' },
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
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            ANNOUNCEMENT
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Introducing Sardis: Secure Payments for AI Agents
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 15, 2025
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />5 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          Today we announce Sardis, a stablecoin execution layer designed
          specifically for AI agents. Learn how MPC wallets and policy
          enforcement enable autonomous financial operations while preventing
          hallucination-driven spending.
        </p>

        <h2>The Problem We're Solving</h2>
        <p>
          AI agents are transforming how we work, but they're stuck in a
          "read-only" trap. They can research, plan, and recommend - but when it
          comes time to actually execute a purchase, they hit a wall: 2FA codes,
          CAPTCHAs, and payment systems designed for humans.
        </p>
        <p>
          We've seen this firsthand. While building AI agents over the past 18
          months, every agent we built hit the same blocker: they couldn't
          complete transactions autonomously. The "last mile" of agent
          productivity remained locked.
        </p>

        <h2>What is Sardis?</h2>
        <p>
          Sardis is a payment infrastructure layer that gives AI agents the
          ability to transact autonomously - with proper guardrails. We provide:
        </p>
        <ul>
          <li>
            <strong>MPC Wallets:</strong> Non-custodial wallets where key shares
            are distributed across parties. No single entity can move funds
            unilaterally.
          </li>
          <li>
            <strong>Policy Engine:</strong> Natural language spending rules that
            agents must follow. "Max $50 per transaction, only approved
            vendors."
          </li>
          <li>
            <strong>Virtual Cards:</strong> Issue virtual Visa/Mastercard
            numbers linked to agent wallets for traditional merchant payments.
          </li>
          <li>
            <strong>Full Auditability:</strong> Every transaction is logged with
            complete context - what the agent was trying to do, why, and
            whether it succeeded.
          </li>
        </ul>

        <h2>Why Now?</h2>
        <p>
          The agent economy is approaching an inflection point. Gartner predicts
          that by 2028, AI agents will autonomously manage 15% of day-to-day
          business decisions. But without proper payment infrastructure, agents
          remain glorified research assistants.
        </p>
        <p>
          Sardis bridges this gap. We're building the financial rails that allow
          agents to execute - not just plan - while keeping humans firmly in
          control through programmable policies.
        </p>

        <h2>How It Works</h2>
        <p>Getting started with Sardis takes minutes:</p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border">
          <div className="text-emerald-400">$ npx @sardis/mcp-server start</div>
          <div className="text-muted-foreground mt-2">
            # That's it. Your agent now has payment capabilities.
          </div>
        </div>

        <p>
          For developers who want more control, our TypeScript and Python SDKs
          provide full programmatic access:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`import { SardisWallet } from '@sardis/sdk';

const wallet = new SardisWallet({
  policy: {
    maxPerTransaction: 50,
    dailyLimit: 500,
    allowedVendors: ['aws.amazon.com', 'github.com']
  }
});

// Agent can now spend within these bounds
await wallet.pay({
  amount: 29.99,
  vendor: 'github.com',
  reason: 'Monthly Pro subscription'
});`}
          </pre>
        </div>

        <h2>What's Next</h2>
        <p>
          We're currently live on Sepolia testnet and working toward mainnet
          launch in Q1 2026. If you're building AI agents and want to give them
          financial autonomy, we'd love to have you as an early design partner.
        </p>
        <p>
          Join our waitlist to get early access, or check out our documentation
          to start building today.
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

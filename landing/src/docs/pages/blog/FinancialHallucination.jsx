import { Link } from "react-router-dom";
import { ArrowLeft, Calendar, Clock, Share2 } from "lucide-react";
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function FinancialHallucination() {
  return (
    <>
      <SEO
        title="Financial Hallucination Prevention: Why AI Needs Guardrails"
        description="AI agents can hallucinate financial transactions just like they hallucinate facts. Learn how Sardis's cryptographic policy enforcement prevents unauthorized spending before funds move."
        path="/docs/blog/financial-hallucination-prevention"
        type="article"
        article={{ publishedDate: '2025-01-10' }}
        schemas={[
          createArticleSchema({
            title: 'Financial Hallucination Prevention: Why AI Needs Guardrails',
            description: 'AI agents can hallucinate financial transactions just like they hallucinate facts. Learn how Sardis\'s cryptographic policy enforcement prevents unauthorized spending before funds move.',
            path: '/docs/blog/financial-hallucination-prevention',
            publishedDate: '2025-01-10',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Financial Hallucination Prevention' },
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
          <span className="px-2 py-1 text-xs font-mono bg-red-500/10 border border-red-500/30 text-red-500">
            SECURITY
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
            FEATURED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">
          Financial Hallucination Prevention: Why AI Needs Guardrails
        </h1>
        <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
          <span className="flex items-center gap-1">
            <Calendar className="w-4 h-4" />
            January 10, 2025
          </span>
          <span className="flex items-center gap-1">
            <Clock className="w-4 h-4" />8 min read
          </span>
        </div>
      </header>

      {/* Content */}
      <div className="prose prose-invert max-w-none">
        <p className="lead text-xl text-muted-foreground">
          AI agents can hallucinate facts, and they can hallucinate financial
          transactions. We explore the risks of unconstrained AI spending and
          how cryptographic policy enforcement provides the solution.
        </p>

        <h2>The Hallucination Problem</h2>
        <p>
          Everyone who has worked with large language models knows about
          hallucinations - when models confidently state things that aren't
          true. But what happens when an AI agent with financial authority
          hallucinates a transaction?
        </p>
        <p>Consider these real scenarios we've observed in testing:</p>
        <ul>
          <li>
            An agent "remembers" a discount code that doesn't exist and attempts
            to apply it repeatedly
          </li>
          <li>
            An agent misinterprets "book a flight" as "book the most expensive
            business class seat"
          </li>
          <li>
            An agent, trying to be helpful, pre-purchases items the user
            mentioned they might want someday
          </li>
          <li>
            An agent rounds up amounts or adds "tips" when the transaction
            doesn't require it
          </li>
        </ul>

        <h2>The Consequences Are Real</h2>
        <p>
          Unlike factual hallucinations that can be corrected with a follow-up
          prompt, financial hallucinations result in real money moving. Once an
          unauthorized transaction completes, you're dealing with chargebacks,
          refund processes, and potentially damaged vendor relationships.
        </p>
        <p>
          The problem is compounded by agent autonomy. An agent running
          overnight might make hundreds of micro-decisions, any of which could
          go wrong. Without proper guardrails, you wake up to a mess.
        </p>

        <h2>Why Traditional Solutions Fail</h2>
        <p>
          You might think: "Just add confirmation prompts." But this defeats the
          purpose of agent autonomy. If a human needs to approve every
          transaction, you haven't really automated anything.
        </p>
        <p>
          Others suggest: "Train the model better." While fine-tuning helps, no
          model is perfect. Financial operations require a higher standard -
          you need cryptographic guarantees, not probabilistic assurances.
        </p>

        <h2>The Sardis Approach: Policy Enforcement</h2>
        <p>
          Sardis solves this with a policy engine that sits between the agent
          and actual fund movement. Policies are defined in natural language
          but enforced cryptographically:
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">
            {`// Define strict boundaries
const policy = {
  maxPerTransaction: 100,
  dailyLimit: 500,
  allowedVendors: ['approved-vendor.com'],
  requireReason: true,
  flagPatterns: ['luxury', 'premium', 'upgrade']
};

// Agent attempts transaction
wallet.pay({ amount: 150, vendor: 'random-store.com' });
// -> REJECTED: exceeds maxPerTransaction
// -> REJECTED: vendor not in allowlist

// This one passes
wallet.pay({
  amount: 25,
  vendor: 'approved-vendor.com',
  reason: 'Monthly subscription renewal'
});
// -> APPROVED`}
          </pre>
        </div>

        <h2>Defense in Depth</h2>
        <p>Our policy enforcement operates at multiple levels:</p>

        <h3>1. Pre-Transaction Validation</h3>
        <p>
          Before any transaction is signed, it's validated against the policy.
          This catches obvious violations immediately.
        </p>

        <h3>2. Cryptographic Signing Requirements</h3>
        <p>
          MPC (Multi-Party Computation) wallets require multiple key shares to
          sign. Sardis holds one share and will refuse to sign transactions that
          violate policy.
        </p>

        <h3>3. Post-Transaction Monitoring</h3>
        <p>
          Even after a transaction completes, our system monitors for patterns
          that might indicate policy drift or attempted circumvention.
        </p>

        <h2>Real-World Examples</h2>
        <p>Here's how our policy engine has prevented issues in production:</p>

        <div className="not-prose border border-border p-4 mb-6">
          <div className="text-sm font-mono">
            <div className="text-red-400 mb-2">BLOCKED TRANSACTION</div>
            <div className="text-muted-foreground">
              Agent: "Booking premium lounge access at $450"
            </div>
            <div className="text-muted-foreground">
              Reason: Exceeds $100 per-transaction limit
            </div>
            <div className="text-muted-foreground">
              Flagged: "premium" in description
            </div>
          </div>
        </div>

        <div className="not-prose border border-border p-4 mb-6">
          <div className="text-sm font-mono">
            <div className="text-emerald-400 mb-2">ALLOWED TRANSACTION</div>
            <div className="text-muted-foreground">
              Agent: "Renewing GitHub Pro at $4/month"
            </div>
            <div className="text-muted-foreground">
              Within limits, approved vendor, valid reason
            </div>
          </div>
        </div>

        <h2>The Balance: Autonomy with Safety</h2>
        <p>
          The goal isn't to restrict agents into uselessness - it's to give them
          freedom within defined boundaries. A well-configured policy allows
          agents to handle routine transactions autonomously while escalating
          anything unusual to humans.
        </p>
        <p>
          Think of it like giving a corporate card to an employee with clear
          expense guidelines. They can book flights and buy supplies without
          asking permission every time, but a $10,000 purchase will get flagged.
        </p>

        <h2>Getting Started</h2>
        <p>
          If you're building AI agents that need to handle money, start with
          strict policies and loosen them over time as you build confidence.
          Our documentation includes policy templates for common use cases.
        </p>
      </div>

      {/* Footer */}
      <footer className="not-prose mt-12 pt-8 border-t border-border">
        <div className="flex items-center justify-between">
          <div className="text-sm text-muted-foreground font-mono">
            Written by the Sardis Security Team
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

import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock } from 'lucide-react';
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function SardisAIAgentPayments() {
  return (
    <>
      <SEO
        title="Sardis AI Agent Payments: What It Is and How It Works"
        description="What is Sardis AI agent payments infrastructure? A practical guide to policy-enforced wallets, virtual cards, and auditable autonomous payment execution."
        path="/docs/blog/sardis-ai-agent-payments"
        type="article"
        article={{ publishedDate: '2026-02-25' }}
        schemas={[
          createArticleSchema({
            title: 'Sardis AI Agent Payments: What It Is and How It Works',
            description: 'A practical guide to Sardis AI agent payments infrastructure: deterministic policy enforcement, approvals, cards, and on-chain rails.',
            path: '/docs/blog/sardis-ai-agent-payments',
            publishedDate: '2026-02-25',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Sardis AI Agent Payments' },
          ]),
        ]}
      />

      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-8">
          <Link
            to="/docs/blog"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>

        <header className="not-prose mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-2 py-1 text-xs font-mono bg-blue-500/10 border border-blue-500/30 text-blue-500">
              GUIDE
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">
            Sardis AI Agent Payments: What It Is and How It Works
          </h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              February 25, 2026
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              4 min read
            </span>
          </div>
        </header>

        <div className="prose prose-invert max-w-none">
          <p className="lead text-xl text-muted-foreground">
            Sardis is AI agent payments infrastructure. It lets autonomous agents execute real transactions
            without giving them unconstrained access to money.
          </p>

          <h2>Why Sardis exists</h2>
          <p>
            AI agents can decide and act quickly, but raw model output is not reliable enough for direct payment
            execution. In finance, a small reasoning error can become a large loss. Sardis adds a deterministic
            control layer between intent and settlement.
          </p>

          <h2>How Sardis AI payments work</h2>
          <ul>
            <li>Agent proposes an action (for example: pay vendor invoice).</li>
            <li>Sardis policy engine evaluates spend limits, merchant/category rules, and risk posture.</li>
            <li>High-risk actions route to approval workflows (including 4-eyes controls where configured).</li>
            <li>Execution happens on the selected rail: virtual card, fiat treasury lane, or on-chain route.</li>
            <li>Decision and execution evidence is captured in an auditable trail.</li>
          </ul>

          <h2>What makes Sardis different</h2>
          <ul>
            <li>Deterministic, fail-closed policy enforcement before money moves.</li>
            <li>Approval quorum controls for sensitive execution lanes.</li>
            <li>Multi-rail support across card, fiat, and on-chain payment paths.</li>
            <li>Operator-grade auditability for compliance and incident review.</li>
          </ul>

          <h2>Who should use Sardis</h2>
          <p>
            Teams building production AI agents for purchasing, treasury operations, or machine-to-machine commerce.
            If you need autonomous execution with control, Sardis is built for that boundary.
          </p>
        </div>
      </article>
    </>
  );
}

import { Link } from 'react-router-dom';
import { ArrowLeft, Calendar, Clock, Share2 } from 'lucide-react';
import SEO, { createArticleSchema, createBreadcrumbSchema } from '@/components/SEO';

export default function SpendingRulesExplainer() {
  return (
    <>
      <SEO
        title="How AI Agent Spending Rules Actually Work — A Plain-English Guide"
        description="No jargon, no code. A practical guide to how Sardis spending policies control what AI agents can and cannot do with money."
        path="/docs/blog/spending-rules-explained"
        type="article"
        article={{ publishedDate: '2026-03-17' }}
        schemas={[
          createArticleSchema({
            title: 'How AI Agent Spending Rules Actually Work — A Plain-English Guide',
            description: 'No jargon, no code. A practical guide to how Sardis spending policies control what AI agents can and cannot do with money.',
            path: '/docs/blog/spending-rules-explained',
            publishedDate: '2026-03-17',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'How AI Agent Spending Rules Actually Work' },
          ]),
        ]}
      />
      <article className="prose dark:prose-invert max-w-none">
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
              EXPLAINER
            </span>
            <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
              FEATURED
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">
            How AI Agent Spending Rules Actually Work
          </h1>
          <p className="text-lg text-muted-foreground mb-4">A plain-English guide for finance teams, engineering leads, and anyone handing money to an AI agent.</p>
          <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              March 17, 2026
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              6 min read
            </span>
          </div>
        </header>

        <p className="text-lg text-muted-foreground leading-relaxed">
          Your AI agent needs to pay for things. Cloud compute, SaaS subscriptions, vendor invoices. But
          giving an agent unrestricted access to a credit card or a crypto wallet is like giving an intern
          the company Amex with no spending limit. You need rules. Here is exactly how they work in Sardis.
        </p>

        <h2>The Core Idea: Rules Before Money Moves</h2>
        <p>
          Every time your agent tries to spend money, Sardis runs the transaction through a <strong>12-check
          enforcement pipeline</strong> before a single dollar moves. If any check fails, the transaction is
          blocked. No exceptions. No overrides by the agent.
        </p>
        <p>
          You write your rules in plain English. Sardis parses them into enforceable policy. The agent never
          sees the raw policy — it just gets "approved" or "denied."
        </p>

        <h2>What You Can Control</h2>

        <h3>1. Spending Limits</h3>
        <p>Set maximum amounts per transaction, per day, per week, or per month.</p>
        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`"Max $100 per transaction"
"Max $500 per day"
"Max $2,000 per month"`}</pre>
        </div>
        <p>
          If your agent tries to spend $150 on a single transaction when the limit is $100, it gets blocked instantly.
          The agent cannot split the transaction to get around the limit — Sardis tracks cumulative spending across
          all time windows.
        </p>

        <h3>2. Merchant & Category Controls</h3>
        <p>Whitelist or blacklist specific merchants or entire merchant categories.</p>
        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`"Only pay AWS, Vercel, and Hetzner"
"Block gambling, adult content, and crypto exchanges"
"Allow SaaS and cloud compute categories only"`}</pre>
        </div>
        <p>
          This is not just text matching. Sardis uses standardized merchant category codes (MCCs) to classify
          every payment destination. Even if a merchant changes their display name, the MCC stays the same.
        </p>

        <h3>3. Approval Thresholds</h3>
        <p>Require human approval above a certain amount or for certain types of transactions.</p>
        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`"Require approval above $200"
"Require 2 approvals above $1,000"
"Auto-approve known vendors under $50"`}</pre>
        </div>
        <p>
          When approval is required, Sardis sends a notification to your Slack channel (or webhook endpoint)
          with the full transaction details. The transaction stays frozen until a human clicks "Approve" or "Deny."
          For high-value transactions, you can require multiple approvers (4-eyes principle).
        </p>

        <h3>4. Time-Based Restrictions</h3>
        <p>Control when your agent can spend money.</p>
        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`"Only allow payments during business hours (9am-6pm EST)"
"No payments on weekends"
"Pause all spending after March 31"`}</pre>
        </div>

        <h3>5. Kill Switch</h3>
        <p>
          Instant freeze at 5 different scopes: a single agent, a wallet, a payment rail, a chain, or
          everything globally. One API call. Takes effect in under 100ms.
        </p>

        <h2>What Happens When an Agent Tries to Pay</h2>
        <p>Here is the exact sequence, every single time:</p>

        <div className="not-prose grid gap-3 my-6">
          {[
            { n: '01', title: 'Kill switch check', desc: 'Is spending frozen at any scope? If yes, instant block.' },
            { n: '02', title: 'Policy lookup', desc: 'Load the active spending policy for this agent/wallet.' },
            { n: '03', title: 'Amount validation', desc: 'Is this transaction within the per-transaction limit?' },
            { n: '04', title: 'Daily budget check', desc: 'Would this push the agent over its daily spending cap?' },
            { n: '05', title: 'Weekly/monthly budget', desc: 'Same check for longer time windows.' },
            { n: '06', title: 'Merchant check', desc: 'Is this merchant on the whitelist? Not on the blacklist?' },
            { n: '07', title: 'Category check', desc: 'Is this merchant category allowed by policy?' },
            { n: '08', title: 'Time window check', desc: 'Is it within allowed spending hours?' },
            { n: '09', title: 'First-seen merchant', desc: 'Never paid this merchant before? Lower threshold applies.' },
            { n: '10', title: 'Anomaly scoring', desc: '6-signal risk score — does this look unusual for this agent?' },
            { n: '11', title: 'Approval threshold', desc: 'Does this amount require human approval?' },
            { n: '12', title: 'Compliance check', desc: 'Sanctions screening, KYC/KYA status, regulatory holds.' },
          ].map((step) => (
            <div key={step.n} className="flex gap-4 p-3 border border-border">
              <span className="font-mono text-sm text-[var(--sardis-orange)] font-bold shrink-0">{step.n}</span>
              <div>
                <span className="font-bold text-sm">{step.title}</span>
                <span className="text-sm text-muted-foreground ml-2">{step.desc}</span>
              </div>
            </div>
          ))}
        </div>

        <p>
          All 12 checks run on every transaction. There is no "fast path" that skips checks. The agent cannot
          request a bypass. The policy is enforced at the infrastructure level, not at the application level.
        </p>

        <h2>What Makes This Different from Just Setting a Credit Card Limit</h2>

        <div className="not-prose grid md:grid-cols-2 gap-4 my-6">
          {[
            { title: 'Credit card limit', desc: 'One number. No merchant control, no time windows, no approval workflows, no audit trail.' },
            { title: 'Sardis spending policy', desc: 'Composable rules across 6 dimensions. Every transaction logged with cryptographic proof. Instant kill switch.' },
            { title: 'Bank transfer limits', desc: 'Per-transaction caps only. No category filtering. 3-day settlement. No agent-aware controls.' },
            { title: 'Sardis spending policy', desc: 'Agent-aware. Knows which AI model is spending, why, and whether it matches historical patterns.' },
          ].map((item, i) => (
            <div key={i} className={`p-4 border ${i % 2 === 0 ? 'border-border' : 'border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5'}`}>
              <h4 className="font-bold font-display mb-1 text-sm">{item.title}</h4>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>

        <h2>The Audit Trail: Proof, Not Promises</h2>
        <p>
          Every transaction — approved or denied — gets a signed attestation envelope. This is a
          cryptographic receipt containing: the policy snapshot at the time of the transaction, the
          12-check evaluation results, the agent identity, and a tamper-evident HMAC signature.
        </p>
        <p>
          These receipts are anchored in a Merkle tree. You can independently verify that no transaction
          record has been altered after the fact. This is the level of evidence you need for SOC 2 audits,
          regulatory compliance, and enterprise procurement reviews.
        </p>

        <div className="not-prose p-4 border border-yellow-500/30 bg-yellow-500/10 my-6">
          <p className="text-sm text-muted-foreground">
            <span className="font-bold text-yellow-500">For finance teams:</span> Sardis produces audit-ready
            evidence for every agent payment. No more reconstructing transaction histories from log files.
            Every payment has a self-contained, cryptographically signed proof of policy compliance.
          </p>
        </div>

        <h2>Getting Started</h2>
        <p>
          Install the SDK, create a wallet, define a policy, and make your first payment in under 5 minutes.
          The policy enforces from the first transaction — there is no "grace period" or "learning mode."
        </p>

        <div className="not-prose bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] p-4 font-mono text-sm mb-6 border border-border overflow-x-auto">
          <pre className="text-[var(--sardis-canvas)]">{`pip install sardis

from sardis import Sardis

client = Sardis(api_key="sk_...")
wallet = client.wallets.create(
    name="procurement-agent",
    policy="Max $100/tx, $500/day, SaaS only, require approval above $200"
)

# Your agent can now spend within these exact guardrails`}</pre>
        </div>

        <div className="not-prose mt-8 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Learn More</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              → <Link to="/docs/policies" className="text-[var(--sardis-orange)] hover:underline">Spending Policies Reference</Link>
            </li>
            <li>
              → <Link to="/docs/spending-mandates" className="text-[var(--sardis-orange)] hover:underline">Spending Mandates (Delegated Authority)</Link>
            </li>
            <li>
              → <Link to="/docs/quickstart" className="text-[var(--sardis-orange)] hover:underline">Quickstart Guide</Link>
            </li>
            <li>
              → <Link to="/docs/security" className="text-[var(--sardis-orange)] hover:underline">Security & Audit Trail</Link>
            </li>
          </ul>
        </div>

        <footer className="not-prose mt-12 pt-8 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground font-mono">
              Written by the Sardis team
            </div>
            <button
              className="flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
              onClick={() => navigator.clipboard.writeText(window.location.href)}
            >
              <Share2 className="w-4 h-4" />
              Share
            </button>
          </div>
        </footer>
      </article>
    </>
  );
}

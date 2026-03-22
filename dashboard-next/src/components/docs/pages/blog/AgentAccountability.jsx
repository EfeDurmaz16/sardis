import Link from 'next/link';
import { ArrowLeft, Calendar, Clock, Share2 } from 'lucide-react';

export default function AgentAccountability() {
  return (
    <>
      <SEO
        title="Who Owns Accountability When an AI Agent Moves Money?"
        description="When an AI agent pays the wrong vendor, overspends, or gets exploited — who is responsible? The operator, the model provider, the framework, or the agent itself?"
        path="/docs/blog/agent-accountability"
        type="article"
        article={{ publishedDate: '2026-03-17' }}
        schemas={[
          createArticleSchema({
            title: 'Who Owns Accountability When an AI Agent Moves Money?',
            description: 'When an AI agent pays the wrong vendor, overspends, or gets exploited — who is responsible? The operator, the model provider, the framework, or the agent itself?',
            path: '/docs/blog/agent-accountability',
            publishedDate: '2026-03-17',
          }),
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Blog', href: '/docs/blog' },
            { name: 'Who Owns Accountability When an AI Agent Moves Money?' },
          ]),
        ]}
      />
      <article className="prose dark:prose-invert max-w-none">
        <div className="not-prose mb-8">
          <Link
            href="/docs/blog"
            className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-[var(--sardis-orange)] transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            Back to Blog
          </Link>
        </div>

        <header className="not-prose mb-8">
          <div className="flex items-center gap-3 mb-4">
            <span className="px-2 py-1 text-xs font-mono bg-red-500/10 border border-red-500/30 text-red-500">
              OPINION
            </span>
            <span className="px-2 py-1 text-xs font-mono bg-[var(--sardis-orange)] text-white">
              FEATURED
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">
            Who Owns Accountability When an AI Agent Moves Money?
          </h1>
          <div className="flex items-center gap-4 text-sm text-muted-foreground font-mono">
            <span className="flex items-center gap-1">
              <Calendar className="w-4 h-4" />
              March 17, 2026
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-4 h-4" />
              7 min read
            </span>
          </div>
        </header>

        <p className="text-lg text-muted-foreground leading-relaxed">
          An AI agent, acting on behalf of a company, pays $14,000 to a vendor that does not exist. The
          invoice was fabricated by a prompt injection attack embedded in an email the agent processed.
          The money is gone. Who is responsible?
        </p>

        <h2>The Accountability Gap</h2>
        <p>
          In traditional finance, accountability is clear. An employee makes a payment — the employee is
          responsible. A payment processor moves funds — the processor is responsible. The chain of custody
          is well-defined, regulated, and insured.
        </p>
        <p>
          AI agents break this model. An agent is not an employee. It does not have legal personhood. It
          cannot be fired, sued, or held liable. Yet it can move real money at the speed of an API call.
        </p>
        <p>
          This creates a gap that no one in the current stack is designed to fill:
        </p>

        <div className="not-prose grid gap-3 my-6">
          {[
            { actor: 'The model provider', problem: 'OpenAI, Anthropic, Google — they provide the reasoning engine. They disclaim liability for outputs. Their terms of service explicitly state they are not responsible for actions taken based on model outputs.' },
            { actor: 'The agent framework', problem: 'LangChain, CrewAI, AutoGPT — they provide orchestration. They connect models to tools. They do not govern what those tools do with money.' },
            { actor: 'The operator', problem: 'You — the company deploying the agent. You gave it access to a wallet. You told it to pay invoices. But did you define what it could and could not pay? Did you set limits? Did you monitor?' },
            { actor: 'The agent itself', problem: 'It has no legal standing. It cannot own assets, sign contracts, or be held liable. It is software. The concept of "agent liability" does not exist in any jurisdiction.' },
          ].map((item) => (
            <div key={item.actor} className="p-4 border border-border">
              <h4 className="font-bold text-sm mb-1">{item.actor}</h4>
              <p className="text-sm text-muted-foreground">{item.problem}</p>
            </div>
          ))}
        </div>

        <h2>The Real Question: Who Defined the Guardrails?</h2>
        <p>
          Accountability in the agent economy is not about blame — it is about <strong>who defined the
          constraints under which the agent operated</strong>. If an agent overspends, the question is not
          "why did the agent do this?" but rather "why was the agent allowed to do this?"
        </p>
        <p>
          This is the difference between:
        </p>
        <ul>
          <li><strong>An agent that could spend $14,000 because no one set a limit</strong> — the operator is accountable.</li>
          <li><strong>An agent that was limited to $500/day but a bug bypassed the check</strong> — the infrastructure provider is accountable.</li>
          <li><strong>An agent that was properly constrained but the policy was ambiguous</strong> — a design flaw that needs better tooling.</li>
        </ul>

        <h2>The Infrastructure Layer Owns the Enforcement</h2>
        <p>
          Our position at Sardis is clear: <strong>accountability must be enforced at the infrastructure level,
          not at the application level</strong>.
        </p>
        <p>
          If you enforce spending limits in your application code, the agent can potentially reason its way
          around them. If you enforce them in a policy engine that the agent cannot access, modify, or
          influence — the rules hold.
        </p>

        <div className="not-prose p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 my-6">
          <p className="text-sm text-muted-foreground">
            <span className="font-bold text-[var(--sardis-orange)]">The principle:</span> The agent proposes.
            The infrastructure disposes. The human defines the rules. Every decision is recorded with
            cryptographic evidence. Accountability is distributed across these three layers — not dumped on
            the operator after the fact.
          </p>
        </div>

        <h2>What Good Accountability Looks Like</h2>

        <h3>1. Policy-as-Code</h3>
        <p>
          Every spending rule is versioned, auditable, and enforced at the infrastructure level. When
          something goes wrong, you can point to the exact policy version that was active, the exact check
          that passed or failed, and the exact state of the system at the time of the transaction.
        </p>

        <h3>2. Cryptographic Evidence</h3>
        <p>
          Every transaction produces a signed attestation envelope — a tamper-evident receipt that includes
          the policy snapshot, the evaluation results, the agent identity, and a Merkle proof. This is not
          a log file. This is courtroom-grade evidence.
        </p>

        <h3>3. Separation of Concerns</h3>
        <p>
          The agent decides <em>what</em> to buy. The policy decides <em>whether</em> it is allowed. The
          infrastructure decides <em>how</em> the payment executes. The human defines <em>the rules</em>
          and reviews <em>the evidence</em>. No single layer has unchecked authority.
        </p>

        <h3>4. Kill Switch as a First-Class Primitive</h3>
        <p>
          If something goes wrong, you need to stop it immediately — not after a support ticket, not after
          a review meeting. One API call. Under 100ms. Five scopes of freeze: agent, wallet, rail, chain,
          or global. This is not a feature — it is a safety mechanism.
        </p>

        <h2>The Regulatory Landscape</h2>
        <p>
          Regulators are watching. The EU AI Act classifies AI systems by risk level. Financial AI agents
          will almost certainly be classified as high-risk. The U.S. is moving toward agent-specific
          guidance through FinCEN and the OCC.
        </p>
        <p>
          The companies that will survive regulatory scrutiny are the ones that can demonstrate:
        </p>
        <ul>
          <li>Clear policy definition (who set the rules?)</li>
          <li>Deterministic enforcement (were the rules followed?)</li>
          <li>Complete audit trail (can you prove it?)</li>
          <li>Human oversight mechanisms (could a human intervene?)</li>
        </ul>
        <p>
          This is not about compliance theater. It is about building systems that are accountable by
          design, not accountable by hope.
        </p>

        <h2>The Bottom Line</h2>
        <p>
          When an AI agent moves money, accountability is shared across the stack. The model provider is
          accountable for the reasoning quality. The operator is accountable for the policy definition. The
          infrastructure is accountable for the enforcement. And every layer needs cryptographic evidence to
          prove it did its job.
        </p>
        <p>
          The companies that figure this out will build the financial backbone of the agent economy. The
          ones that do not will be the case studies in why they should have.
        </p>

        <div className="not-prose mt-8 p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Related</h3>
          <ul className="space-y-2 text-sm text-muted-foreground">
            <li>
              → <Link href="/docs/blog/financial-hallucination-prevention" className="text-[var(--sardis-orange)] hover:underline">Financial Hallucination Prevention</Link>
            </li>
            <li>
              → <Link href="/docs/blog/spending-rules-explained" className="text-[var(--sardis-orange)] hover:underline">How AI Agent Spending Rules Actually Work</Link>
            </li>
            <li>
              → <Link href="/docs/security" className="text-[var(--sardis-orange)] hover:underline">Security & Cryptographic Audit Trail</Link>
            </li>
            <li>
              → <Link href="/docs/policies" className="text-[var(--sardis-orange)] hover:underline">Spending Policies Reference</Link>
            </li>
          </ul>
        </div>

        <footer className="not-prose mt-12 pt-8 border-t border-border">
          <div className="flex items-center justify-between">
            <div className="text-sm text-muted-foreground font-mono">
              Written by Efe Baran Durmaz, Founder @ Sardis
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

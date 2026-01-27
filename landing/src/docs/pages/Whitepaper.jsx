export default function DocsWhitepaper() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
            WHITEPAPER
          </span>
          <span>v1.0 — January 2026</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Sardis Whitepaper</h1>
        <p className="text-xl text-muted-foreground">
          The Payment OS for the Agent Economy: Preventing Financial Hallucinations
          Through Programmable Trust.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Abstract
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          As AI agents evolve from conversational assistants to autonomous actors capable of executing
          complex workflows, they encounter a critical limitation: the inability to transact financially.
          Current payment infrastructure is designed to block non-human actors through mechanisms like
          2FA, CAPTCHAs, and behavioral analysis.
        </p>
        <p className="text-muted-foreground leading-relaxed">
          Sardis introduces a novel financial infrastructure layer that provides AI agents with
          non-custodial MPC wallets, natural language spending policies, and a real-time policy engine
          that prevents "financial hallucinations"—the accidental over-spending or mis-spending of
          funds due to agent logic errors.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> The Problem
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">The Read-Only Trap</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          We are transitioning to an Agentic Economy where AI agents perform increasingly complex tasks
          on behalf of humans. Yet these agents remain fundamentally "read-only" when it comes to
          financial transactions. They can browse, plan, and recommend—but they cannot pay.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Financial Hallucination Risk</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Most discourse around AI safety focuses on text hallucinations. We argue that "financial
          hallucination"—an agent accidentally spending $10,000 instead of $100 due to a retry loop,
          decimal error, or logic bug—represents a more immediate and quantifiable risk.
        </p>

        <div className="not-prose p-4 border border-destructive/30 bg-destructive/5 mb-4">
          <h4 className="font-bold font-display text-destructive mb-2">Example: The $10K Bug</h4>
          <p className="text-sm text-muted-foreground">
            An agent tasked with purchasing $100 of API credits enters a retry loop after a timeout.
            Without spending limits, it executes the same purchase 100 times, resulting in $10,000 in charges.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> The Solution
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Financial Firewall</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis implements a "Financial Firewall" that sits between agents and payment rails.
          Every transaction is validated against a set of programmable policies before execution.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Natural Language Policies</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Unlike traditional payment systems that require complex rule configurations, Sardis accepts
          policies in plain English:
        </p>

        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <pre className="text-[var(--sardis-canvas)]">{`"Allow SaaS vendors up to $100 per transaction"
"Block all retail purchases"
"Maximum $500 daily spend"
"Only allow payments to openai.com, github.com, vercel.com"`}</pre>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Non-Custodial Architecture</h3>
        <p className="text-muted-foreground leading-relaxed">
          Sardis uses Multi-Party Computation (MPC) via Turnkey to ensure that agents control their
          own wallets without any single party having access to the complete private key. This provides
          the security of self-custody with the convenience of managed infrastructure.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Market Opportunity
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The "Machine Customer Economy" is projected to reach $30 trillion by 2030 (Gartner).
          As agents become capable of autonomous purchasing decisions, the need for secure,
          programmable payment infrastructure becomes critical.
        </p>

        <div className="not-prose grid md:grid-cols-3 gap-4">
          {[
            { value: '$30T', label: 'Machine Customer Economy by 2030' },
            { value: '85%', label: 'Of B2B transactions will be automated' },
            { value: '10x', label: 'Growth in agent-initiated payments' },
          ].map((stat) => (
            <div key={stat.label} className="p-4 border border-border text-center">
              <div className="text-3xl font-bold font-display text-[var(--sardis-orange)]">{stat.value}</div>
              <div className="text-sm text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Technical Architecture
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis consists of four primary components:
        </p>

        <div className="not-prose space-y-3">
          {[
            { num: '01', title: 'Policy Engine', desc: 'Real-time transaction validation with natural language rule parsing' },
            { num: '02', title: 'MPC Wallets', desc: 'Non-custodial key management via Turnkey infrastructure' },
            { num: '03', title: 'Settlement Layer', desc: 'Multi-rail support: on-chain (Base, Polygon, ETH) and fiat (Lithic cards)' },
            { num: '04', title: 'Integration SDKs', desc: 'Native support for LangChain, Vercel AI, OpenAI, and MCP' },
          ].map((item) => (
            <div key={item.num} className="flex gap-4 p-4 border border-border">
              <div className="font-mono text-[var(--sardis-orange)] font-bold">{item.num}</div>
              <div>
                <h4 className="font-bold font-display">{item.title}</h4>
                <p className="text-sm text-muted-foreground">{item.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Business Model
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis follows an Open Core licensing model:
        </p>

        <div className="not-prose grid md:grid-cols-2 gap-4">
          <div className="p-4 border border-emerald-500/30 bg-emerald-500/5">
            <h4 className="font-bold font-display text-emerald-500 mb-2">Open Source (MIT)</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Python SDK</li>
              <li>• TypeScript SDK</li>
              <li>• MCP Server</li>
              <li>• Integration adapters</li>
            </ul>
          </div>
          <div className="p-4 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
            <h4 className="font-bold font-display text-[var(--sardis-orange)] mb-2">Proprietary</h4>
            <ul className="text-sm text-muted-foreground space-y-1">
              <li>• Policy Engine core</li>
              <li>• MPC node management</li>
              <li>• Compliance infrastructure</li>
              <li>• Enterprise features</li>
            </ul>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Conclusion</h3>
        <p className="text-muted-foreground text-sm mb-4">
          Sardis provides the missing financial infrastructure layer for the Agent Economy.
          By combining non-custodial wallets, natural language policies, and a real-time policy engine,
          we enable agents to transact safely while preventing the financial hallucinations that
          would otherwise make autonomous agent spending too risky to deploy.
        </p>
        <div className="flex gap-3">
          <a href="mailto:contact@sardis.sh"
            className="px-4 py-2 bg-[var(--sardis-orange)] text-white text-sm font-mono hover:bg-[var(--sardis-orange)]/90 transition-colors">
            Contact Us
          </a>
          <a href="https://github.com/EfeDurmaz16/sardis" target="_blank" rel="noreferrer"
            className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">
            View on GitHub
          </a>
        </div>
      </section>
    </article>
  );
}

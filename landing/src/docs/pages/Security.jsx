export default function DocsSecurity() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-red-500/10 border border-red-500/30 text-red-500">
            SECURITY
          </span>
          <span>v1.0 — January 2026</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Security Whitepaper</h1>
        <p className="text-xl text-muted-foreground">
          A comprehensive overview of Sardis security architecture, threat models, and mitigation strategies.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Security Principles
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis is designed with security as a first-class concern. Our architecture follows these core principles:
        </p>

        <div className="not-prose grid md:grid-cols-2 gap-4">
          {[
            { title: 'Non-Custodial', desc: 'Users maintain control of their keys at all times via MPC' },
            { title: 'Defense in Depth', desc: 'Multiple layers of security controls at every level' },
            { title: 'Least Privilege', desc: 'Components have minimal permissions required to function' },
            { title: 'Zero Trust', desc: 'All requests are validated, regardless of source' },
          ].map((item) => (
            <div key={item.title} className="p-4 border border-border">
              <h3 className="font-bold font-display mb-1">{item.title}</h3>
              <p className="text-sm text-muted-foreground">{item.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Threat Model
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Financial Hallucination</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The primary threat Sardis addresses is "financial hallucination"—unintended financial transactions
          caused by agent logic errors, retry loops, or prompt injection attacks.
        </p>

        <div className="not-prose space-y-3 mb-6">
          {[
            { threat: 'Retry Loop Attack', severity: 'HIGH', mitigation: 'Transaction deduplication, rate limiting, daily limits' },
            { threat: 'Decimal Precision Error', severity: 'HIGH', mitigation: 'Strict amount validation, confirmation for large amounts' },
            { threat: 'Prompt Injection', severity: 'MEDIUM', mitigation: 'Policy engine validates all requests, not just prompts' },
            { threat: 'Merchant Impersonation', severity: 'MEDIUM', mitigation: 'Merchant allowlist, domain verification' },
            { threat: 'Session Hijacking', severity: 'LOW', mitigation: 'Short-lived tokens, request signing' },
          ].map((item) => (
            <div key={item.threat} className="flex items-start gap-4 p-4 border border-border">
              <span className={`px-2 py-1 text-xs font-mono font-bold shrink-0 ${
                item.severity === 'HIGH' ? 'bg-red-500/10 text-red-500 border border-red-500/30' :
                item.severity === 'MEDIUM' ? 'bg-yellow-500/10 text-yellow-500 border border-yellow-500/30' :
                'bg-emerald-500/10 text-emerald-500 border border-emerald-500/30'
              }`}>
                {item.severity}
              </span>
              <div>
                <h4 className="font-bold font-display">{item.threat}</h4>
                <p className="text-sm text-muted-foreground">{item.mitigation}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MPC Architecture
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis uses Multi-Party Computation (MPC) via Turnkey to provide non-custodial wallet security.
          The private key is never assembled in any single location.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-xs overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Key Distribution (3-of-3 threshold)
┌─────────────────────────────────────────────────────────┐
│                                                         │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐         │
│   │ Share 1 │     │ Share 2 │     │ Share 3 │         │
│   │ (User)  │     │(Turnkey)│     │(Sardis) │         │
│   └────┬────┘     └────┬────┘     └────┬────┘         │
│        │               │               │               │
│        └───────────────┼───────────────┘               │
│                        │                               │
│                  ┌─────▼─────┐                         │
│                  │  MPC Sign │                         │
│                  └─────┬─────┘                         │
│                        │                               │
│                  ┌─────▼─────┐                         │
│                  │ Signature │                         │
│                  └───────────┘                         │
│                                                         │
│  No single party can sign without cooperation          │
└─────────────────────────────────────────────────────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Policy Engine Security
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The Policy Engine is the critical security component that validates every transaction.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Validation Checks</h3>
        <div className="not-prose mb-6">
          <ul className="space-y-2">
            {[
              'Merchant allowlist/blocklist verification',
              'Transaction amount within defined limits',
              'Daily/weekly/monthly spend limits',
              'Category restrictions enforcement',
              'Rate limiting per agent/wallet',
              'Duplicate transaction detection',
              'Risk score calculation and threshold',
            ].map((check) => (
              <li key={check} className="flex items-center gap-3 text-sm">
                <span className="w-1.5 h-1.5 bg-emerald-500 shrink-0"></span>
                <span className="text-muted-foreground">{check}</span>
              </li>
            ))}
          </ul>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Audit Logging</h3>
        <p className="text-muted-foreground leading-relaxed">
          Every policy decision is logged with full context including the request, policy rules evaluated,
          decision rationale, and cryptographic proof. Logs are immutable and stored for compliance purposes.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Compliance
        </h2>

        <div className="not-prose grid md:grid-cols-2 gap-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">KYC/AML</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Identity verification and anti-money laundering checks via Persona and Elliptic.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              INTEGRATED
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">SOC 2 Type II</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Enterprise security controls and audit procedures.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-yellow-500/10 text-yellow-500 border border-yellow-500/30">
              IN PROGRESS
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">GDPR</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Data protection and privacy compliance for EU users.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              COMPLIANT
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">PCI DSS</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Payment card industry data security standard via Lithic.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              VIA PARTNER
            </span>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-red-500/30 bg-red-500/5">
        <h3 className="font-bold font-display mb-2 text-red-500">Responsible Disclosure</h3>
        <p className="text-muted-foreground text-sm mb-4">
          If you discover a security vulnerability, please report it responsibly:
        </p>
        <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-sm">
          <span className="text-muted-foreground">Email:</span>{' '}
          <a href="mailto:security@sardis.sh" className="text-[var(--sardis-orange)]">security@sardis.sh</a>
        </div>
        <p className="text-muted-foreground text-sm mt-4">
          We offer a bug bounty program for qualifying vulnerabilities.
        </p>
      </section>
    </article>
  );
}

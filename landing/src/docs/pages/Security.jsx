export default function DocsSecurity() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-red-500/10 border border-red-500/30 text-red-500">
            SECURITY
          </span>
          <span>v2.0 — January 2026</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Security Whitepaper</h1>
        <p className="text-xl text-muted-foreground">
          A comprehensive overview of Sardis security architecture, threat models, and mitigation strategies
          across crypto, fiat, and card payment rails.
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
            { title: 'Unified Policy', desc: 'Same security rules apply to crypto, fiat, and card transactions' },
            { title: 'Compliance First', desc: 'Built-in KYC/AML for fiat operations via licensed providers' },
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
            { threat: 'Retry Loop Attack', severity: 'HIGH', mitigation: 'Transaction deduplication, rate limiting, daily limits across all rails' },
            { threat: 'Decimal Precision Error', severity: 'HIGH', mitigation: 'Strict amount validation, confirmation for large amounts' },
            { threat: 'Prompt Injection', severity: 'MEDIUM', mitigation: 'Policy engine validates all requests, not just prompts' },
            { threat: 'Merchant Impersonation', severity: 'MEDIUM', mitigation: 'Merchant allowlist, domain verification, AP2 mandate chain' },
            { threat: 'Unauthorized Off-Ramp', severity: 'HIGH', mitigation: 'KYC verification required, bank account ownership validation' },
            { threat: 'Session Hijacking', severity: 'LOW', mitigation: 'Short-lived tokens, request signing, IP binding' },
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
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│   ┌─────────┐     ┌─────────┐     ┌─────────┐             │
│   │ Share 1 │     │ Share 2 │     │ Share 3 │             │
│   │ (User)  │     │(Turnkey)│     │(Sardis) │             │
│   └────┬────┘     └────┬────┘     └────┬────┘             │
│        │               │               │                   │
│        └───────────────┼───────────────┘                   │
│                        │                                   │
│                  ┌─────▼─────┐                             │
│                  │  MPC Sign │                             │
│                  └─────┬─────┘                             │
│                        │                                   │
│                  ┌─────▼─────┐                             │
│                  │ Signature │                             │
│                  └───────────┘                             │
│                                                             │
│  No single party can sign without cooperation              │
└─────────────────────────────────────────────────────────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Fiat Rails Security
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Fiat operations introduce additional security considerations. Sardis implements multiple layers of protection:
        </p>

        <div className="not-prose space-y-4 mb-6">
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">KYC Verification</h4>
            <p className="text-sm text-muted-foreground mb-2">
              Off-ramp operations require KYC verification via Persona (680+ lines of integration code with
              webhook support). Identity is verified before any fiat can leave the system. KYC status is
              checked on every withdrawal request.
            </p>
            <div className="flex gap-2 mt-2">
              <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">PERSONA ✓</span>
              <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">BRIDGE ✓</span>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">AML/Sanctions Screening</h4>
            <p className="text-sm text-muted-foreground mb-2">
              Real-time AML screening via Elliptic (618 lines with HMAC-signed API). Wallet addresses and
              transactions are screened against OFAC, UN, and EU sanctions lists before execution.
            </p>
            <div className="flex gap-2 mt-2">
              <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">ELLIPTIC ✓</span>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Bank Account Ownership</h4>
            <p className="text-sm text-muted-foreground mb-2">
              Bank accounts must be verified as owned by the KYC'd entity before off-ramp. Micro-deposit
              verification or instant verification via Plaid ensures account ownership.
            </p>
          </div>

          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Transaction Limits</h4>
            <p className="text-sm text-muted-foreground mb-2">
              Fiat-specific limits apply in addition to general policy limits. Off-ramp has stricter
              default limits than on-ramp to prevent unauthorized withdrawals.
            </p>
            <div className="bg-muted/30 p-2 font-mono text-xs mt-2">
              Default: $500/tx on-ramp, $200/tx off-ramp, $1000/day total fiat
            </div>
          </div>

          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Provider Security</h4>
            <p className="text-sm text-muted-foreground">
              All fiat operations go through licensed, regulated providers (Onramper aggregates 30+ licensed
              providers, Bridge is a licensed money transmitter). Sardis never directly handles fiat.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Policy Engine Security
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The Policy Engine is the critical security component that validates every transaction across all payment rails.
        </p>

        <h3 className="text-lg font-bold font-display mb-3">Unified Validation</h3>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The same policy rules apply whether the transaction is crypto, fiat, or virtual card:
        </p>
        <div className="not-prose mb-6">
          <ul className="space-y-2">
            {[
              'Merchant allowlist/blocklist verification (applies to all rails)',
              'Transaction amount within defined limits (per-rail and total)',
              'Daily/weekly/monthly spend limits (aggregated across rails)',
              'Category restrictions enforcement (MCC codes for cards)',
              'Rate limiting per agent/wallet (unified across rails)',
              'Duplicate transaction detection (cross-rail deduplication)',
              'Risk score calculation and threshold',
              'Fiat-specific: KYC status verification',
              'Fiat-specific: Bank account ownership check',
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
          decision rationale, and cryptographic proof. Logs include fiat transfer references, bank account
          IDs (masked), and KYC verification status. Logs are immutable and stored for compliance purposes.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Unified Balance Security
          <span className="px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          The unified USDC/USD balance model (1:1 parity) introduces specific security considerations:
        </p>

        <div className="not-prose grid md:grid-cols-2 gap-4">
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">1:1 Parity Guarantee</h4>
            <p className="text-sm text-muted-foreground">
              USDC↔USD conversions are executed at exactly 1:1 via Bridge, a regulated provider.
              No slippage, no spread—like Coinbase Exchange treats USDC=USD.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Conversion Audit Trail</h4>
            <p className="text-sm text-muted-foreground">
              Every auto-conversion is logged with: trigger source (card payment, manual), amounts,
              provider transaction ID, and timestamps. Fully auditable.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Conversion Limits</h4>
            <p className="text-sm text-muted-foreground">
              Auto-conversion respects the same Policy Engine limits as direct payments.
              "Max $100/day" applies to card swipes that trigger USDC→USD conversion.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h4 className="font-bold font-display mb-2">Instant Settlement</h4>
            <p className="text-sm text-muted-foreground">
              Conversions happen instantly at card authorization time. No delayed settlement
              risk—the USD is available before the card transaction settles.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Compliance
        </h2>

        <div className="not-prose grid md:grid-cols-2 gap-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">KYC/AML</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Identity verification via Persona, AML screening via Elliptic. Required for fiat off-ramp.
              Optional for crypto-only wallets.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              INTEGRATED
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">SOC 2 Type II</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Enterprise security controls and audit procedures. Certification in progress.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-yellow-500/10 text-yellow-500 border border-yellow-500/30">
              IN PROGRESS
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">GDPR</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Data protection and privacy compliance for EU users. Right to deletion supported.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              COMPLIANT
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">PCI DSS</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Payment card industry data security standard via Lithic partnership.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              VIA PARTNER
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Money Transmission</h3>
            <p className="text-sm text-muted-foreground mb-2">
              Fiat operations via licensed money transmitters (Bridge, Onramper providers).
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              VIA PARTNER
            </span>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Sanctions Screening</h3>
            <p className="text-sm text-muted-foreground mb-2">
              OFAC and international sanctions list screening via Elliptic.
            </p>
            <span className="px-2 py-1 text-xs font-mono bg-emerald-500/10 text-emerald-500 border border-emerald-500/30">
              INTEGRATED
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
          We offer a bug bounty program for qualifying vulnerabilities. Rewards up to $10,000 for critical issues.
        </p>
      </section>
    </article>
  );
}

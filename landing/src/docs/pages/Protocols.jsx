import { Link } from 'react-router-dom';

export default function DocsProtocols() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            PROTOCOLS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Protocol Stack</h1>
        <p className="text-xl text-muted-foreground">
          Industry-standard protocols for secure agent payments.
        </p>
      </div>

      <section className="mb-12">
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`┌─────────────────────────────────────────────────────────────┐
│                     External Agents                          │
└─────────────────────────────────────────────────────────────┘
                    │   A2A     │    UCP    │   x402
                    ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Sardis Protocol Layer                       │
│      A2A (messages)  │  UCP (commerce)  │  x402 (micro)      │
│                         │                                    │
│                    ┌────┴────┐                               │
│                    │ AP2/TAP │  ← Verification               │
│                    └─────────┘                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│         Base | Polygon | Ethereum | Arbitrum | Optimism      │
└─────────────────────────────────────────────────────────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <div className="not-prose grid gap-4">
          <Link to="/docs/ap2" className="block p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">📋</span>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">AP2 (Agent Payment Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm">Google, PayPal, Mastercard, Visa consortium standard. Mandate chain verification.</p>
          </Link>

          <Link to="/docs/ucp" className="block p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🛒</span>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">UCP (Universal Commerce Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm">Standardized checkout flow. Cart management, sessions, fulfillment.</p>
          </Link>

          <Link to="/docs/a2a" className="block p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🤖</span>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">A2A (Agent-to-Agent)</h3>
            </div>
            <p className="text-muted-foreground text-sm">Google-developed multi-agent communication protocol.</p>
          </Link>

          <Link to="/docs/tap" className="block p-6 border border-border hover:border-[var(--sardis-orange)] transition-colors group">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🔐</span>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">TAP (Trust Anchor Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm">Cryptographic identity verification. Ed25519/ECDSA signatures.</p>
          </Link>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Supported Chains
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Chain</th>
                <th className="px-4 py-2 text-left border-b border-border">Tokens</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Base</td><td className="px-4 py-2 border-b border-border">USDC, EURC</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Polygon</td><td className="px-4 py-2 border-b border-border">USDC, USDT, EURC</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Ethereum</td><td className="px-4 py-2 border-b border-border">USDC, USDT, PYUSD, EURC</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Arbitrum</td><td className="px-4 py-2 border-b border-border">USDC, USDT</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Optimism</td><td className="px-4 py-2 border-b border-border">USDC, USDT</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

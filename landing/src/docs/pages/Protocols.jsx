import { Link } from 'react-router-dom';
import {
  Agreement02Icon,
  ShoppingBag01Icon,
  ConnectIcon,
  Key01Icon
} from 'hugeicons-react';

export default function DocsProtocols() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-10">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            PROTOCOLS
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Protocol Stack</h1>
        <p className="text-xl text-muted-foreground leading-relaxed">
          Industry-standard protocols for secure agent payments.
        </p>
      </div>

      <section className="mb-14">
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`┌─────────────────────────────────────────────────────────────┐
│                     External Agents                          │
└─────────────────────────────────────────────────────────────┘
                    │   A2A     │    UCP    │   x402
                    ▼           ▼           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Sardis Protocol Layer                       │
│  A2A (messages)│ UCP (commerce)│ x402 (micro) │ ACP (shops) │
│                         │                                    │
│                    ┌────┴────┐                               │
│                    │ AP2/TAP │  ← Verification               │
│                    └─────────┘                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│   Bank Transfer │ Virtual Cards │ Stablecoins (optional)     │
└─────────────────────────────────────────────────────────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-14">
        <div className="not-prose grid gap-5">
          <Link to="/docs/ap2" className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--sardis-orange)]/10 flex items-center justify-center">
                <Agreement02Icon size={22} color="var(--sardis-orange)" />
              </div>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">AP2 (Agent Payment Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">Google, PayPal, Mastercard, Visa consortium standard. Mandate chain verification.</p>
          </Link>

          <Link to="/docs/ucp" className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                <ShoppingBag01Icon size={22} className="text-emerald-500" />
              </div>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">UCP (Universal Commerce Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">Standardized checkout flow. Cart management, sessions, fulfillment.</p>
          </Link>

          <Link to="/docs/a2a" className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
                <ConnectIcon size={22} className="text-blue-500" />
              </div>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">A2A (Agent-to-Agent)</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">Google-developed multi-agent communication protocol.</p>
          </Link>

          <Link to="/docs/tap" className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
                <Key01Icon size={22} className="text-purple-500" />
              </div>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">TAP (Trust Anchor Protocol)</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">Cryptographic identity verification. Ed25519/ECDSA signatures.</p>
          </Link>

          <div className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
                <Agreement02Icon size={22} className="text-yellow-500" />
              </div>
              <h3 className="font-bold font-display text-lg group-hover:text-[var(--sardis-orange)]">x402 (HTTP Payments)</h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">HTTP-native micropayments via 402 status code. Coinbase-developed standard for pay-per-request APIs.</p>
          </div>

          <Link to="/docs/acp" className="block p-6 bg-card/50 rounded-lg shadow-sm hover:shadow-md hover:bg-card transition-all group">
            <div className="flex items-center gap-4 mb-3">
              <div className="w-10 h-10 rounded-lg bg-[var(--sardis-orange)]/10 flex items-center justify-center">
                <ShoppingBag01Icon size={22} color="var(--sardis-orange)" />
              </div>
              <h3 className="font-bold font-display text-lg">
                <span className="group-hover:text-[var(--sardis-orange)]">ACP (Agentic Commerce Protocol)</span>
                <span className="ml-2 px-2 py-0.5 text-xs font-mono bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
              </h3>
            </div>
            <p className="text-muted-foreground text-sm leading-relaxed pl-14">OpenAI's open standard for AI agent commerce. Product feeds, agentic checkout, delegated payments for ChatGPT-native purchasing.</p>
          </Link>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Stablecoin Networks (Optional Rail)
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Chain</th>
                <th className="px-4 py-2 text-left border-b border-border">Tokens</th>
                <th className="px-4 py-2 text-left border-b border-border">Status</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Base</td><td className="px-4 py-2 border-b border-border">USDC, EURC</td><td className="px-4 py-2 border-b border-border"><span className="text-emerald-500">✓ Deployed</span></td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Polygon</td><td className="px-4 py-2 border-b border-border">USDC, USDT, EURC</td><td className="px-4 py-2 border-b border-border"><span className="text-yellow-500">Ready</span></td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Ethereum</td><td className="px-4 py-2 border-b border-border">USDC, USDT, PYUSD, EURC</td><td className="px-4 py-2 border-b border-border"><span className="text-yellow-500">Ready</span></td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Arbitrum</td><td className="px-4 py-2 border-b border-border">USDC, USDT</td><td className="px-4 py-2 border-b border-border"><span className="text-yellow-500">Ready</span></td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">Optimism</td><td className="px-4 py-2 border-b border-border">USDC, USDT</td><td className="px-4 py-2 border-b border-border"><span className="text-yellow-500">Ready</span></td></tr>
            </tbody>
          </table>
        </div>
        <p className="text-sm text-muted-foreground mt-3">
          <span className="text-emerald-500">✓ Deployed</span> = Contracts live on testnet &nbsp;|&nbsp;
          <span className="text-yellow-500">Ready</span> = Chain integration complete, pending deployment
        </p>
      </section>
    </article>
  );
}

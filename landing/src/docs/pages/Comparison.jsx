import SEO, { createBreadcrumbSchema } from '@/components/SEO';

const comparisonData = [
  {
    feature: 'Non-custodial MPC wallets',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Natural language spending policies',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Per-transaction limits',
    sardis: true,
    creditCard: 'Limited',
    bankApi: 'Limited',
    custodialWallet: 'Limited',
  },
  {
    feature: 'Merchant category restrictions',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Time-based spending controls',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Cryptographic audit trail',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Multi-chain support',
    sardis: '5 chains',
    creditCard: 'N/A',
    bankApi: 'N/A',
    custodialWallet: 'Varies',
  },
  {
    feature: 'Virtual card issuance',
    sardis: true,
    creditCard: 'N/A',
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Fiat on/off-ramp',
    sardis: true,
    creditCard: 'N/A',
    bankApi: true,
    custodialWallet: 'Varies',
  },
  {
    feature: 'Protocol support (AP2/A2A/TAP)',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'MCP server for Claude',
    sardis: '52 tools',
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'Agent-to-agent payments',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
  {
    feature: 'KYC/AML compliance',
    sardis: true,
    creditCard: 'Issuer-dependent',
    bankApi: true,
    custodialWallet: 'Varies',
  },
  {
    feature: 'Gasless transactions (ERC-4337)',
    sardis: true,
    creditCard: 'N/A',
    bankApi: 'N/A',
    custodialWallet: false,
  },
  {
    feature: 'Policy Firewall (fail-closed)',
    sardis: true,
    creditCard: false,
    bankApi: false,
    custodialWallet: false,
  },
];

function CheckCell({ value }) {
  if (value === true) return <span className="text-emerald-500 font-bold">Yes</span>;
  if (value === false) return <span className="text-red-400">No</span>;
  return <span className="text-yellow-500 text-sm">{value}</span>;
}

export default function Comparison() {
  const schemas = [
    createBreadcrumbSchema([
      { name: 'Home', href: '/' },
      { name: 'Documentation', href: '/docs' },
      { name: 'Why Sardis', href: '/docs/comparison' },
    ]),
  ];

  return (
    <>
      <SEO
        title="Why Sardis - AI Agent Payment Comparison"
        description="Compare Sardis with alternatives for AI agent payments: credit cards, bank APIs, and custodial wallets. See why Sardis is the safest way to give AI agents access to money with non-custodial MPC wallets and natural language spending policies."
        path="/docs/comparison"
        schemas={schemas}
      />
      <article className="prose prose-invert max-w-none">
        <div className="not-prose mb-10">
          <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
            <span className="px-2 py-1 bg-[var(--sardis-orange)]/10 border border-[var(--sardis-orange)]/30 text-[var(--sardis-orange)]">
              COMPARISON
            </span>
          </div>
          <h1 className="text-4xl font-bold font-display mb-4">Why Sardis?</h1>
          <p className="text-xl text-muted-foreground leading-relaxed">
            The safest way to give AI agents access to money. See how Sardis compares to alternative approaches.
          </p>
        </div>

        {/* The Core Problem */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-4">The AI Agent Money Problem</h2>
          <p className="text-muted-foreground leading-relaxed mb-4">
            AI agents can reason, plan, and execute complex workflows. But giving them access to real money is dangerous without proper guardrails. Here's what happens with common approaches:
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="p-4 border border-red-500/30 bg-red-500/5">
              <h3 className="font-bold text-red-400 mb-2">Shared Credit Card</h3>
              <p className="text-sm text-muted-foreground">Agent has the card number and can spend without limits. No per-transaction controls, no merchant restrictions, no audit trail. One hallucination = unlimited spending.</p>
            </div>
            <div className="p-4 border border-red-500/30 bg-red-500/5">
              <h3 className="font-bold text-red-400 mb-2">Bank API Access</h3>
              <p className="text-sm text-muted-foreground">Direct bank API gives the agent ability to make transfers. Limited spending controls, no natural language policies, and bank APIs aren't designed for high-frequency agent transactions.</p>
            </div>
            <div className="p-4 border border-yellow-500/30 bg-yellow-500/5">
              <h3 className="font-bold text-yellow-400 mb-2">Custodial Crypto Wallet</h3>
              <p className="text-sm text-muted-foreground">A third party holds keys. Agent can transact but you trust the custodian. No built-in policy engine, limited audit trail, and custodian risk.</p>
            </div>
            <div className="p-4 border border-emerald-500/30 bg-emerald-500/5">
              <h3 className="font-bold text-emerald-400 mb-2">Sardis (Non-Custodial MPC)</h3>
              <p className="text-sm text-muted-foreground">Agent gets its own MPC wallet with policy-enforced spending limits. Natural language policies, merchant restrictions, time controls, cryptographic audit trail. Agent cannot bypass controls.</p>
            </div>
          </div>
        </section>

        {/* Feature Comparison Table */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">Feature Comparison</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Feature</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-[var(--sardis-orange)]">Sardis</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Credit Card</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Bank API</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Custodial Wallet</th>
                </tr>
              </thead>
              <tbody>
                {comparisonData.map((row, i) => (
                  <tr key={i} className="border-b border-border/50 hover:bg-card/50 transition-colors">
                    <td className="py-3 px-4 font-medium">{row.feature}</td>
                    <td className="py-3 px-4 text-center"><CheckCell value={row.sardis} /></td>
                    <td className="py-3 px-4 text-center"><CheckCell value={row.creditCard} /></td>
                    <td className="py-3 px-4 text-center"><CheckCell value={row.bankApi} /></td>
                    <td className="py-3 px-4 text-center"><CheckCell value={row.custodialWallet} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* How Sardis Works */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">How Sardis Works</h2>
          <div className="space-y-4">
            <div className="flex gap-4 items-start p-4 border border-border">
              <span className="flex-shrink-0 w-8 h-8 bg-[var(--sardis-orange)] text-white font-bold flex items-center justify-center font-mono">1</span>
              <div>
                <h3 className="font-bold mb-1">Create a Wallet</h3>
                <p className="text-sm text-muted-foreground">Each agent gets its own non-custodial MPC wallet. Private keys are split via Turnkey — Sardis never has access to funds.</p>
                <code className="text-xs text-[var(--sardis-orange)] mt-1 block">pip install sardis && sardis init</code>
              </div>
            </div>
            <div className="flex gap-4 items-start p-4 border border-border">
              <span className="flex-shrink-0 w-8 h-8 bg-[var(--sardis-orange)] text-white font-bold flex items-center justify-center font-mono">2</span>
              <div>
                <h3 className="font-bold mb-1">Define Spending Policies</h3>
                <p className="text-sm text-muted-foreground">Write rules in plain English. "Max $100/day on cloud services, only AWS and Vercel, business hours only." Sardis parses and enforces them.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start p-4 border border-border">
              <span className="flex-shrink-0 w-8 h-8 bg-[var(--sardis-orange)] text-white font-bold flex items-center justify-center font-mono">3</span>
              <div>
                <h3 className="font-bold mb-1">Agent Makes Payments</h3>
                <p className="text-sm text-muted-foreground">Every payment goes through the Policy Firewall. If it passes, the AP2 mandate chain is created and the transaction executes. If not, it's blocked.</p>
              </div>
            </div>
            <div className="flex gap-4 items-start p-4 border border-border">
              <span className="flex-shrink-0 w-8 h-8 bg-[var(--sardis-orange)] text-white font-bold flex items-center justify-center font-mono">4</span>
              <div>
                <h3 className="font-bold mb-1">Full Audit Trail</h3>
                <p className="text-sm text-muted-foreground">Every transaction, policy check, and mandate chain is recorded in an append-only ledger with Merkle tree anchoring for tamper-proof compliance.</p>
              </div>
            </div>
          </div>
        </section>

        {/* Supported Frameworks */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">Works With Your Stack</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Framework</th>
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Language</th>
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Integration</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Status</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Claude Desktop / Cursor', 'MCP', 'npx @sardis/mcp-server start', 'Stable'],
                  ['LangChain', 'Python / JS', 'pip install sardis', 'Stable'],
                  ['OpenAI Function Calling', 'Python', 'pip install sardis', 'Stable'],
                  ['Vercel AI SDK', 'TypeScript', 'npm install @sardis/ai-sdk', 'Stable'],
                  ['CrewAI', 'Python', 'pip install sardis', 'Beta'],
                  ['AutoGPT / AutoGen', 'Python', 'pip install sardis', 'Beta'],
                  ['LlamaIndex', 'Python', 'pip install sardis', 'Beta'],
                ].map(([name, lang, cmd, status], i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-3 px-4 font-medium">{name}</td>
                    <td className="py-3 px-4 text-muted-foreground">{lang}</td>
                    <td className="py-3 px-4"><code className="text-xs text-[var(--sardis-orange)]">{cmd}</code></td>
                    <td className="py-3 px-4 text-center">
                      <span className={`px-2 py-0.5 text-xs font-mono ${status === 'Stable' ? 'bg-emerald-500/10 border border-emerald-500/30 text-emerald-500' : 'bg-yellow-500/10 border border-yellow-500/30 text-yellow-500'}`}>
                        {status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* Supported Chains */}
        <section className="not-prose mb-12">
          <h2 className="text-2xl font-bold font-display mb-6">Multi-Chain Support</h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm border-collapse">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Chain</th>
                  <th className="text-left py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Tokens</th>
                  <th className="text-center py-3 px-4 font-mono text-xs uppercase tracking-wider text-muted-foreground">Gasless (ERC-4337)</th>
                </tr>
              </thead>
              <tbody>
                {[
                  ['Base', 'USDC, EURC', true],
                  ['Polygon', 'USDC, USDT, EURC', 'Coming soon'],
                  ['Ethereum', 'USDC, USDT, PYUSD, EURC', 'Coming soon'],
                  ['Arbitrum', 'USDC, USDT', 'Coming soon'],
                  ['Optimism', 'USDC, USDT', 'Coming soon'],
                ].map(([chain, tokens, gasless], i) => (
                  <tr key={i} className="border-b border-border/50">
                    <td className="py-3 px-4 font-medium">{chain}</td>
                    <td className="py-3 px-4 text-muted-foreground">{tokens}</td>
                    <td className="py-3 px-4 text-center"><CheckCell value={gasless} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        {/* CTA */}
        <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5 mt-12">
          <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Ready to get started?</h3>
          <p className="text-muted-foreground text-sm mb-4">
            Give your AI agents safe access to money in 5 minutes.
          </p>
          <div className="flex gap-4">
            <a
              href="/docs/quickstart"
              className="px-4 py-2 bg-[var(--sardis-orange)] text-white font-medium text-sm hover:bg-[var(--sardis-orange)]/90 transition-colors"
            >
              Quick Start Guide
            </a>
            <a
              href="/playground"
              className="px-4 py-2 border border-border text-foreground font-medium text-sm hover:border-[var(--sardis-orange)] transition-colors"
            >
              Try the Playground
            </a>
          </div>
        </section>
      </article>
    </>
  );
}

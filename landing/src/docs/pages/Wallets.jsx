import SEO, { createBreadcrumbSchema } from '@/components/SEO';

export default function DocsWallets() {
  return (
    <>
      <SEO
        title="AI Agent Wallets - MPC Wallet Guide"
        description="Create non-custodial MPC wallets for AI agents using Sardis. Private keys are never stored — signing happens across distributed nodes via Turnkey. Supports Base, Polygon, Ethereum, Arbitrum, and Optimism."
        path="/docs/wallets"
        schemas={[
          createBreadcrumbSchema([
            { name: 'Home', href: '/' },
            { name: 'Documentation', href: '/docs' },
            { name: 'Wallets' },
          ]),
        ]}
      />
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Wallets</h1>
        <p className="text-xl text-muted-foreground">Non-custodial MPC wallets for AI agents.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Overview
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis wallets use MPC (Multi-Party Computation) via Turnkey. Private keys are never stored - signing happens across distributed nodes.
        </p>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Non-custodial - You control the wallet</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">MPC signing - No single point of failure</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Policy enforcement - Spending limits built-in</span>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Create wallet
    wallet = await client.wallets.create(
        agent_id="my-agent",
        chain="base",
        metadata={"team": "engineering"},
    )
    print(f"Wallet: {wallet.id}")
    print(f"Address: {wallet.address}")

    # Get balance
    balance = await client.wallets.get_balance(wallet.id)
    print(f"Balance: {balance.available_minor / 1_000_000} USDC")

    # Fund wallet (testnet only)
    await client.wallets.fund(wallet.id, amount_minor=100_000_000)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> TypeScript
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'sk_...' });

// Create wallet
const wallet = await client.wallets.create({
  agentId: 'my-agent',
  chain: 'base',
  metadata: { team: 'engineering' },
});

// Get balance
const balance = await client.wallets.getBalance(wallet.id);
console.log('Balance:', balance.availableMinor / 1_000_000, 'USDC');

// List wallets
const wallets = await client.wallets.list({ agentId: 'my-agent' });`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MCP Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create a new wallet</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_wallets</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List all wallets</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_balance</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get wallet balance</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_fund_wallet</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Fund wallet (testnet)</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
    </>
  );
}

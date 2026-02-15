export default function DocsQuickstart() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">
            GETTING STARTED
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Quick Start</h1>
        <p className="text-xl text-muted-foreground">
          Get Sardis running in under 5 minutes.
        </p>
      </div>

      <section className="not-prose mb-8 p-4 border border-emerald-500/30 bg-emerald-500/10">
        <div className="flex items-center gap-2 mb-2">
          <span className="w-2 h-2 bg-emerald-500 rounded-full animate-pulse"></span>
          <span className="font-bold text-emerald-500">LIVE ON BASE SEPOLIA</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Smart contracts deployed and verified. Ready for testnet integration.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> USD-First Treasury Flow (Design Partner Lane)
        </h2>
        <p className="text-muted-foreground mb-4">
          Launch default is fiat-first treasury. Card spend is backed by prefunded USD accounts.
          Stablecoin conversion is optional and quote-based.
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# 1) Sync financial accounts
POST /api/v2/treasury/account-holders/sync

# 2) Link bank account (MICRO_DEPOSIT flow)
POST /api/v2/treasury/external-bank-accounts
POST /api/v2/treasury/external-bank-accounts/{token}/verify-micro-deposits

# 3) Fund treasury (ACH collection)
POST /api/v2/treasury/fund

# 4) Observe payment + balances
GET /api/v2/treasury/payments/{payment_token}
GET /api/v2/treasury/balances`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Zero Integration (MCP)
        </h2>
        <p className="text-muted-foreground mb-4">
          The fastest way to start using Sardis with Claude Desktop or Cursor.
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npx @sardis/mcp-server init --mode simulated</div>
            <div className="text-[var(--sardis-canvas)]/70">$ npx @sardis/mcp-server start</div>
          </div>
        </div>

        <p className="text-muted-foreground mt-4 mb-4">
          `init` creates a local <code className="px-1 py-0.5 bg-muted font-mono text-sm">.env.sardis</code> template.
          Then add to your <code className="px-1 py-0.5 bg-muted font-mono text-sm">claude_desktop_config.json</code>:
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`{
  "mcpServers": {
    "sardis": {
      "command": "npx",
      "args": ["@sardis/mcp-server", "start"]
    }
  }
}`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Product Demo Route
        </h2>
        <p className="text-muted-foreground mb-4">
          Use <code className="px-1 py-0.5 bg-muted font-mono text-sm">/demo</code> for pitch and design-partner walkthroughs.
        </p>

        <div className="not-prose grid md:grid-cols-2 gap-4 mb-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Simulated (Public)</h3>
            <p className="text-sm text-muted-foreground">
              No secrets required. Safe for public links and first-touch demos.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold font-display mb-2">Live (Private)</h3>
            <p className="text-sm text-muted-foreground">
              Requires server env vars and operator password gate. Never expose keys client-side.
            </p>
          </div>
        </div>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Landing (server-side env)
SARDIS_API_URL=https://api-staging.sardis.sh
SARDIS_API_KEY=sk_live_...
DEMO_OPERATOR_PASSWORD=<shared-password>

# Optional for richer live flow
DEMO_LIVE_AGENT_ID=agent_demo_01
DEMO_LIVE_CARD_ID=vc_demo_01`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mt-4 text-sm">
          Private runbook: <code className="px-1 py-0.5 bg-muted font-mono text-sm">docs/release/investor-demo-operator-kit.md</code>
        </p>
        <p className="text-muted-foreground mt-2 text-sm">
          Note: local <code className="px-1 py-0.5 bg-muted font-mono text-sm">vite dev</code> is enough for simulated mode.
          For private live mode, run via Vercel runtime so
          {' '}
          <code className="px-1 py-0.5 bg-muted font-mono text-sm">/api/demo-auth</code>
          {' '}
          and
          {' '}
          <code className="px-1 py-0.5 bg-muted font-mono text-sm">/api/demo-proxy</code>
          {' '}
          are available.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Local Engineering Readiness (Repo)
        </h2>
        <p className="text-muted-foreground mb-4">
          If you are running Sardis from source, use these preflight checks before release or design-partner onboarding.
        </p>

        <div className="not-prose space-y-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ pnpm run bootstrap:js</div>
            <div className="text-[var(--sardis-canvas)]/70">$ pnpm run check:release-readiness</div>
            <div className="text-[var(--sardis-canvas)]/70">$ pnpm run check:live-chain   # optional (requires Turnkey/testnet creds)</div>
          </div>
          <p className="text-xs text-muted-foreground">
            If your environment blocks npm registry DNS/network, JS package checks are skipped in degraded mode and enforced in CI/strict mode.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Installation</h3>
        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ pip install sardis</div>
            <div className="text-[var(--sardis-canvas)]/50 mt-1"># or install individual packages: sardis-core, sardis-protocol, sardis-chain</div>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Basic Usage</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

client = SardisClient(api_key="your_api_key")

wallet = client.wallets.create(
    name="research-agent",
    chain="base",
    token="USDC",
    policy="Max $100/day, Max $25 per tx"
)

result = wallet.pay(
    to="openai.com",
    amount="20.00",
    purpose="GPT-4 API credits"
)

print(result.success)
print(result.tx_id)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> TypeScript SDK
        </h2>

        <h3 className="text-lg font-bold font-display mb-3">Installation</h3>
        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ npm install @sardis/sdk</div>
          </div>
        </div>

        <h3 className="text-lg font-bold font-display mb-3">Basic Usage</h3>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`import { SardisClient } from '@sardis/sdk';

const client = new SardisClient({ apiKey: 'your_api_key' });

const result = await client.payments.executeMandate({
  psp_domain: 'api.openai.com',
  amount: '20.00',
  token: 'USDC',
  chain: 'base',
  purpose: 'GPT-4 API credits'
});

console.log('Payment ID:', result.payment_id);
console.log('Status:', result.status);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Run the Demo
        </h2>

        <div className="not-prose mb-4">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <div className="text-[var(--sardis-orange)]">$ python examples/simple_payment.py</div>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">Expected output:</p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm">
            <pre className="text-[var(--sardis-canvas)]">{`1. Creating wallet with $50 USDC...
2. Executing payment of $2 to OpenAI API...
3. Checking wallet balance...
✓ Demo completed successfully!`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Testnet Configuration
        </h2>
        <p className="text-muted-foreground mb-4">
          Configure your environment to use deployed contracts on Base Sepolia:
        </p>

        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Deployed Contract Addresses (Base Sepolia)
SARDIS_WALLET_FACTORY=0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7
SARDIS_ESCROW=0x5cf752B512FE6066a8fc2E6ce555c0C755aB5932

# API Configuration
SARDIS_API_URL=https://api.sardis.sh
SARDIS_API_KEY=sk_test_...

# Network Configuration
SARDIS_CHAIN=base_sepolia
SARDIS_RPC_URL=https://sepolia.base.org`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mt-4 text-sm">
          View contracts on{' '}
          <a
            href="https://sepolia.basescan.org/address/0x0922f46cbDA32D93691FE8a8bD7271D24E53B3D7"
            target="_blank"
            rel="noopener noreferrer"
            className="text-[var(--sardis-orange)] hover:underline"
          >
            BaseScan →
          </a>
        </p>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Next Steps</h3>
        <ul className="space-y-2 text-muted-foreground text-sm">
          <li>→ Learn about the <a href="/docs/architecture" className="text-[var(--sardis-orange)] hover:underline">Architecture</a></li>
          <li>→ Explore the <a href="/docs/sdk" className="text-[var(--sardis-orange)] hover:underline">SDK Reference</a></li>
          <li>→ View <a href="/docs/deployment" className="text-[var(--sardis-orange)] hover:underline">Deployment Guide</a></li>
          <li>→ Read the <a href="/docs/whitepaper" className="text-[var(--sardis-orange)] hover:underline">Whitepaper</a></li>
        </ul>
      </section>
    </article>
  );
}

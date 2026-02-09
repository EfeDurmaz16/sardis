export default function DocsPayments() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Payments</h1>
        <p className="text-xl text-muted-foreground">Execute payments via bank transfer, virtual card, or stablecoins — all governed by policy.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Payment Flow
        </h2>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Payment Request
      │
      ▼
┌─────────────────┐
│ Policy Check    │ ← Spending limits, vendor rules
└─────────────────┘
      │ ✓
      ▼
┌─────────────────┐
│ Compliance      │ ← Sanctions screening
└─────────────────┘
      │ ✓
      ▼
┌─────────────────┐
│ Chain Execution │ ← MPC signing, on-chain transfer
└─────────────────┘
      │
      ▼
Transaction Hash`}</pre>
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
    # Execute payment
    result = await client.payments.execute({
        "wallet_id": "wallet_abc123",
        "destination": "0x...",
        "amount_minor": 10_000_000,  # $10.00
        "token": "USDC",
        "chain": "base",
        "purpose": "API subscription",
    })

    print(f"Transaction: {result.tx_hash}")
    print(f"Status: {result.status}")

    # Get transaction details
    tx = await client.transactions.get(result.tx_id)
    print(f"Confirmed: {tx.confirmed_at}")`}</pre>
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

const result = await client.payments.execute({
  walletId: 'wallet_abc123',
  destination: '0x...',
  amountMinor: 10_000_000,
  token: 'USDC',
  chain: 'base',
  purpose: 'API subscription',
});

console.log('Transaction:', result.txHash);

// List transactions
const txs = await client.transactions.list({
  walletId: 'wallet_abc123',
  limit: 10,
});`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Supported Tokens
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border">Token</th>
                <th className="px-4 py-2 text-left border-b border-border">Chains</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">USDC</td><td className="px-4 py-2 border-b border-border text-muted-foreground">All chains</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">USDT</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Polygon, Ethereum, Arbitrum, Optimism</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">EURC</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Base, Polygon, Ethereum</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">PYUSD</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Ethereum</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MCP Tools
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_pay</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Execute a payment</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_check_policy</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Validate against policy</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_transaction</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get transaction details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_transactions</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List wallet transactions</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

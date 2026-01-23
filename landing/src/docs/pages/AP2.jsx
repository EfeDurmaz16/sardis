export default function DocsAP2() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">PROTOCOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">AP2 Protocol</h1>
        <p className="text-xl text-muted-foreground">Agent Payment Protocol - Industry standard for secure agent payments.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Mandate Chain
        </h2>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`IntentMandate ───▶ CartMandate ───▶ PaymentMandate
   (User)           (Merchant)         (Signed)
      │                  │                 │
      │ "I want to buy"  │ "Here's cart"   │ "Approved"
      ▼                  ▼                 ▼
                  Sardis Verifier
            • Chain integrity check
            • Signature validation
            • Policy enforcement`}</pre>
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
    # Create intent mandate
    intent = await client.mandates.create_intent(
        agent_id="shopping-agent",
        max_amount_minor=50_000_000,
        allowed_categories=["saas"],
    )

    # Execute payment from cart
    result = await client.payments.execute_mandate(cart.id)
    print(f"Transaction: {result.tx_hash}")`}</pre>
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

const intent = await client.mandates.createIntent({
  agentId: 'shopping-agent',
  maxAmountMinor: 50_000_000,
  allowedCategories: ['saas'],
});

const result = await client.payments.executeMandate(cart.id);
console.log('Transaction:', result.txHash);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Verification
        </h2>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Chain integrity - Each mandate references its parent</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Signature validation - All mandates cryptographically signed</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Amount bounds - Cart total ≤ intent max amount</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">✓</span>
            <span className="text-muted-foreground">Replay protection - Mandate not previously executed</span>
          </div>
        </div>
      </section>
    </article>
  );
}

import { Link } from 'react-router-dom';

export default function DocsACP() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">PROTOCOLS</span>
          <span className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 text-emerald-500">NEW</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">ACP Protocol</h1>
        <p className="text-xl text-muted-foreground">Agentic Commerce Protocol - OpenAI's open standard for AI agent commerce.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Overview
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          ACP (Agentic Commerce Protocol) is an open standard developed by OpenAI in partnership with Stripe.
          It defines how AI agents discover products, initiate checkout sessions, and complete purchases
          using delegated payment credentials — without ever handling raw card numbers or bank details.
        </p>
        <p className="text-muted-foreground leading-relaxed">
          Sardis implements ACP as a first-class protocol alongside{' '}
          <Link to="/docs/ap2" className="text-[var(--sardis-orange)]">AP2</Link>,{' '}
          <Link to="/docs/ucp" className="text-[var(--sardis-orange)]">UCP</Link>, and{' '}
          <Link to="/docs/a2a" className="text-[var(--sardis-orange)]">A2A</Link>, enabling agents
          to purchase from any ACP-compatible merchant through Sardis-managed wallets.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Checkout Flow
        </h2>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Agent                    Merchant (ACP)              Sardis
  │                          │                          │
  │  1. GET /acp/manifest    │                          │
  │ ─────────────────────▶   │                          │
  │  ◀─ product_feed[]       │                          │
  │                          │                          │
  │  2. POST /acp/checkout   │                          │
  │ ─────────────────────▶   │                          │
  │  ◀─ { session_id, url }  │                          │
  │                          │                          │
  │  3. Authorize payment    │                          │
  │ ─────────────────────────────────────────────────▶  │
  │                          │    ◀─ shared_token       │
  │                          │                          │
  │  4. POST /acp/pay        │                          │
  │ ─────────────────────▶   │                          │
  │  { session_id, token }   │  5. Stripe charge ──▶    │
  │                          │                          │
  │  ◀─ { order_id, status } │                          │
  │                          │                          │
  │  6. Webhook: fulfilled   │                          │
  │  ◀──────────────────────                            │`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> REST Endpoints
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border font-mono">Method</th>
                <th className="px-4 py-2 text-left border-b border-border font-mono">Endpoint</th>
                <th className="px-4 py-2 text-left border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-emerald-500">GET</td><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">/acp/manifest</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Product feed discovery</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-yellow-500">POST</td><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">/acp/checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create checkout session</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-yellow-500">POST</td><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">/acp/pay</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Submit payment with shared token</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-emerald-500">GET</td><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">/acp/orders/:id</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Order status & fulfillment</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-yellow-500">POST</td><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">/acp/webhooks</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Fulfillment & refund events</td></tr>
            </tbody>
          </table>
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
    # Discover products from ACP-compatible merchant
    manifest = await client.acp.get_manifest(
        merchant_url="https://shop.example.com/acp/manifest"
    )

    # Create checkout session
    session = await client.acp.create_checkout(
        merchant_url="https://shop.example.com",
        items=[{"product_id": "prod_abc", "quantity": 1}],
    )

    # Sardis creates a delegated payment token
    token = await client.acp.authorize_payment(
        agent_id="shopping-agent",
        session_id=session.id,
        max_amount_minor=5000,  # $50.00 cap
    )

    # Complete purchase
    order = await client.acp.pay(
        session_id=session.id,
        payment_token=token.shared_token,
    )
    print(f"Order: {order.order_id} — {order.status}")`}</pre>
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

// Discover products
const manifest = await client.acp.getManifest({
  merchantUrl: 'https://shop.example.com/acp/manifest',
});

// Create checkout session
const session = await client.acp.createCheckout({
  merchantUrl: 'https://shop.example.com',
  items: [{ productId: 'prod_abc', quantity: 1 }],
});

// Authorize with Sardis policy engine
const token = await client.acp.authorizePayment({
  agentId: 'shopping-agent',
  sessionId: session.id,
  maxAmountMinor: 5000,
});

// Complete purchase
const order = await client.acp.pay({
  sessionId: session.id,
  paymentToken: token.sharedToken,
});
console.log('Order:', order.orderId, order.status);`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Delegated Payments
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          ACP uses <strong className="text-foreground">Stripe Shared Payment Tokens</strong> for delegated payments.
          Instead of sharing card numbers, Sardis generates a one-time token scoped to a specific checkout session and amount.
          The merchant charges the token through Stripe — the agent never sees raw payment credentials.
        </p>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">&#10003;</span>
            <span className="text-muted-foreground">Token scoped to session — cannot be reused for other purchases</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">&#10003;</span>
            <span className="text-muted-foreground">Amount-capped — token cannot exceed the authorized limit</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">&#10003;</span>
            <span className="text-muted-foreground">Policy-gated — Sardis spending policies enforced before token issuance</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="text-emerald-500">&#10003;</span>
            <span className="text-muted-foreground">Audit trail — every token issuance logged in Sardis ledger</span>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Webhook Events
        </h2>
        <div className="not-prose">
          <table className="w-full border border-border text-sm">
            <thead>
              <tr className="bg-muted/30">
                <th className="px-4 py-2 text-left border-b border-border font-mono">Event</th>
                <th className="px-4 py-2 text-left border-b border-border">Description</th>
              </tr>
            </thead>
            <tbody>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">checkout.completed</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Payment confirmed, order created</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">order.fulfilled</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Merchant fulfilled the order</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">order.refunded</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Full or partial refund issued</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">payment.failed</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Payment declined or token expired</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Sardis + ACP
        </h2>
        <p className="text-muted-foreground leading-relaxed mb-4">
          Sardis acts as the agent's payment backend for ACP flows. When an agent wants to buy
          from an ACP merchant, Sardis handles the entire payment authorization:
        </p>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`┌─────────────┐     ┌───────────┐     ┌──────────────┐
│  AI Agent   │────▶│  Sardis   │────▶│ ACP Merchant │
└─────────────┘     └───────────┘     └──────────────┘
                         │
                    ┌────┴────┐
                    │ Policy  │  ← Check spending limits
                    │ Engine  │  ← Verify merchant category
                    └────┬────┘
                         │
                    ┌────┴────┐
                    │ Stripe  │  ← Issue shared payment token
                    │ Token   │  ← Scoped to session + amount
                    └─────────┘`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-border bg-muted/30">
        <h3 className="font-bold font-display mb-2">Related Protocols</h3>
        <div className="flex flex-wrap gap-3">
          <Link to="/docs/ap2" className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">AP2 (Payment)</Link>
          <Link to="/docs/ucp" className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">UCP (Commerce)</Link>
          <Link to="/docs/a2a" className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">A2A (Agent-to-Agent)</Link>
          <Link to="/docs/tap" className="px-4 py-2 border border-border hover:border-[var(--sardis-orange)] text-sm font-mono transition-colors">TAP (Trust Anchor)</Link>
        </div>
      </section>
    </article>
  );
}

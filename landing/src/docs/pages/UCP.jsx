export default function DocsUCP() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">PROTOCOLS</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">UCP Protocol</h1>
        <p className="text-xl text-muted-foreground">Universal Commerce Protocol - Standardized checkout for AI agents.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Checkout Flow
        </h2>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`1. Create Checkout    2. Update Cart     3. Complete
┌────────────────┐   ┌────────────────┐  ┌────────────────┐
│ Session + Items│──▶│ + Discount     │─▶│ Payment + Order│
└────────────────┘   └────────────────┘  └────────────────┘

4. Track Fulfillment
┌─────────────────────────────────────────────────────────┐
│ Shipping → In Transit → Delivered                        │
└─────────────────────────────────────────────────────────┘`}</pre>
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
    # Create checkout
    session = await client.ucp.create_checkout(
        merchant_id="merchant_456",
        line_items=[
            {"name": "Widget", "quantity": 2, "unit_price_minor": 1500}
        ],
    )

    # Apply discount
    await client.ucp.apply_discount(session.id, code="SAVE10")

    # Complete
    result = await client.ucp.complete_checkout(
        session_id=session.id,
        chain="base",
        token="USDC",
    )
    print(f"Order: {result.order_id}")`}</pre>
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Start session</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_update_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Modify items</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_complete_checkout</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Complete & pay</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_apply_discount</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Apply discount</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_track_fulfillment</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Track shipment</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

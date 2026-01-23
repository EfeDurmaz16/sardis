export default function DocsHolds() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Holds</h1>
        <p className="text-xl text-muted-foreground">Pre-authorization holds for reservations and delayed capture.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Hold Lifecycle
        </h2>
        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-6 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`Create Hold ─────▶ Capture ─────▶ Payment Executed
     │
     │
     └────────────▶ Release ─────▶ Funds Returned
                   (or Expire)`}</pre>
          </div>
        </div>
        <p className="text-muted-foreground">
          Holds reserve funds without executing a payment. Use cases include hotel reservations, rental deposits, and two-phase payments.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Python
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Create hold
    hold = await client.holds.create(
        wallet_id="wallet_abc123",
        amount_minor=50_000_000,  # $50.00
        token="USDC",
        purpose="Hotel reservation",
        expires_in_hours=72,
    )
    print(f"Hold: {hold.id}")

    # Later: capture the hold
    captured = await client.holds.capture(hold.id)
    print(f"Captured: {captured.tx_hash}")

    # Or: release the hold
    released = await client.holds.release(hold.id)
    print(f"Released: {released.released_at}")`}</pre>
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

// Create hold
const hold = await client.holds.create({
  walletId: 'wallet_abc123',
  amountMinor: 50_000_000,
  token: 'USDC',
  purpose: 'Hotel reservation',
});

// Capture
const captured = await client.holds.capture(hold.id);

// Or release
const released = await client.holds.release(hold.id);

// List holds
const holds = await client.holds.list({ walletId: 'wallet_abc123' });`}</pre>
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
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_create_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Create a fund hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_capture_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Capture a hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_release_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Release/void a hold</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_get_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Get hold details</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_list_holds</td><td className="px-4 py-2 border-b border-border text-muted-foreground">List wallet holds</td></tr>
              <tr><td className="px-4 py-2 border-b border-border font-mono text-[var(--sardis-orange)]">sardis_extend_hold</td><td className="px-4 py-2 border-b border-border text-muted-foreground">Extend hold expiration</td></tr>
            </tbody>
          </table>
        </div>
      </section>
    </article>
  );
}

export default function DocsPolicies() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Spending Policies</h1>
        <p className="text-xl text-muted-foreground">Natural language spending limits for AI agents.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Policy Types
        </h2>
        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Amount Limits</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`max_per_transaction: $50
max_daily: $500
max_weekly: $2,000`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Vendor Restrictions</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`allowed_vendors: ["openai", "anthropic", "aws"]
blocked_vendors: ["amazon", "ebay"]`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Category Rules</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`allowed_categories: ["saas", "cloud_compute"]
blocked_categories: ["gambling", "adult"]`}</pre>
            </div>
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
    # Create policy
    policy = await client.policies.create(
        wallet_id="wallet_abc123",
        rules={
            "max_per_transaction": 100_000_000,  # $100
            "max_daily": 1000_000_000,           # $1,000
            "allowed_vendors": ["openai", "anthropic"],
            "blocked_categories": ["gambling"],
        },
    )

    # Validate a transaction
    result = await client.policies.validate(
        wallet_id="wallet_abc123",
        transaction={
            "amount_minor": 50_000_000,
            "vendor": "openai",
        },
    )
    print(f"Allowed: {result.allowed}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Natural Language
        </h2>
        <p className="text-muted-foreground mb-4">
          Create policies using natural language descriptions:
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create_from_natural_language(
    wallet_id="wallet_abc123",
    description="""
    Allow spending up to $50 per transaction and $500 per day.
    Only allow purchases from OpenAI, Anthropic, and AWS.
    Block any gambling or adult content.
    Only allow transactions during business hours (9 AM - 6 PM EST).
    """,
)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Evaluation Order
        </h2>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">1</span>
            <span className="text-muted-foreground">Blocked vendors/categories - Immediate rejection</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">2</span>
            <span className="text-muted-foreground">Allowed vendors/categories - Must match if specified</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">3</span>
            <span className="text-muted-foreground">Amount limits - Check transaction and aggregate limits</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">4</span>
            <span className="text-muted-foreground">Time-based rules - Check allowed hours/days</span>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Best Practices</h3>
        <ul className="space-y-1 text-muted-foreground text-sm">
          <li>1. Start restrictive - Begin with low limits</li>
          <li>2. Use allowlists - Prefer allowlists over blocklists</li>
          <li>3. Monitor violations - Review blocked transactions</li>
          <li>4. Separate policies - Different wallets for different risk profiles</li>
        </ul>
      </section>
    </article>
  );
}

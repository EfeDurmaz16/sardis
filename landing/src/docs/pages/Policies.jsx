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

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Multi-Level Limit Strategy
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis supports per-transaction, daily, weekly, and monthly limits. Use multiple levels together
          for defense-in-depth.
        </p>
        <div className="not-prose overflow-x-auto mb-4">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Limit Type</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Use Case</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Example</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b border-border">
                <td className="p-3 font-mono">max_per_transaction</td>
                <td className="p-3">Cap single purchases</td>
                <td className="p-3">$50 - prevents large accidental charges</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">max_daily</td>
                <td className="p-3">Daily budget envelope</td>
                <td className="p-3">$500 - limits total daily exposure</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">max_weekly</td>
                <td className="p-3">Weekly spending cap</td>
                <td className="p-3">$2,000 - smooths burst spending</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono">max_monthly</td>
                <td className="p-3">Monthly budget enforcement</td>
                <td className="p-3">$5,000 - hard monthly ceiling</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Per-Merchant Overrides
        </h2>
        <p className="text-muted-foreground mb-4">
          Override global limits for specific merchants using <code>merchant_rules</code>:
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        # Global defaults
        "max_per_transaction": 50_000_000,   # $50/tx globally
        "max_daily": 1000_000_000,           # $1,000/day total

        # Per-merchant overrides
        "merchant_rules": [
            {
                "merchant": "openai",
                "max_per_transaction": 200_000_000,  # $200/tx for OpenAI
                "daily_limit": 500_000_000,          # $500/day for OpenAI
            },
            {
                "merchant": "anthropic",
                "max_per_transaction": 200_000_000,  # $200/tx for Anthropic
            },
            {
                "merchant": "aws",
                "max_per_transaction": 500_000_000,  # $500/tx for AWS
                "daily_limit": 1000_000_000,         # $1,000/day for AWS
            },
        ],
    },
)`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Recommended Combinations
        </h2>
        <div className="not-prose overflow-x-auto mb-4">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Profile</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Per-Tx</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Daily</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Weekly</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Monthly</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">Conservative</td>
                <td className="p-3">$25</td>
                <td className="p-3">$100</td>
                <td className="p-3">$500</td>
                <td className="p-3">$1,000</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-yellow-400">Standard</td>
                <td className="p-3">$100</td>
                <td className="p-3">$500</td>
                <td className="p-3">$2,000</td>
                <td className="p-3">$5,000</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-[var(--sardis-orange)]">Enterprise</td>
                <td className="p-3">$500</td>
                <td className="p-3">$5,000</td>
                <td className="p-3">$20,000</td>
                <td className="p-3">$50,000</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div className="not-prose p-4 border border-yellow-500/30 bg-yellow-500/5">
          <p className="text-sm text-muted-foreground">
            <strong className="text-yellow-500">Edge Case:</strong> If <code>max_per_transaction</code> exceeds <code>max_daily</code>,
            the daily limit acts as the effective cap. For example, a $200/tx policy with $100/day means the agent
            can never actually spend $200 in a single transaction because the daily limit would be exceeded.
            Sardis validates this and warns during policy creation.
          </p>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Best Practices</h3>
        <ul className="space-y-1 text-muted-foreground text-sm">
          <li>1. Start restrictive - Begin with low limits and increase as trust builds</li>
          <li>2. Use allowlists - Prefer allowlists over blocklists for vendors and categories</li>
          <li>3. Layer limits - Combine per-tx, daily, and monthly limits for defense-in-depth</li>
          <li>4. Monitor violations - Review blocked transactions to tune your policies</li>
          <li>5. Separate policies - Use different wallets for different risk profiles</li>
          <li>6. Override for trusted merchants - Set higher per-tx limits for known vendors like OpenAI</li>
          <li>7. Add time restrictions - Pair amount limits with <a href="/docs/time-based-policies" className="text-[var(--sardis-orange)] underline">time-based policies</a> for maximum safety</li>
        </ul>
      </section>
    </article>
  );
}

export default function DocsTimeBasedPolicies() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
          <span className="px-2 py-1 bg-green-500/10 border border-green-500/30 text-green-500">STABLE</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Time-Based Policies</h1>
        <p className="text-xl text-muted-foreground">Restrict agent transactions to specific hours, days, and timezones.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Overview
        </h2>
        <p className="text-muted-foreground mb-4">
          Time-based policies let you control <em>when</em> an AI agent can spend money. Combined with amount limits
          and merchant restrictions, time windows provide an additional layer of safety by ensuring transactions only
          occur during supervised periods.
        </p>
        <div className="not-prose p-4 border border-border bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
          <p className="text-sm text-muted-foreground">
            <strong className="text-[var(--sardis-orange)]">Default:</strong> If no time policy is set, transactions are allowed 24/7 UTC.
            All time comparisons use UTC internally. Timezone offsets are applied before evaluation.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Timezone Handling
        </h2>
        <p className="text-muted-foreground mb-4">
          All policy times are stored and evaluated in UTC. When you specify a timezone (e.g., <code>America/New_York</code>),
          Sardis converts the current time to your timezone before checking the policy window.
        </p>
        <div className="not-prose space-y-3">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Supported Timezone Formats</h3>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`# IANA timezone names (recommended)
timezone: "America/New_York"      # EST/EDT auto-handled
timezone: "Europe/London"         # GMT/BST auto-handled
timezone: "Asia/Tokyo"            # JST (no DST)

# UTC offset (fixed, no DST adjustment)
timezone: "UTC"
timezone: "UTC-5"
timezone: "UTC+9"`}</pre>
            </div>
          </div>
          <div className="not-prose p-4 border border-yellow-500/30 bg-yellow-500/5">
            <p className="text-sm text-muted-foreground">
              <strong className="text-yellow-500">DST Handling:</strong> When using IANA timezone names
              (e.g., <code>America/New_York</code>), Sardis automatically adjusts for Daylight Saving Time.
              A policy set to "9 AM - 5 PM EST" will correctly evaluate as "9 AM - 5 PM EDT" during summer months.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Configuration Examples
        </h2>
        <div className="not-prose space-y-4">

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-1">1. Business Hours Only (Weekdays 9 AM - 5 PM EST)</h3>
            <p className="text-sm text-muted-foreground mb-3">Most common pattern. Restrict spending to when your team is available to monitor.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "time_policy": {
            "timezone": "America/New_York",
            "allowed_hours": {"start": 9, "end": 17},
            "allowed_days": ["mon", "tue", "wed", "thu", "fri"],
        },
        "max_per_transaction": 100_000_000,  # $100
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-1">2. Block Weekends</h3>
            <p className="text-sm text-muted-foreground mb-3">Allow transactions any time on weekdays, block all weekend activity.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "time_policy": {
            "timezone": "UTC",
            "allowed_days": ["mon", "tue", "wed", "thu", "fri"],
            # No allowed_hours = all hours on allowed days
        },
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-1">3. Daytime Only (6 AM - 10 PM UTC)</h3>
            <p className="text-sm text-muted-foreground mb-3">Allow transactions during waking hours across all timezones.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "time_policy": {
            "timezone": "UTC",
            "allowed_hours": {"start": 6, "end": 22},
            # No allowed_days = all days
        },
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-1">4. Extended Friday Hours</h3>
            <p className="text-sm text-muted-foreground mb-3">Standard hours Mon-Thu, extended hours on Friday.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "time_policy": {
            "timezone": "America/New_York",
            "schedules": [
                {
                    "days": ["mon", "tue", "wed", "thu"],
                    "hours": {"start": 9, "end": 17},
                },
                {
                    "days": ["fri"],
                    "hours": {"start": 9, "end": 20},
                },
            ],
        },
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-1">5. Combined: Time + Amount Limits</h3>
            <p className="text-sm text-muted-foreground mb-3">Different spending limits for business hours vs. after hours.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`# Business hours: higher limits
policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "time_policy": {
            "timezone": "America/New_York",
            "schedules": [
                {
                    "days": ["mon", "tue", "wed", "thu", "fri"],
                    "hours": {"start": 9, "end": 17},
                    "max_daily": 1000_000_000,  # $1,000/day during biz hours
                    "max_per_transaction": 200_000_000,  # $200/tx
                },
                {
                    "label": "after_hours",
                    "hours": {"start": 17, "end": 9},
                    "max_daily": 100_000_000,  # $100/day after hours
                    "max_per_transaction": 50_000_000,  # $50/tx
                },
            ],
        },
    },
)`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Natural Language Examples
        </h2>
        <p className="text-muted-foreground mb-4">
          Time-based policies can be created using natural language via <code>create_from_natural_language</code>:
        </p>
        <div className="not-prose">
          <div className="overflow-x-auto">
            <table className="w-full text-sm border border-border">
              <thead>
                <tr className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
                  <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Natural Language Input</th>
                  <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Parsed Policy</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-b border-border">
                  <td className="p-3">"Only allow spending during business hours EST"</td>
                  <td className="p-3 font-mono text-xs">{`{timezone: "America/New_York", hours: {start:9, end:17}, days: ["mon"-"fri"]}`}</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="p-3">"Block all weekend transactions"</td>
                  <td className="p-3 font-mono text-xs">{`{blocked_days: ["sat", "sun"]}`}</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="p-3">"Allow between 6 AM and 10 PM UTC"</td>
                  <td className="p-3 font-mono text-xs">{`{timezone: "UTC", hours: {start:6, end:22}}`}</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="p-3">"$50 limit after hours, $200 during work"</td>
                  <td className="p-3 font-mono text-xs">{`{schedules: [{hours:9-17, max_per_tx:200}, {hours:17-9, max_per_tx:50}]}`}</td>
                </tr>
                <tr className="border-b border-border">
                  <td className="p-3">"Only 9 to 5 Tokyo time on weekdays"</td>
                  <td className="p-3 font-mono text-xs">{`{timezone: "Asia/Tokyo", hours: {start:9, end:17}, days: ["mon"-"fri"]}`}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Edge Cases
        </h2>
        <div className="not-prose space-y-3">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Midnight Boundaries</h3>
            <p className="text-sm text-muted-foreground">
              If <code>start &gt; end</code> (e.g., <code>{`{start: 22, end: 6}`}</code>), Sardis treats this as
              an overnight window spanning midnight. A policy of "10 PM to 6 AM" covers 22:00-23:59 and 00:00-05:59.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">DST Transitions</h3>
            <p className="text-sm text-muted-foreground">
              During spring-forward (e.g., 2:00 AM jumps to 3:00 AM), the "lost" hour is treated as outside the window.
              During fall-back, the repeated hour is evaluated once (first occurrence). Always use IANA names
              for correct DST handling.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Multiple Schedules</h3>
            <p className="text-sm text-muted-foreground">
              When using the <code>schedules</code> array, overlapping windows are evaluated in order.
              The first matching schedule applies. Non-matching times are blocked by default.
            </p>
          </div>
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">No Time Policy Set</h3>
            <p className="text-sm text-muted-foreground">
              If <code>time_policy</code> is omitted entirely, transactions are allowed at all times.
              Time policies are additive restrictions - they only narrow the allowed window.
            </p>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> SDK Reference
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis import SardisClient

async with SardisClient(api_key="sk_...") as client:
    # Create time-restricted policy
    policy = await client.policies.create(
        wallet_id="wallet_abc",
        rules={
            "max_per_transaction": 50_000_000,   # $50/tx
            "max_daily": 500_000_000,            # $500/day
            "allowed_vendors": ["openai", "anthropic", "aws"],
            "time_policy": {
                "timezone": "America/New_York",
                "allowed_hours": {"start": 9, "end": 17},
                "allowed_days": ["mon", "tue", "wed", "thu", "fri"],
            },
        },
    )

    # Check if a transaction would be allowed right now
    check = await client.policies.validate(
        wallet_id="wallet_abc",
        transaction={
            "amount_minor": 25_000_000,
            "vendor": "openai",
        },
    )
    print(f"Allowed: {check.allowed}")
    if not check.allowed:
        print(f"Reason: {check.reason}")
        # e.g., "Transaction blocked: outside allowed hours (9:00-17:00 EST)"

    # Natural language creation
    policy = await client.policies.create_from_natural_language(
        wallet_id="wallet_def",
        description="Allow up to $100/day during business hours EST, "
                    "$25/day on evenings and weekends, "
                    "only for SaaS and cloud services",
    )`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Best Practices</h3>
        <ul className="space-y-1 text-muted-foreground text-sm">
          <li>1. <strong>Use IANA timezone names</strong> instead of UTC offsets to get automatic DST handling</li>
          <li>2. <strong>Start with business hours</strong> until you understand your agent's spending patterns</li>
          <li>3. <strong>Combine with amount limits</strong> for defense-in-depth (lower limits outside business hours)</li>
          <li>4. <strong>Monitor blocked transactions</strong> to fine-tune your time windows over time</li>
          <li>5. <strong>Consider global teams</strong> - use the timezone of the person responsible for oversight</li>
        </ul>
      </section>
    </article>
  );
}

export default function DocsMerchantCategories() {
  return (
    <article className="prose prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-blue-500/10 border border-blue-500/30 text-blue-500">CORE FEATURES</span>
          <span className="px-2 py-1 bg-green-500/10 border border-green-500/30 text-green-500">STABLE</span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Merchant Categories & MCC Codes</h1>
        <p className="text-xl text-muted-foreground">Control which types of merchants your AI agent can transact with using industry-standard MCC codes.</p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> What Are MCC Codes?
        </h2>
        <p className="text-muted-foreground mb-4">
          Merchant Category Codes (MCCs) are four-digit numbers assigned by card networks (Visa, Mastercard) to classify
          businesses by the type of goods or services they provide. Every card transaction includes the merchant's MCC,
          which Sardis uses to enforce category-based spending policies.
        </p>
        <div className="not-prose p-4 border border-border bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
          <p className="text-sm text-muted-foreground">
            <strong className="text-[var(--sardis-orange)]">How It Works:</strong> When a virtual card transaction occurs,
            the card network reports the merchant's MCC. Sardis maps MCCs to human-readable categories and checks them
            against your policy's <code>allowed_categories</code> and <code>blocked_categories</code> lists.
          </p>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Category Reference
        </h2>
        <p className="text-muted-foreground mb-4">
          Sardis maps raw MCC codes to named categories for easier policy configuration:
        </p>
        <div className="not-prose overflow-x-auto">
          <table className="w-full text-sm border border-border">
            <thead>
              <tr className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a]">
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Category</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">MCC Codes</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Examples</th>
                <th className="text-left p-3 border-b border-border font-mono text-[var(--sardis-orange)]">Default</th>
              </tr>
            </thead>
            <tbody className="text-muted-foreground">
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">saas</td>
                <td className="p-3 font-mono text-xs">5734, 5817</td>
                <td className="p-3">Software subscriptions, SaaS tools</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">cloud_infrastructure</td>
                <td className="p-3 font-mono text-xs">7372</td>
                <td className="p-3">AWS, GCP, Azure, Vercel</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">developer_tools</td>
                <td className="p-3 font-mono text-xs">5734, 7372</td>
                <td className="p-3">GitHub, JetBrains, Datadog</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">ai_services</td>
                <td className="p-3 font-mono text-xs">7372, 5818</td>
                <td className="p-3">OpenAI, Anthropic, Replicate</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">advertising</td>
                <td className="p-3 font-mono text-xs">7311</td>
                <td className="p-3">Google Ads, Meta Ads, LinkedIn Ads</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">office_supplies</td>
                <td className="p-3 font-mono text-xs">5111, 5943</td>
                <td className="p-3">Staples, Office Depot</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">telecommunications</td>
                <td className="p-3 font-mono text-xs">4812, 4814</td>
                <td className="p-3">Twilio, Phone services</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-green-400">shipping</td>
                <td className="p-3 font-mono text-xs">4215</td>
                <td className="p-3">FedEx, UPS, USPS</td>
                <td className="p-3 text-green-400">Allowed</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-yellow-400">travel</td>
                <td className="p-3 font-mono text-xs">3000-3299, 4511, 7011</td>
                <td className="p-3">Airlines, hotels, car rental</td>
                <td className="p-3 text-yellow-400">Neutral</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-yellow-400">food_delivery</td>
                <td className="p-3 font-mono text-xs">5811, 5812, 5814</td>
                <td className="p-3">DoorDash, Uber Eats, restaurants</td>
                <td className="p-3 text-yellow-400">Neutral</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-yellow-400">retail</td>
                <td className="p-3 font-mono text-xs">5311, 5411, 5691</td>
                <td className="p-3">Amazon, Walmart, general retail</td>
                <td className="p-3 text-yellow-400">Neutral</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">gambling</td>
                <td className="p-3 font-mono text-xs">7800, 7801, 7802, 7995</td>
                <td className="p-3">Casinos, lotteries, sports betting</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">adult_content</td>
                <td className="p-3 font-mono text-xs">5967</td>
                <td className="p-3">Adult entertainment, dating services</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">cash_advance</td>
                <td className="p-3 font-mono text-xs">6010, 6011</td>
                <td className="p-3">ATMs, cash disbursements</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">quasi_cash</td>
                <td className="p-3 font-mono text-xs">6051, 6540</td>
                <td className="p-3">Money orders, crypto, prepaid cards</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">securities</td>
                <td className="p-3 font-mono text-xs">6211</td>
                <td className="p-3">Stock brokers, trading platforms</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">wire_transfer</td>
                <td className="p-3 font-mono text-xs">4829</td>
                <td className="p-3">Wire transfers, money orders</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
              <tr className="border-b border-border">
                <td className="p-3 font-mono text-red-400">pawn_shops</td>
                <td className="p-3 font-mono text-xs">5933</td>
                <td className="p-3">Pawn shops, secondhand dealers</td>
                <td className="p-3 text-red-400">Blocked</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Allowed vs Blocked Categories
        </h2>
        <div className="not-prose space-y-4">
          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Allowlist Mode (Recommended)</h3>
            <p className="text-sm text-muted-foreground mb-3">Only specified categories are permitted. Everything else is blocked.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "allowed_categories": ["saas", "cloud_infrastructure", "ai_services"],
        # All other categories are implicitly blocked
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Blocklist Mode</h3>
            <p className="text-sm text-muted-foreground mb-3">All categories allowed except those explicitly blocked.</p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "blocked_categories": ["gambling", "adult_content", "securities"],
        # All other categories are allowed
    },
)`}</pre>
            </div>
          </div>

          <div className="p-4 border border-border">
            <h3 className="font-bold text-[var(--sardis-orange)] mb-2">Conflict Resolution</h3>
            <p className="text-sm text-muted-foreground mb-3">
              When both <code>allowed_categories</code> and <code>blocked_categories</code> are set,
              the allowed list takes precedence. A category in the allowed list cannot be blocked.
            </p>
            <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-3 font-mono text-xs">
              <pre className="text-[var(--sardis-canvas)]">{`# "saas" is allowed even though "retail" category
# might overlap - allowed_categories wins
policy = await client.policies.create(
    wallet_id="wallet_abc",
    rules={
        "allowed_categories": ["saas", "cloud_infrastructure"],
        "blocked_categories": ["gambling"],  # Extra safety
    },
)`}</pre>
            </div>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MCC Auto-Detection
        </h2>
        <p className="text-muted-foreground mb-4">
          When a Lithic virtual card transaction occurs, the card network automatically provides the merchant's MCC.
          Sardis uses this in two ways:
        </p>
        <div className="not-prose space-y-2 text-sm">
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">1</span>
            <span className="text-muted-foreground"><strong>Real-time ASA decisions:</strong> During authorization (Lithic ASA webhook), the MCC is checked against blocked MCCs before approving the transaction.</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">2</span>
            <span className="text-muted-foreground"><strong>Post-transaction audit:</strong> After settlement, the MCC is logged in the transaction record for analytics and policy refinement.</span>
          </div>
          <div className="flex items-center gap-3 p-3 border border-border">
            <span className="font-mono text-[var(--sardis-orange)]">3</span>
            <span className="text-muted-foreground"><strong>On-chain payments:</strong> For crypto transactions, Sardis maps the recipient address to known merchant categories when possible.</span>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Natural Language Examples
        </h2>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# All these create equivalent category policies:

policy = await client.policies.create_from_natural_language(
    wallet_id="wallet_abc",
    description="Only allow SaaS and developer tools",
)
# -> allowed_categories: ["saas", "developer_tools"]

policy = await client.policies.create_from_natural_language(
    wallet_id="wallet_def",
    description="Block gambling, adult content, and cash advances",
)
# -> blocked_categories: ["gambling", "adult_content", "cash_advance"]

policy = await client.policies.create_from_natural_language(
    wallet_id="wallet_ghi",
    description="Allow cloud services and AI APIs, max $500/day",
)
# -> allowed_categories: ["cloud_infrastructure", "ai_services"]
# -> max_daily: 500_000_000`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> MCC Lookup Tool
        </h2>
        <p className="text-muted-foreground mb-4">
          Use the <code>sardis_mcc_lookup</code> MCP tool or API endpoint to look up categories:
        </p>
        <div className="not-prose">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Python SDK
result = await client.mcc_lookup(code="5734")
# -> {"code": "5734", "category": "saas", "description": "Computer Software Stores"}

# Via MCP tool
sardis_mcc_lookup(code="7995")
# -> {"code": "7995", "category": "gambling", "description": "Betting/Casino/Lottery"}`}</pre>
          </div>
        </div>
      </section>

      <section className="not-prose p-6 border border-[var(--sardis-orange)]/30 bg-[var(--sardis-orange)]/5">
        <h3 className="font-bold font-display mb-2 text-[var(--sardis-orange)]">Best Practices</h3>
        <ul className="space-y-1 text-muted-foreground text-sm">
          <li>1. <strong>Use allowlists over blocklists</strong> - Safer default: only known-good categories are permitted</li>
          <li>2. <strong>Always block high-risk MCCs</strong> - Gambling, cash advances, and quasi-cash are blocked by default</li>
          <li>3. <strong>Combine with merchant rules</strong> - Use per-merchant overrides for fine-grained control</li>
          <li>4. <strong>Review unknown MCCs</strong> - Some merchants use unexpected MCCs; monitor and adjust</li>
          <li>5. <strong>Use the MCC lookup tool</strong> - Verify merchant categories before adding to policies</li>
        </ul>
      </section>
    </article>
  );
}

export default function IntegrationMPP() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            INTEGRATION
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">MPP &amp; Tempo Integration</h1>
        <p className="text-xl text-muted-foreground">
          Connect Sardis to the Model Payment Protocol (MPP) and Tempo network for AI-native payments.
        </p>
      </div>

      <div className="not-prose mb-8 p-4 rounded-lg bg-purple-500/5 border border-purple-500/20">
        <p className="text-sm text-muted-foreground">
          Sardis was featured at the MPP Hackathon (March 2026) with the Guard Intelligence Plane
          -- a financial intelligence layer for AI agents operating on the MPP network.
        </p>
      </div>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> What is MPP?
        </h2>

        <p className="text-muted-foreground mb-4">
          The <strong>Model Payment Protocol</strong> is Stripe's open standard for AI-to-service payments.
          It enables AI agents to discover, negotiate, and pay for services programmatically.
          Sardis adds policy enforcement, compliance checks, and audit trails on top of MPP transactions.
        </p>

        <p className="text-muted-foreground mb-4">
          <strong>Tempo</strong> is the high-throughput L1 blockchain (100K+ TPS, EVM compatible) that MPP
          runs on. Sardis supports Tempo mainnet and testnet for MPP settlement.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Installation
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`pip install sardis-mpp`}</pre>
          </div>
        </div>

        <p className="text-muted-foreground mb-4">
          The <code>sardis-mpp</code> package wraps the <code>pympp</code> SDK with Sardis policy
          enforcement, spending mandates, and audit trail integration.
        </p>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Quick Start
        </h2>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`from sardis_mpp import SardisMPPClient

# Initialize with Sardis policy enforcement
client = SardisMPPClient(
    sardis_api_key="sk_live_...",
    agent_id="agent_procurement",
    tempo_rpc_url="https://rpc.tempo.xyz",  # or testnet
)

# Discover services in the MPP directory
services = await client.discover(
    category="compute",
    max_price_usd=10.0,
)

# Pay for a service — policy checks run automatically
receipt = await client.pay(
    service_id=services[0].id,
    amount_usd=5.00,
    memo="GPU compute for batch inference",
)

print(f"Payment: {receipt.tx_hash}")
print(f"Policy:  {receipt.policy_result}")  # ALLOW / BLOCK
print(f"Audit:   {receipt.audit_id}")`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> x402 Auto-Pay
        </h2>

        <p className="text-muted-foreground mb-4">
          MPP supports the <strong>x402</strong> protocol for automatic micro-payments. When an API
          returns a <code>402 Payment Required</code> header, the Sardis MPP client automatically
          negotiates and pays — subject to your spending policy.
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Enable x402 auto-pay with policy limits
client = SardisMPPClient(
    sardis_api_key="sk_live_...",
    agent_id="agent_researcher",
    x402_auto_pay=True,
    x402_max_per_request=1.00,  # Max $1 per auto-pay
)

# This will auto-pay if the API returns 402
response = await client.fetch(
    "https://api.example.com/data",
    headers={"Accept": "application/json"},
)
# Sardis enforces: per-request cap, daily limit, merchant whitelist`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Tempo Chain Config
        </h2>

        <div className="not-prose mb-6">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left py-3 px-4 font-mono font-medium text-muted-foreground">Network</th>
                  <th className="text-left py-3 px-4 font-mono font-medium text-muted-foreground">Chain ID</th>
                  <th className="text-left py-3 px-4 font-mono font-medium text-muted-foreground">RPC</th>
                </tr>
              </thead>
              <tbody className="text-muted-foreground">
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-foreground">Tempo Mainnet</td>
                  <td className="py-3 px-4 font-mono">42429</td>
                  <td className="py-3 px-4 font-mono">rpc.tempo.xyz</td>
                </tr>
                <tr className="border-b border-border/50">
                  <td className="py-3 px-4 font-mono text-foreground">Tempo Testnet (Moderato)</td>
                  <td className="py-3 px-4 font-mono">42431</td>
                  <td className="py-3 px-4 font-mono">rpc-testnet.tempo.xyz</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Policy Enforcement
        </h2>

        <p className="text-muted-foreground mb-4">
          Every MPP transaction passes through the Sardis policy engine before execution.
          Define policies in natural language or structured rules:
        </p>

        <div className="not-prose mb-6">
          <div className="bg-[var(--sardis-ink)] dark:bg-[#1a1a1a] border border-border p-4 font-mono text-sm overflow-x-auto">
            <pre className="text-[var(--sardis-canvas)]">{`# Natural language policy
policy = "Allow up to $50/day on compute services. "
         "Block gambling and adult content. "
         "Require approval for any single payment over $20."

client.set_policy(policy)

# Or structured rules
client.set_policy_rules([
    {"type": "daily_limit", "amount_usd": 50},
    {"type": "category_block", "categories": ["gambling", "adult"]},
    {"type": "approval_threshold", "amount_usd": 20},
])`}</pre>
          </div>
        </div>
      </section>

      <section className="mb-12">
        <h2 className="text-2xl font-bold font-display mb-4 flex items-center gap-2">
          <span className="text-[var(--sardis-orange)]">#</span> Next Steps
        </h2>

        <ul>
          <li>Read the <a href="/docs/spending-mandates" className="text-[var(--sardis-orange)] hover:underline">Spending Mandates</a> guide for delegated financial authority</li>
          <li>Explore <a href="/docs/policies" className="text-[var(--sardis-orange)] hover:underline">Spending Policies</a> for fine-grained control</li>
          <li>See <a href="/docs/blockchain-infrastructure" className="text-[var(--sardis-orange)] hover:underline">Blockchain Infrastructure</a> for chain configuration</li>
        </ul>
      </section>
    </article>
  );
}

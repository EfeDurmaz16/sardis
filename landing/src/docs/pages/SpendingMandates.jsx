export default function SpendingMandates() {
  return (
    <article className="prose dark:prose-invert max-w-none">
      <div className="not-prose mb-8">
        <div className="flex items-center gap-3 text-sm text-muted-foreground font-mono mb-4">
          <span className="px-2 py-1 bg-purple-500/10 border border-purple-500/30 text-purple-500">
            CORE CONCEPT
          </span>
        </div>
        <h1 className="text-4xl font-bold font-display mb-4">Spending Mandates</h1>
        <p className="text-xl text-muted-foreground">
          The authorization primitive that makes agent payments safe.
        </p>
      </div>

      <section className="not-prose mb-8 p-4 border border-purple-500/30 bg-purple-500/10">
        <p className="text-sm text-muted-foreground">
          <strong className="text-purple-500">Key insight:</strong> The hard part of agent payments is not access to money.
          It is controlling authority over money. A spending mandate defines exactly what an agent is allowed to spend,
          on what, and under what conditions.
        </p>
      </section>

      <h2>What is a Spending Mandate?</h2>
      <p>
        A spending mandate is a <strong>machine-readable payment permission</strong> that defines the scoped,
        time-limited, revocable authority an AI agent has to spend money. Think of it as a power of attorney
        for payments — but with precise limits, automatic enforcement, and instant revocation.
      </p>
      <p>
        Unlike giving an agent a credit card (broad access, no controls), a spending mandate defines:
      </p>
      <ul>
        <li><strong>WHO</strong> can spend (agent identity + who authorized it)</li>
        <li><strong>WHAT</strong> they can buy (merchant allowlist, blocked merchants, categories)</li>
        <li><strong>HOW MUCH</strong> (per-transaction, daily, weekly, monthly, and total limits)</li>
        <li><strong>ON WHICH RAILS</strong> (virtual cards, USDC, bank transfer — or all three)</li>
        <li><strong>FOR HOW LONG</strong> (activation time, expiration)</li>
        <li><strong>WITH WHAT APPROVAL</strong> (auto-approve small amounts, human review for large ones)</li>
        <li><strong>WITH WHAT REVOCATION</strong> (instant kill, with reason tracking and audit trail)</li>
      </ul>

      <h2>Quick Start</h2>
      <pre className="not-prose"><code className="language-python">{`from sardis import SardisClient, SpendingMandate

client = SardisClient()

# Create a mandate for an API consumption agent
mandate = SpendingMandate(
    purpose="AI API usage for research",
    amount_per_tx=50,           # Max $50 per API call
    amount_daily=200,           # Max $200/day
    amount_monthly=2000,        # Max $2,000/month
    merchant_scope={
        "allowed": ["openai.com", "anthropic.com", "google.com"]
    },
    approval_threshold=100,     # Human approval above $100
)

# Check if a payment is authorized
result = mandate.check(amount=25, merchant="openai.com")
print(result.approved)          # True
print(result.requires_approval) # False

result = mandate.check(amount=150, merchant="openai.com")
print(result.approved)          # True
print(result.requires_approval) # True (above $100 threshold)

result = mandate.check(amount=25, merchant="stripe.com")
print(result.approved)          # False — not in allowed list
`}</code></pre>

      <h2>Lifecycle</h2>
      <p>
        Every mandate follows a strict lifecycle with audited state transitions:
      </p>
      <div className="not-prose mb-6">
        <table className="w-full text-sm border border-border">
          <thead>
            <tr className="bg-muted/30">
              <th className="text-left p-3 border-b border-border">State</th>
              <th className="text-left p-3 border-b border-border">Description</th>
              <th className="text-left p-3 border-b border-border">Payments Allowed?</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['Draft', 'Created but not yet active', 'No'],
              ['Active', 'Enforcing — payments checked against this mandate', 'Yes (within limits)'],
              ['Suspended', 'Temporarily paused (e.g., during investigation)', 'No'],
              ['Revoked', 'Permanently invalidated — cannot be reactivated', 'No'],
              ['Expired', 'Past expiration time', 'No'],
              ['Consumed', 'Total budget exhausted', 'No'],
            ].map(([state, desc, payments]) => (
              <tr key={state} className="border-b border-border">
                <td className="p-3 font-mono font-medium">{state}</td>
                <td className="p-3">{desc}</td>
                <td className="p-3">{payments}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2>Cross-Rail Authorization</h2>
      <p>
        A single mandate works across all payment rails. The same rules apply whether the
        agent pays with a virtual card, USDC on Base, or a bank transfer:
      </p>
      <pre className="not-prose"><code className="language-python">{`mandate = SpendingMandate(
    purpose="Office supplies and cloud infrastructure",
    amount_per_tx=5000,
    allowed_rails=["card", "usdc", "bank"],  # All rails permitted
    merchant_scope={
        "allowed": ["aws.amazon.com", "staples.com"]
    },
    approval_threshold=1000,
)

# Same mandate validates regardless of rail
mandate.check(amount=500, merchant="aws.amazon.com", rail="usdc")  # Approved
mandate.check(amount=500, merchant="aws.amazon.com", rail="card")  # Approved
mandate.check(amount=500, merchant="aws.amazon.com", rail="bank")  # Approved
`}</code></pre>

      <h2>Approval Workflows</h2>
      <p>Three approval modes control when human review is required:</p>
      <ul>
        <li><strong>Auto:</strong> All payments within limits are auto-approved</li>
        <li><strong>Threshold:</strong> Auto-approve below the threshold, require human approval above it</li>
        <li><strong>Always Human:</strong> Every payment requires human sign-off</li>
      </ul>

      <h2>Instant Revocation</h2>
      <p>
        A mandate can be revoked instantly at any time. Once revoked, <strong>all future payments
        are blocked immediately</strong> — the mandate cannot be reactivated. This is the ultimate
        safety control.
      </p>
      <pre className="not-prose"><code className="language-python">{`# Instant revocation
mandate.revoke(reason="Suspicious activity detected")
# All future mandate.check() calls return approved=False
`}</code></pre>

      <h2>Industry Alignment</h2>
      <p>
        The spending mandate model aligns with where the entire payments industry is heading:
      </p>
      <ul>
        <li><strong>Stripe</strong> Shared Payment Tokens — seller-scoped, amount-bounded, expirable</li>
        <li><strong>Visa</strong> Trusted Agent Protocol — trusted agent identity and authorization</li>
        <li><strong>Mastercard</strong> Agent Pay — tokenized agent transactions with trust framework</li>
        <li><strong>Google</strong> AP2 — cross-rail payment protocol for AI agents</li>
        <li><strong>OpenAI</strong> Commerce Protocol — delegated payment through compliant PSPs</li>
      </ul>
      <p>
        Sardis implements the full authorization-layer vision that these protocols point toward —
        but with natural language policies, cross-rail portability, and enterprise-grade controls.
      </p>

      <h2>Next: Payment Tokens</h2>
      <p>
        Spending mandates are the <strong>architectural bridge</strong> to payment tokens. Today, mandates
        are enforced off-chain by the Sardis API. Tomorrow, the same mandate semantics will be
        encoded as on-chain ERC-20 transfer hooks — making the token itself enforce the spending rules.
      </p>
      <p>
        Learn more in the <a href="/docs/architecture">Architecture</a> section.
      </p>
    </article>
  );
}

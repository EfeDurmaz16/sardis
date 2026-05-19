import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Sardis vs Stripe: AI Agent Payment Comparison",
  description:
    "A detailed comparison of Sardis and Stripe for AI agent payments. Understand the differences in architecture, pricing, security, and use cases for autonomous AI agent commerce.",
  alternates: { canonical: "/compare/sardis-vs-stripe" },
  openGraph: {
    title: "Sardis vs Stripe: AI Agent Payment Comparison",
    description:
      "A detailed comparison of Sardis and Stripe for AI agent payments.",
    url: "https://sardis.sh/compare/sardis-vs-stripe",
    siteName: "Sardis",
    type: "website",
  },
}

/* Static JSON-LD — all values are hardcoded constants, no user input */
const productJsonLdString = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "Product",
  name: "Sardis",
  description:
    "The Payment OS for the Agent Economy. Non-custodial MPC wallets with natural language spending policies for AI agents.",
  brand: { "@type": "Organization", name: "Sardis Labs, Inc." },
  url: "https://sardis.sh",
  category: "Payment Infrastructure",
  offers: {
    "@type": "Offer",
    price: "0",
    priceCurrency: "USD",
    description: "Free tier with simulation mode. Usage-based production pricing. 0% merchant fee on USDC checkout.",
  },
})

const breadcrumbJsonLdString = JSON.stringify({
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  itemListElement: [
    { "@type": "ListItem", position: 1, name: "Home", item: "https://sardis.sh" },
    { "@type": "ListItem", position: 2, name: "Compare", item: "https://sardis.sh/compare" },
    { "@type": "ListItem", position: 3, name: "Sardis vs Stripe", item: "https://sardis.sh/compare/sardis-vs-stripe" },
  ],
})

const th = {
  padding: "14px 16px",
  fontSize: 13,
  fontWeight: 600 as const,
  textAlign: "left" as const,
  color: "#1A1614",
  borderBottom: "2px solid rgba(26,22,20,0.1)",
  background: "rgba(26,22,20,0.03)",
}

const td = {
  padding: "14px 16px",
  fontSize: 14,
  color: "rgba(26,22,20,0.65)",
  lineHeight: "22px",
  borderBottom: "1px solid rgba(26,22,20,0.06)",
  verticalAlign: "top" as const,
}

const tdFeature = {
  ...td,
  fontWeight: 500 as const,
  color: "#1A1614",
  width: "30%",
}

const h2Style = {
  fontSize: "clamp(24px, 4vw, 36px)",
  fontWeight: 700 as const,
  letterSpacing: "-0.03em",
  lineHeight: 1.2,
  margin: "0 0 16px",
}

const h3Style = {
  fontSize: 20,
  fontWeight: 600 as const,
  letterSpacing: "-0.02em",
  margin: "0 0 12px",
}

const para = {
  fontSize: 15,
  color: "rgba(26,22,20,0.55)",
  lineHeight: "26px",
  margin: "0 0 20px",
  maxWidth: 680,
}

export default function SardisVsStripePage() {
  return (
    <>
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: productJsonLdString }} />
      <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: breadcrumbJsonLdString }} />
      <main
        style={{
          background: "#FDFBF7",
          color: "#1A1614",
          minHeight: "100vh",
          fontFamily: "'Plus Jakarta Sans', sans-serif",
        }}
      >
        {/* Nav */}
        <nav style={{ display: "flex", justifyContent: "center", padding: "24px 16px 0" }}>
          <div
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              width: "100%",
              maxWidth: 1100,
              padding: "12px 24px",
              background: "rgba(26,22,20,0.04)",
              border: "1px solid rgba(26,22,20,0.06)",
              borderRadius: 100,
            }}
          >
            <Link href="/landing" style={{ display: "flex", alignItems: "center", gap: 10, textDecoration: "none" }}>
              <svg width={20} height={20} viewBox="0 0 28 28" fill="none">
                <path d="M20 5H10a7 7 0 000 14h2" stroke="#1A1614" strokeWidth="3" strokeLinecap="round" fill="none" />
                <path d="M8 23h10a7 7 0 000-14h-2" stroke="#1A1614" strokeWidth="3" strokeLinecap="round" fill="none" />
              </svg>
              <span style={{ fontSize: 15, fontWeight: 700, color: "#1A1614", letterSpacing: "-0.02em" }}>Sardis</span>
            </Link>
            <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
              <Link href="/landing" style={{ fontSize: 13, color: "rgba(26,22,20,0.45)", textDecoration: "none" }}>Home</Link>
              <Link href="/faq" style={{ fontSize: 13, color: "rgba(26,22,20,0.45)", textDecoration: "none" }}>FAQ</Link>
              <a href="https://docs.sardis.sh" target="_blank" rel="noopener noreferrer" style={{ fontSize: 13, color: "rgba(26,22,20,0.45)", textDecoration: "none" }}>Docs</a>
            </div>
          </div>
        </nav>

        {/* Header */}
        <section style={{ display: "flex", flexDirection: "column", alignItems: "center", padding: "80px 16px 48px", textAlign: "center" }}>
          <span style={{ fontSize: 12, fontWeight: 500, color: "rgba(26,22,20,0.35)", letterSpacing: "0.1em", textTransform: "uppercase", marginBottom: 16 }}>
            Comparison
          </span>
          <h1 style={{ fontSize: "clamp(32px, 5vw, 56px)", fontWeight: 800, letterSpacing: "-0.04em", lineHeight: 1.1, maxWidth: 800, margin: 0 }}>
            Sardis vs Stripe
          </h1>
          <p style={{ fontSize: 17, color: "rgba(26,22,20,0.45)", lineHeight: "28px", maxWidth: 600, marginTop: 20 }}>
            Stripe is the gold standard for human-to-merchant payments. Sardis is purpose-built for autonomous AI agents that transact without human oversight. Here is how they compare.
          </p>
          <p style={{ fontSize: 13, color: "rgba(26,22,20,0.3)", marginTop: 16 }}>
            Last updated: April 2026
          </p>
        </section>

        {/* Content */}
        <article style={{ maxWidth: 860, margin: "0 auto", padding: "0 16px 96px" }}>

          {/* TL;DR */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>The fundamental difference</h2>
            <p style={para}>
              Stripe processes payments initiated by humans through checkout forms, invoices, and subscription billing pages. A human clicks &ldquo;Pay,&rdquo; Stripe handles the rest. This model works brilliantly for e-commerce, SaaS billing, and marketplaces — Stripe processes over $1 trillion in annual payment volume because of it.
            </p>
            <p style={para}>
              Sardis processes payments initiated by AI agents through API calls, SDK invocations, and MCP tool calls. There is no human in the loop at transaction time. An agent decides it needs to pay for inference credits, cloud compute, or a SaaS subscription, and Sardis evaluates the request against programmable spending policies before signing the transaction with an MPC wallet. The agent never holds private keys. The human sets the rules; the agent operates within them.
            </p>
            <p style={para}>
              This is not a marginal difference. It changes the trust model, the authorization flow, the compliance surface, and the infrastructure architecture. Stripe trusts the human at the keyboard. Sardis trusts the policy, not the agent.
            </p>
          </section>

          {/* Feature Comparison Table */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Feature comparison</h2>
            <div style={{ overflowX: "auto", marginTop: 24 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(26,22,20,0.08)" }}>
                <thead>
                  <tr>
                    <th style={th}>Feature</th>
                    <th style={th}>Sardis</th>
                    <th style={th}>Stripe</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdFeature}>Primary user</td>
                    <td style={td}>AI agents (autonomous software)</td>
                    <td style={td}>Humans (via checkout, invoices, dashboards)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Authorization model</td>
                    <td style={td}>Programmable spending policies in plain English</td>
                    <td style={td}>Human approval (click &ldquo;Pay&rdquo;, confirm invoice)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Wallet infrastructure</td>
                    <td style={td}>Non-custodial MPC wallets (Turnkey)</td>
                    <td style={td}>No wallet — routes to existing card/bank networks</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Settlement</td>
                    <td style={td}>On-chain stablecoins (USDC, USDT, EURC) — seconds</td>
                    <td style={td}>Traditional card rails — 2-7 business days</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Supported chains</td>
                    <td style={td}>Base, Polygon, Ethereum, Arbitrum, Optimism</td>
                    <td style={td}>N/A (traditional payment rails only)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Spending controls</td>
                    <td style={td}>Per-agent policies: amount, merchant, time, chain, token</td>
                    <td style={td}>Account-level settings, Radar fraud rules</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Compliance</td>
                    <td style={td}>KYC (Didit), AML (Elliptic), sanctions screening</td>
                    <td style={td}>PCI DSS, SCA, built-in Radar for fraud</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Audit trail</td>
                    <td style={td}>Append-only ledger with Merkle anchoring</td>
                    <td style={td}>Dashboard logs and event webhooks</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>SDK languages</td>
                    <td style={td}>Python, TypeScript, MCP server (52 tools)</td>
                    <td style={td}>Python, TypeScript, Ruby, Go, Java, PHP, .NET</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>AI framework integrations</td>
                    <td style={td}>Browser Use, CrewAI, OpenAI Agents, Vercel AI, LangChain</td>
                    <td style={td}>None (designed for web frameworks)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Virtual cards</td>
                    <td style={td}>Yes (via Stripe Issuing)</td>
                    <td style={td}>Yes (Stripe Issuing)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Fiat on-ramp</td>
                    <td style={td}>Yes (Coinbase Onramp)</td>
                    <td style={td}>Native (card/bank acceptance)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Protocol support</td>
                    <td style={td}>AP2 (Google/PayPal/Mastercard/Visa), TAP, x402, A2A</td>
                    <td style={td}>Standard card network protocols</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Open source</td>
                    <td style={td}>Open-core (SDKs, MCP server, integrations)</td>
                    <td style={td}>Client libraries open source, platform proprietary</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Pricing Comparison */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Pricing comparison</h2>
            <p style={para}>
              Stripe charges 2.9% + $0.30 per successful card charge in the US, with additional fees for international cards, currency conversion, and Stripe Issuing. This pricing model is designed for card-based e-commerce where the merchant absorbs the processing cost.
            </p>
            <p style={para}>
              Sardis charges 0% merchant fees on USDC stablecoin checkout. Because settlement happens on-chain via stablecoins, there are no card network interchange fees. The only costs are blockchain gas fees (typically under $0.01 on Base) and optional premium features for enterprise plans. The free tier includes simulation mode with no API key required.
            </p>
            <div style={{ overflowX: "auto", marginTop: 24 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(26,22,20,0.08)" }}>
                <thead>
                  <tr>
                    <th style={th}>Cost</th>
                    <th style={th}>Sardis</th>
                    <th style={th}>Stripe</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdFeature}>Transaction fee</td>
                    <td style={td}>0% (USDC checkout)</td>
                    <td style={td}>2.9% + $0.30 per charge</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Gas / network fees</td>
                    <td style={td}>~$0.001-0.01 on Base</td>
                    <td style={td}>N/A (absorbed in processing fee)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>International fees</td>
                    <td style={td}>None (stablecoins are borderless)</td>
                    <td style={td}>+1.5% for international cards</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Free tier</td>
                    <td style={td}>Yes — simulation mode, no API key</td>
                    <td style={td}>No minimum, pay per transaction</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Virtual card issuance</td>
                    <td style={td}>Via Stripe Issuing (pass-through cost)</td>
                    <td style={td}>$0.10 per virtual card created</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p style={{ ...para, marginTop: 20 }}>
              For AI agent workloads that make many small transactions — buying API credits, paying for compute, purchasing data feeds — the 2.9% + $0.30 per-transaction fee adds up quickly. A $5 API credit purchase loses 8.9% to processing fees on Stripe. On Sardis, the same transaction costs under a cent in gas.
            </p>
          </section>

          {/* Architecture Deep Dive */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Architecture differences</h2>

            <h3 style={h3Style}>Trust model</h3>
            <p style={para}>
              Stripe&apos;s trust model assumes a human is present at the point of sale. The cardholder authenticates via 3D Secure, the merchant is verified through Stripe&apos;s onboarding, and disputes are resolved through chargeback processes. This is a well-understood model that has worked for decades of e-commerce.
            </p>
            <p style={para}>
              Sardis&apos;s trust model assumes no human is present. The AI agent is not trusted — the spending policy is. Sardis enforces constraints at the infrastructure level: the MPC wallet will not produce a signature unless the policy engine approves the transaction. This is a fundamentally different security architecture. You are not trusting the agent to make good decisions; you are making it impossible for the agent to make unauthorized ones.
            </p>

            <h3 style={h3Style}>Settlement speed</h3>
            <p style={para}>
              Stripe settles via traditional card networks, which means 2-7 business days for funds to reach the merchant&apos;s bank account. Stripe does offer Instant Payouts for an additional 1% fee, but this still requires existing card rail infrastructure.
            </p>
            <p style={para}>
              Sardis settles on-chain in seconds. A USDC transfer on Base achieves finality in approximately 2 seconds. There are no intermediary banks, no T+2 settlement windows, and no weekend delays. For AI agents that need to pay for resources in real-time — like compute during an inference job — this speed difference is critical.
            </p>

            <h3 style={h3Style}>Programmability</h3>
            <p style={para}>
              Stripe offers Radar rules for fraud detection and basic webhook-driven automation. These work well for pattern matching on card transactions but were not designed for pre-authorizing autonomous software agents. Stripe&apos;s API is optimized for creating charges, subscriptions, and invoices — human-oriented payment objects.
            </p>
            <p style={para}>
              Sardis&apos;s entire API is designed around agent payment objects: spending policies, mandate chains (AP2), wallet creation, and policy-gated execution. The SDK methods like <code style={{ fontSize: 13, background: "rgba(26,22,20,0.05)", padding: "2px 6px", borderRadius: 4 }}>client.pay()</code> are purpose-built for the agent workflow of intent, policy check, sign, and broadcast.
            </p>
          </section>

          {/* Use Cases */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>When to use Stripe vs Sardis</h2>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginTop: 24 }}>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Use Stripe when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>Your customers are humans paying through checkout forms</li>
                  <li style={{ marginBottom: 8 }}>You need subscription billing with invoicing</li>
                  <li style={{ marginBottom: 8 }}>You accept credit/debit cards as the primary payment method</li>
                  <li style={{ marginBottom: 8 }}>Your payment flows involve manual approval or human review</li>
                  <li style={{ marginBottom: 8 }}>You operate in markets where card payments dominate</li>
                  <li>You need the broadest possible SDK language support</li>
                </ul>
              </div>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Use Sardis when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>AI agents need to transact autonomously without human approval</li>
                  <li style={{ marginBottom: 8 }}>You need programmable spending policies that enforce limits automatically</li>
                  <li style={{ marginBottom: 8 }}>Settlement speed matters — seconds, not days</li>
                  <li style={{ marginBottom: 8 }}>You want to avoid 2.9% + $0.30 per-transaction fees on high-volume agent payments</li>
                  <li style={{ marginBottom: 8 }}>Your agents need to pay across chains (Base, Polygon, Ethereum, Arbitrum, Optimism)</li>
                  <li>You need a tamper-evident audit trail for every agent transaction</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Why Sardis */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Why choose Sardis for AI agent payments</h2>
            <p style={para}>
              The question is not whether Stripe is a good product — it is the best payment processor for human commerce. The question is whether a system built for humans clicking checkout buttons is the right infrastructure for autonomous agents making thousands of transactions per hour.
            </p>
            <p style={para}>
              Sardis exists because the answer is no. AI agents need a different authorization model (policies, not passwords), a different custody model (MPC, not card-on-file), a different settlement layer (on-chain, not T+2 ACH), and a different compliance surface (real-time sanctions screening, not post-hoc fraud detection).
            </p>
            <p style={para}>
              Stripe and Sardis are complementary, not competitive. Sardis uses Stripe Issuing for virtual card creation when agents need to pay traditional merchants. Many teams will run both — Stripe for their human customers, Sardis for their AI agents. The architectures serve different principals in the transaction.
            </p>
            <p style={para}>
              If you are building AI agents that need to spend money, Sardis gives you the infrastructure to let them do it safely. Set the rules in plain English, deploy the agent, and trust the system — not the agent — to enforce your financial boundaries.
            </p>
          </section>

          {/* Integration Example */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Getting started</h2>
            <p style={para}>
              Sardis is designed to be as simple to integrate as Stripe. Install the SDK, create an API key, define a spending policy, and your agent can start transacting in under 10 minutes.
            </p>
            <div
              style={{
                background: "#1A1614",
                borderRadius: 16,
                padding: 24,
                overflow: "auto",
              }}
            >
              <pre style={{ margin: 0, fontSize: 13, lineHeight: "22px", color: "rgba(253,251,247,0.7)", fontFamily: "var(--font-geist-mono), monospace" }}>
{`from sardis import SardisClient

client = SardisClient(api_key="sk_live_...")

# Create an agent with a spending policy
agent = client.agents.create(
    name="Procurement Bot",
    chain="base",
    policy="Max $500/day, only SaaS and cloud providers"
)

# The agent can now pay within its policy
payment = client.pay(
    agent_id=agent.id,
    amount="49.99",
    to="openai.com",
    purpose="GPT-4 API credits"
)

print(payment.status)  # "completed"
print(payment.tx_hash) # "0xabc..."
`}
              </pre>
            </div>
          </section>

          {/* Bottom CTA */}
          <section
            style={{
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              padding: "64px 0",
              textAlign: "center",
              borderTop: "1px solid rgba(26,22,20,0.06)",
            }}
          >
            <h2 style={{ ...h2Style, maxWidth: 500, textAlign: "center" }}>
              Give your AI agents safe spending power
            </h2>
            <p style={{ ...para, textAlign: "center", marginBottom: 28 }}>
              Free tier with simulation mode. No credit card required. Set up in 10 minutes.
            </p>
            <div style={{ display: "flex", gap: 12, flexWrap: "wrap", justifyContent: "center" }}>
              <a
                href="https://app.sardis.sh"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "14px 28px",
                  background: "#1A1614",
                  color: "#FDFBF7",
                  borderRadius: 100,
                  fontSize: 14,
                  fontWeight: 500,
                  textDecoration: "none",
                }}
              >
                Get started free
                <span style={{ fontSize: 13 }}>&#8594;</span>
              </a>
              <a
                href="https://docs.sardis.sh"
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  padding: "14px 28px",
                  border: "1px solid rgba(26,22,20,0.1)",
                  borderRadius: 100,
                  fontSize: 14,
                  color: "rgba(26,22,20,0.45)",
                  textDecoration: "none",
                }}
              >
                Read the docs
              </a>
            </div>
          </section>
        </article>

        {/* Footer */}
        <footer style={{ display: "flex", justifyContent: "center", padding: "24px 16px", borderTop: "1px solid rgba(26,22,20,0.06)" }}>
          <span style={{ fontSize: 12, color: "rgba(26,22,20,0.3)" }}>
            &copy; {new Date().getFullYear()} Sardis Labs, Inc.
          </span>
        </footer>
      </main>
    </>
  )
}

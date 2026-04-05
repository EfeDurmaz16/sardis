import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Sardis vs Locus: AI Agent Payment Platform Comparison",
  description:
    "Compare Sardis and Locus (YC F25) for AI agent payments. Understand the differences in architecture, wallet infrastructure, policy enforcement, protocol support, and multi-chain capabilities.",
  alternates: { canonical: "/compare/sardis-vs-locus" },
  openGraph: {
    title: "Sardis vs Locus: AI Agent Payment Platform Comparison",
    description:
      "Compare Sardis and Locus for AI agent payment infrastructure.",
    url: "https://sardis.sh/compare/sardis-vs-locus",
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
    { "@type": "ListItem", position: 3, name: "Sardis vs Locus", item: "https://sardis.sh/compare/sardis-vs-locus" },
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

export default function SardisVsLocusPage() {
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
            Sardis vs Locus
          </h1>
          <p style={{ fontSize: 17, color: "rgba(26,22,20,0.45)", lineHeight: "28px", maxWidth: 600, marginTop: 20 }}>
            Sardis and Locus (YC F25) both build payment infrastructure for AI agents. Both offer wallets, spending controls, and USDC settlement. Here is where they differ and which is right for your use case.
          </p>
          <p style={{ fontSize: 13, color: "rgba(26,22,20,0.3)", marginTop: 16 }}>
            Last updated: April 2026
          </p>
        </section>

        {/* Content */}
        <article style={{ maxWidth: 860, margin: "0 auto", padding: "0 16px 96px" }}>

          {/* Overview */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Both platforms at a glance</h2>
            <p style={para}>
              Sardis and Locus are building in the same emerging category: payment infrastructure for AI agents. Both recognize that autonomous software needs a fundamentally different payment stack than human-initiated commerce. Both offer USDC wallets on Base, spending controls, and developer-friendly SDKs. The differences are in architecture depth, multi-chain support, protocol coverage, and approach to compliance.
            </p>
            <p style={para}>
              Locus (YC F25) offers a unified USDC balance that agents can use for wallets, API access (30+ pay-per-use APIs), deployments (Railway), and a Stripe-style checkout SDK. Their focus is on simplicity: one balance, many uses. Founded by a team from Scale AI and Coinbase, Locus is currently in beta on Base.
            </p>
            <p style={para}>
              Sardis takes a deeper infrastructure approach. Rather than bundling API marketplace and deployment features, Sardis focuses on the payment orchestration layer: MPC wallet custody (Turnkey), natural language spending policies, AP2 mandate chain verification, KYC/AML compliance pipeline, and multi-chain settlement across five EVM networks. Sardis also provides native integrations with six AI frameworks and a 52-tool MCP server for Claude Desktop and Cursor.
            </p>
          </section>

          {/* Feature Table */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Feature comparison</h2>
            <div style={{ overflowX: "auto", marginTop: 24 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(26,22,20,0.08)" }}>
                <thead>
                  <tr>
                    <th style={th}>Feature</th>
                    <th style={th}>Sardis</th>
                    <th style={th}>Locus (YC F25)</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdFeature}>Architecture</td>
                    <td style={td}>Payment orchestration with policy engine and compliance pipeline</td>
                    <td style={td}>Unified balance with wallet, API marketplace, and deployments</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Wallet type</td>
                    <td style={td}>Non-custodial MPC wallets (Turnkey) with policy-gated signing</td>
                    <td style={td}>Smart wallets on Base with subwallet support</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Spending controls</td>
                    <td style={td}>Natural language policies: amount, merchant, time, chain, token, frequency</td>
                    <td style={td}>Spending limits, per-transaction budgets, approval thresholds, vendor allowlists</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Supported chains</td>
                    <td style={td}>Base, Polygon, Ethereum, Arbitrum, Optimism</td>
                    <td style={td}>Base (additional chains planned)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Supported tokens</td>
                    <td style={td}>USDC, USDT, EURC, PYUSD</td>
                    <td style={td}>USDC</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Cross-chain</td>
                    <td style={td}>CCTP V2 with unified addresses</td>
                    <td style={td}>Base only (no cross-chain yet)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Compliance (KYC/AML)</td>
                    <td style={td}>KYC (Didit), AML (Elliptic), real-time sanctions screening</td>
                    <td style={td}>Not publicly documented</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Audit trail</td>
                    <td style={td}>Append-only ledger with Merkle anchoring (tamper-evident)</td>
                    <td style={td}>Full audit trails (per documentation)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Protocol support</td>
                    <td style={td}>AP2 (Google/PayPal/Mastercard/Visa), TAP, x402, A2A</td>
                    <td style={td}>OpenAI Agentic Commerce Protocol (ACP)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>API marketplace</td>
                    <td style={td}>No (focused on payment orchestration)</td>
                    <td style={td}>Yes — 30+ pay-per-use APIs (AI models, data, search)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Deployment integration</td>
                    <td style={td}>No</td>
                    <td style={td}>Yes — Railway app provisioning via API</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Checkout SDK</td>
                    <td style={td}>Yes (embedded checkout with client secrets)</td>
                    <td style={td}>Yes (Stripe-style checkout for AI payments)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>AI framework integrations</td>
                    <td style={td}>Browser Use, CrewAI, OpenAI Agents, Vercel AI, LangChain, Activepieces</td>
                    <td style={td}>OpenAI Agents (ACP demo)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>MCP server</td>
                    <td style={td}>Yes — 52 tools for Claude Desktop and Cursor</td>
                    <td style={td}>Not publicly available</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Virtual cards</td>
                    <td style={td}>Yes (via Stripe Issuing)</td>
                    <td style={td}>Not available</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Fiat support</td>
                    <td style={td}>On-ramp (Coinbase) + virtual cards for fiat merchants</td>
                    <td style={td}>ACH and wire (coming soon)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Gas handling</td>
                    <td style={td}>Circle Paymaster (sponsored gas) + Pimlico backup</td>
                    <td style={td}>Sponsored gas on Base</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Open source</td>
                    <td style={td}>Open-core (SDKs, MCP server, 15+ framework integrations)</td>
                    <td style={td}>ACP demo on GitHub</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Key Differences */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Key architectural differences</h2>

            <h3 style={h3Style}>Multi-chain vs single-chain</h3>
            <p style={para}>
              Sardis supports five EVM chains — Base, Polygon, Ethereum, Arbitrum, and Optimism — with CCTP V2 for cross-chain USDC movement. This matters for agents that interact with DeFi protocols, pay merchants on different chains, or need to optimize for gas costs across networks.
            </p>
            <p style={para}>
              Locus currently operates on Base only, with additional chains planned. For agents that only need to transact on Base, this is sufficient. But for enterprise use cases that require multi-chain flexibility or cross-chain settlement, Sardis provides more infrastructure out of the box.
            </p>

            <h3 style={h3Style}>MPC custody vs smart wallets</h3>
            <p style={para}>
              Sardis uses Turnkey MPC wallets where the private key is split across multiple parties and never reconstituted. The MPC signing process is gated by the policy engine — the wallet physically cannot sign a transaction that violates the agent&apos;s spending policy. This is non-custodial by design.
            </p>
            <p style={para}>
              Locus uses smart wallets on Base with subwallet support. Smart wallets offer programmability through on-chain logic, but the security model depends on how the wallet contract is configured and who controls the admin keys. Both approaches are valid; MPC provides cryptographic enforcement at the signing layer, while smart wallets provide enforcement at the contract layer.
            </p>

            <h3 style={h3Style}>Protocol depth</h3>
            <p style={para}>
              Sardis implements AP2 (the consortium standard from Google, PayPal, Mastercard, and Visa), TAP for agent identity verification, x402 for HTTP-native payments, and Google&apos;s A2A for agent-to-agent communication. These protocols provide interoperability with the broader agent commerce ecosystem.
            </p>
            <p style={para}>
              Locus has demonstrated integration with OpenAI&apos;s Agentic Commerce Protocol (ACP), which focuses on OpenAI-ecosystem agent commerce. The choice between AP2 and ACP may depend on which agent ecosystem your application targets — AP2 is cross-platform, while ACP is OpenAI-native.
            </p>

            <h3 style={h3Style}>Bundled services vs focused orchestration</h3>
            <p style={para}>
              Locus bundles payment wallets with an API marketplace (30+ pay-per-use APIs) and deployment provisioning (Railway). This is convenient for agents that need a single account to pay for AI models, data, compute, and other services.
            </p>
            <p style={para}>
              Sardis focuses exclusively on payment orchestration — wallets, policies, compliance, and settlement — and provides framework integrations (Browser Use, CrewAI, OpenAI Agents, Vercel AI, LangChain) that let agents use Sardis within their existing toolchains. Sardis does not bundle third-party APIs but gives agents the financial infrastructure to pay for any service directly.
            </p>
          </section>

          {/* When to Use */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>When to use Locus vs Sardis</h2>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginTop: 24 }}>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Consider Locus when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>You want a single balance for wallets, APIs, and deployments</li>
                  <li style={{ marginBottom: 8 }}>Your agents primarily consume APIs and you want bundled pay-per-use access</li>
                  <li style={{ marginBottom: 8 }}>You only need Base chain support</li>
                  <li style={{ marginBottom: 8 }}>You are building in the OpenAI ecosystem and want ACP integration</li>
                  <li>You prefer a simpler, all-in-one platform over modular infrastructure</li>
                </ul>
              </div>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Choose Sardis when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>You need multi-chain support (Base, Polygon, Ethereum, Arbitrum, Optimism)</li>
                  <li style={{ marginBottom: 8 }}>You need MPC wallet custody with cryptographic policy enforcement</li>
                  <li style={{ marginBottom: 8 }}>You require KYC/AML compliance built into the payment pipeline</li>
                  <li style={{ marginBottom: 8 }}>You want AP2 mandate chain verification (Google, PayPal, Mastercard, Visa standard)</li>
                  <li style={{ marginBottom: 8 }}>You need native integrations with multiple AI frameworks, not just OpenAI</li>
                  <li style={{ marginBottom: 8 }}>You want virtual card issuance for fiat merchant payments</li>
                  <li>You need a 52-tool MCP server for Claude Desktop and Cursor</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Why Sardis */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Why choose Sardis</h2>
            <p style={para}>
              Both Sardis and Locus are building important infrastructure for the agent economy. The key question is what your agents need: a bundled platform with API marketplace and deployment tools, or a deep payment orchestration layer with multi-chain support, MPC custody, compliance, and cross-platform protocol support.
            </p>
            <p style={para}>
              Sardis is designed for production-grade AI agent payments where compliance, auditability, and multi-chain flexibility are requirements — not nice-to-haves. The combination of MPC wallets (Turnkey), natural language spending policies, AP2 mandate verification, KYC/AML pipeline, and tamper-evident audit trail provides enterprise-grade financial infrastructure for autonomous agents.
            </p>
            <p style={para}>
              If you need your agents to pay across chains, comply with financial regulations, integrate with multiple AI frameworks, and produce audit trails that satisfy compliance requirements, Sardis provides the depth of infrastructure that the agent economy demands.
            </p>
          </section>

          {/* Code Example */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Getting started with Sardis</h2>
            <p style={para}>
              Install the SDK, create an agent with a spending policy, and start transacting in under 10 minutes.
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
{`from sardis import Sardis

client = Sardis(api_key="sk_live_...")

# Create agent with granular spending policy
agent = client.agents.create(
    name="Research Assistant",
    chain="base",
    policy="Max $50/tx, $300/day, only AI and data providers"
)

# Agent pays for API access — policy enforced automatically
payment = client.pay(
    agent_id=agent.id,
    amount="8.00",
    to="perplexity.ai",
    purpose="Search API credits"
)

print(payment.status)    # "completed"
print(payment.tx_hash)   # "0xdef..."
print(payment.policy_ok) # True
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

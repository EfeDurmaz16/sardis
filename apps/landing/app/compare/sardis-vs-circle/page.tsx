import type { Metadata } from "next"
import Link from "next/link"

export const metadata: Metadata = {
  title: "Sardis vs Circle: AI Agent Payment Infrastructure Comparison",
  description:
    "Compare Sardis and Circle for AI agent payments. Understand the differences between stablecoin issuance infrastructure and agent-native payment orchestration with spending policies.",
  alternates: { canonical: "/compare/sardis-vs-circle" },
  openGraph: {
    title: "Sardis vs Circle: AI Agent Payment Infrastructure Comparison",
    description:
      "Compare Sardis and Circle for AI agent payments.",
    url: "https://sardis.sh/compare/sardis-vs-circle",
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
    { "@type": "ListItem", position: 3, name: "Sardis vs Circle", item: "https://sardis.sh/compare/sardis-vs-circle" },
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

export default function SardisVsCirclePage() {
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
            Sardis vs Circle
          </h1>
          <p style={{ fontSize: 17, color: "rgba(26,22,20,0.45)", lineHeight: "28px", maxWidth: 600, marginTop: 20 }}>
            Circle is the issuer of USDC and provides stablecoin infrastructure. Sardis is the payment orchestration layer that gives AI agents controlled access to stablecoins like USDC. Here is how they compare.
          </p>
          <p style={{ fontSize: 13, color: "rgba(26,22,20,0.3)", marginTop: 16 }}>
            Last updated: April 2026
          </p>
        </section>

        {/* Content */}
        <article style={{ maxWidth: 860, margin: "0 auto", padding: "0 16px 96px" }}>

          {/* Fundamental Difference */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>The fundamental difference</h2>
            <p style={para}>
              Circle is the company behind USDC, the second-largest stablecoin by market capitalization. Circle provides the stablecoin issuance layer, the CCTP (Cross-Chain Transfer Protocol) for moving USDC between blockchains, the Circle Paymaster for gasless transactions, and Programmable Wallets for application developers. Circle is infrastructure for stablecoins — the token layer.
            </p>
            <p style={para}>
              Sardis is the orchestration layer that sits above the token layer. Sardis uses USDC as its primary settlement token, leverages CCTP V2 for cross-chain transfers, and integrates Circle Paymaster for gas sponsorship. But Sardis adds what Circle does not provide: natural language spending policies, agent identity verification, compliance checks, and a policy firewall that prevents unauthorized transactions before they reach the chain.
            </p>
            <p style={para}>
              Think of it this way: Circle gives you the money (USDC) and the pipes (CCTP). Sardis gives AI agents the rules for how to use that money safely. Circle is to Sardis what Visa&apos;s card network is to a corporate expense management platform — the underlying rail versus the policy and control layer on top.
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
                    <th style={th}>Circle</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdFeature}>Primary purpose</td>
                    <td style={td}>Payment orchestration for AI agents</td>
                    <td style={td}>Stablecoin issuance and infrastructure</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Target user</td>
                    <td style={td}>AI agent developers, autonomous software</td>
                    <td style={td}>Exchanges, fintechs, app developers, enterprises</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Spending policies</td>
                    <td style={td}>Natural language policies per agent (amount, merchant, time, chain)</td>
                    <td style={td}>None — wallets execute any valid transaction</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Wallet type</td>
                    <td style={td}>Non-custodial MPC wallets (Turnkey) with policy gating</td>
                    <td style={td}>Programmable Wallets (custodial and non-custodial options)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Supported tokens</td>
                    <td style={td}>USDC, USDT, EURC, PYUSD</td>
                    <td style={td}>USDC, EURC (Circle-issued only)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Cross-chain</td>
                    <td style={td}>CCTP V2 integration (unified addresses)</td>
                    <td style={td}>CCTP V2 (native protocol owner)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Gas sponsorship</td>
                    <td style={td}>Circle Paymaster + Pimlico backup</td>
                    <td style={td}>Circle Paymaster (native)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Compliance</td>
                    <td style={td}>KYC (Didit), AML (Elliptic), real-time sanctions screening</td>
                    <td style={td}>Verite identity framework, compliance APIs</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Audit trail</td>
                    <td style={td}>Append-only ledger with Merkle anchoring</td>
                    <td style={td}>Transaction history via APIs</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>AI framework integrations</td>
                    <td style={td}>Browser Use, CrewAI, OpenAI Agents, Vercel AI, LangChain</td>
                    <td style={td}>None (general developer APIs)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Protocol support</td>
                    <td style={td}>AP2 (Google/PayPal/Mastercard/Visa), TAP, x402, A2A</td>
                    <td style={td}>CCTP, ERC-20, Verite</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Fiat on/off-ramp</td>
                    <td style={td}>Coinbase Onramp</td>
                    <td style={td}>Circle Mint (institutional), partner integrations</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Virtual cards</td>
                    <td style={td}>Yes (via Stripe Issuing)</td>
                    <td style={td}>No</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>SDKs</td>
                    <td style={td}>Python, TypeScript, MCP server (52 tools)</td>
                    <td style={td}>JavaScript, Python, Go, Java</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* Architecture */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Architecture differences</h2>

            <h3 style={h3Style}>Policy enforcement vs open execution</h3>
            <p style={para}>
              Circle Programmable Wallets let any authorized caller execute transactions. If your application has the credentials, it can move funds. This is the right model for human-controlled applications where the developer decides when to call the transfer function.
            </p>
            <p style={para}>
              Sardis adds a mandatory policy evaluation step before any transaction can execute. When an AI agent requests a payment, the policy engine checks the amount, recipient, time, frequency, chain, and token against the agent&apos;s spending policy. If any rule fails, the MPC wallet refuses to produce a signature. The agent cannot bypass this — the policy is enforced at the signing layer, not the application layer.
            </p>
            <p style={para}>
              This distinction matters because AI agents, unlike human developers, make autonomous decisions about when and how to spend. Without policy enforcement at the infrastructure level, an agent with wallet access could drain funds through a series of individually valid but collectively unauthorized transactions.
            </p>

            <h3 style={h3Style}>Agent identity and mandate chains</h3>
            <p style={para}>
              Circle provides Verite for decentralized identity verification, which is useful for KYC/KYB flows. But it does not define agent-specific identity or purchase mandate chains.
            </p>
            <p style={para}>
              Sardis implements the AP2 (Agent Payment Protocol) mandate chain — Intent, Cart, Payment — developed by Google, PayPal, Mastercard, and Visa. Every agent payment follows a structured workflow where the intent is declared, the cart is assembled, and the payment is authorized against the mandate. This gives enterprises an auditable chain of reasoning for every agent transaction, not just a transfer record.
            </p>

            <h3 style={h3Style}>Sardis builds on Circle</h3>
            <p style={para}>
              Sardis is not a replacement for Circle — it is a customer of Circle&apos;s infrastructure. Sardis uses USDC as the primary settlement token, CCTP V2 for cross-chain movement, and Circle Paymaster for gasless transactions. The relationship is similar to how a fintech company uses Visa&apos;s network while adding its own authorization and compliance logic on top.
            </p>
            <p style={para}>
              If you are building general stablecoin infrastructure — an exchange, a remittance service, a treasury management tool — Circle&apos;s APIs give you direct access to the token and transfer layer. If you are building AI agents that need to spend stablecoins safely within defined guardrails, Sardis provides the orchestration layer that Circle does not.
            </p>
          </section>

          {/* Pricing */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Pricing comparison</h2>
            <p style={para}>
              Circle&apos;s core infrastructure — USDC transfers, CCTP, and basic Programmable Wallets — is generally free to use. Circle earns revenue from the interest on USDC reserves, not from transaction fees. Enterprise features, Circle Mint for institutional on/off-ramp, and high-volume wallet management have custom pricing.
            </p>
            <p style={para}>
              Sardis charges 0% merchant fees on USDC stablecoin checkout. The free tier includes simulation mode with no API key required. Production usage is on a usage-based model. Enterprise plans with dedicated support and custom SLAs are available on request.
            </p>
            <div style={{ overflowX: "auto", marginTop: 24 }}>
              <table style={{ width: "100%", borderCollapse: "collapse", borderRadius: 12, overflow: "hidden", border: "1px solid rgba(26,22,20,0.08)" }}>
                <thead>
                  <tr>
                    <th style={th}>Cost</th>
                    <th style={th}>Sardis</th>
                    <th style={th}>Circle</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td style={tdFeature}>USDC transfers</td>
                    <td style={td}>0% fee (gas only)</td>
                    <td style={td}>Free (gas only)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Merchant checkout fee</td>
                    <td style={td}>0%</td>
                    <td style={td}>N/A (no checkout product)</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Free tier</td>
                    <td style={td}>Simulation mode, no API key needed</td>
                    <td style={td}>Programmable Wallets free tier</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Policy engine</td>
                    <td style={td}>Included</td>
                    <td style={td}>N/A</td>
                  </tr>
                  <tr>
                    <td style={tdFeature}>Enterprise</td>
                    <td style={td}>Custom pricing</td>
                    <td style={td}>Custom pricing</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          {/* When to Use */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>When to use Circle vs Sardis</h2>

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: 24, marginTop: 24 }}>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Use Circle directly when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>You are building a stablecoin exchange or trading platform</li>
                  <li style={{ marginBottom: 8 }}>You need programmatic access to USDC minting and redemption at institutional scale</li>
                  <li style={{ marginBottom: 8 }}>Your application manages wallets where humans make all spending decisions</li>
                  <li style={{ marginBottom: 8 }}>You need CCTP for cross-chain USDC movement as a standalone feature</li>
                  <li>You are building general-purpose fintech infrastructure, not AI agent workflows</li>
                </ul>
              </div>
              <div style={{ padding: 24, border: "1px solid rgba(26,22,20,0.08)", borderRadius: 16 }}>
                <h3 style={{ ...h3Style, marginBottom: 8 }}>Use Sardis when</h3>
                <ul style={{ ...para, margin: 0, paddingLeft: 20 }}>
                  <li style={{ marginBottom: 8 }}>AI agents need to spend USDC autonomously within enforced spending policies</li>
                  <li style={{ marginBottom: 8 }}>You need per-agent spending controls (amount limits, merchant restrictions, time constraints)</li>
                  <li style={{ marginBottom: 8 }}>You want native integrations with AI frameworks (CrewAI, OpenAI Agents, Browser Use)</li>
                  <li style={{ marginBottom: 8 }}>You need an auditable mandate chain for every agent transaction (AP2 protocol)</li>
                  <li>You want virtual card issuance so agents can pay traditional merchants</li>
                </ul>
              </div>
            </div>
          </section>

          {/* Why Sardis */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Why choose Sardis for AI agent payments</h2>
            <p style={para}>
              Circle gives you the best stablecoin infrastructure in the industry — USDC is the most trusted programmable dollar, and CCTP is the standard for cross-chain stablecoin movement. Sardis does not compete with Circle; Sardis builds on Circle.
            </p>
            <p style={para}>
              What Circle does not provide is the agent-specific orchestration layer: who can spend, how much, on what, when, and with what audit trail. These are the questions that matter when autonomous software is making financial decisions. Sardis answers them with programmable policies, MPC co-signing, AP2 mandate verification, and a tamper-evident audit ledger.
            </p>
            <p style={para}>
              If you are building AI agents that need to transact with stablecoins, you will likely use both. Circle for the token and transport layer. Sardis for the policy, identity, and compliance layer that makes autonomous spending safe.
            </p>
          </section>

          {/* Code Example */}
          <section style={{ marginBottom: 56 }}>
            <h2 style={h2Style}>Getting started</h2>
            <p style={para}>
              Sardis handles USDC settlement under the hood. Your agent code interacts with the Sardis SDK — you do not need to manage Circle APIs directly.
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

# Agent pays with USDC on Base — Circle CCTP handles
# cross-chain if needed, Sardis enforces the policy
agent = client.agents.create(
    name="Data Buyer",
    chain="base",
    policy="Max $200/day, only data providers and APIs"
)

payment = client.pay(
    agent_id=agent.id,
    amount="12.50",
    to="data-provider.com",
    purpose="Weather dataset access"
)

print(payment.status)   # "completed"
print(payment.chain)    # "base"
print(payment.token)    # "USDC"
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
